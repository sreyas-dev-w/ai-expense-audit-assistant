"""Validation Agent — a LangGraph subgraph that checks a structured claim.

Flow (see ``docs/agents/validation-agent.md``):

    START → load_context → run_rules → reason → assemble → END
                 └─ lookup failure is a warning, not a terminal error
                 └─ malformed / unexpected failure → error_terminal

Input contract:  ``request``  → ``ValidationRequest`` (OCR envelope).
Output contract: ``result``   → ``ValidationAgentResult``.

Deterministic rules live in ``app/rules/`` and are the source of truth for
amounts, dates, mismatches, budget, and duplicates. The LLM only adds an
authenticity assessment and cannot override a blocking rule to PASS.
"""
from __future__ import annotations

import asyncio
import json
from functools import lru_cache, partial
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.core.config import settings
from app.rules import run_all_rules
from app.schemas.validation import (
    AuthenticityAssessment,
    BudgetSnapshot,
    DuplicateCandidate,
    ValidationAgentError,
    ValidationAgentOutput,
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationReasoningOutput,
    ValidationRequest,
    ValidationSeverity,
    ValidationVerdict,
)
from app.services.gemini_client import GeminiLLMError
from app.services.validation_context_service import (
    ValidationContextService,
)

_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "validation_prompt.txt"

EMPTY_RESULT_CODE = "missing_result"
LLM_TIMEOUT_CODE = "llm_timeout"
INVALID_LLM_OUTPUT_CODE = "invalid_llm_output"
MALFORMED_INPUT_CODE = "malformed_input"


class ValidationAgentState(TypedDict, total=False):
    request: ValidationRequest
    budget: BudgetSnapshot | None
    duplicates: list[DuplicateCandidate]
    context_warnings: list[str]
    findings: list[ValidationFinding]
    checks: list[Any]
    warnings: list[str]
    authenticity: AuthenticityAssessment | None
    llm_ok: bool
    result: ValidationAgentResult | None
    error: ValidationAgentError | None


async def load_context_node(
    state: ValidationAgentState,
    *,
    context_service: ValidationContextService,
) -> dict[str, Any]:
    try:
        context = await context_service.load(state["request"])
    except Exception as exc:
        return {
            "budget": None,
            "duplicates": [],
            "context_warnings": [f"Context lookup failed: {exc}"],
        }
    return {
        "budget": context.budget,
        "duplicates": context.duplicates,
        "context_warnings": context.warnings,
    }


async def run_rules_node(state: ValidationAgentState) -> dict[str, Any]:
    findings, checks, warnings, _expense = run_all_rules(
        state["request"],
        budget=state.get("budget"),
        duplicates=state.get("duplicates") or [],
        context_warnings=state.get("context_warnings") or [],
    )
    return {
        "findings": findings,
        "checks": checks,
        "warnings": warnings,
    }


async def reason_node(
    state: ValidationAgentState,
    *,
    llm_client: Any,
) -> dict[str, Any]:
    warnings = list(state.get("warnings") or [])
    findings = list(state.get("findings") or [])
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(
                llm_client.generate_structured,
                system_instruction=get_validation_system_prompt(),
                contents=_build_contents(state),
                response_schema=ValidationReasoningOutput,
            ),
            timeout=settings.gemini_llm_timeout_seconds,
        )
    except asyncio.TimeoutError:
        warnings.append("authenticity_reasoning_unavailable: LLM timed out")
        return {
            "authenticity": AuthenticityAssessment(),
            "warnings": warnings,
            "llm_ok": False,
        }
    except GeminiLLMError as exc:
        warnings.append(f"authenticity_reasoning_unavailable: {exc}")
        return {
            "authenticity": AuthenticityAssessment(),
            "warnings": warnings,
            "llm_ok": False,
        }

    try:
        reasoning = ValidationReasoningOutput.model_validate(raw)
    except ValidationError as exc:
        warnings.append(
            f"authenticity_reasoning_unavailable: invalid LLM output ({exc.error_count()} errors)"
        )
        return {
            "authenticity": AuthenticityAssessment(),
            "warnings": warnings,
            "llm_ok": False,
        }

    extra = [
        item
        for item in reasoning.extra_findings
        if item.category == ValidationFindingCategory.AUTHENTICITY
    ]
    findings.extend(extra)
    warnings.extend(reasoning.warnings)
    return {
        "authenticity": reasoning.authenticity,
        "findings": findings,
        "warnings": warnings,
        "llm_ok": True,
    }


async def assemble_node(state: ValidationAgentState) -> dict[str, Any]:
    findings = list(state.get("findings") or [])
    authenticity = state.get("authenticity") or AuthenticityAssessment()
    llm_ok = bool(state.get("llm_ok", False))
    verdict = _verdict(findings, authenticity)
    output = ValidationAgentOutput(
        verdict=verdict,
        confidence=_confidence(verdict, llm_ok=llm_ok),
        findings=findings,
        checks=list(state.get("checks") or []),
        warnings=_unique(state.get("warnings") or []),
        duplicate_candidates=list(state.get("duplicates") or []),
        budget=state.get("budget"),
        authenticity=authenticity,
        summary=_summary(verdict, findings, authenticity),
    )
    return {
        "result": ValidationAgentResult(
            status=ValidationAgentStatus.SUCCESS,
            output=output,
        )
    }


async def error_terminal_node(state: ValidationAgentState) -> dict[str, Any]:
    error = state.get("error") or ValidationAgentError(
        code=EMPTY_RESULT_CODE,
        message="Validation agent finished without producing a result",
    )
    return {
        "result": ValidationAgentResult(
            status=ValidationAgentStatus.ERROR,
            error=error,
        )
    }


def build_validation_agent(
    *,
    context_service: ValidationContextService,
    llm_client: Any,
) -> CompiledStateGraph:
    """Compile the Validation Agent subgraph with injected services."""
    graph = StateGraph(ValidationAgentState)
    graph.add_node(
        "load_context",
        partial(load_context_node, context_service=context_service),
    )
    graph.add_node("run_rules", run_rules_node)
    graph.add_node("reason", partial(reason_node, llm_client=llm_client))
    graph.add_node("assemble", assemble_node)
    graph.add_node("error_terminal", error_terminal_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "run_rules")
    graph.add_edge("run_rules", "reason")
    graph.add_edge("reason", "assemble")
    graph.add_edge("assemble", END)
    graph.add_edge("error_terminal", END)
    return graph.compile()


async def run_validation_agent(
    request: ValidationRequest,
    *,
    context_service: ValidationContextService,
    llm_client: Any,
) -> ValidationAgentResult:
    """Run the Validation Agent once, returning its envelope result."""
    graph = build_validation_agent(
        context_service=context_service, llm_client=llm_client
    )
    try:
        final_state = await graph.ainvoke({"request": request})
    except Exception as exc:
        return ValidationAgentResult(
            status=ValidationAgentStatus.ERROR,
            error=ValidationAgentError(
                code=MALFORMED_INPUT_CODE,
                message=f"Validation agent failed: {exc}",
            ),
        )
    result = final_state.get("result")
    if result is None:
        return ValidationAgentResult(
            status=ValidationAgentStatus.ERROR,
            error=ValidationAgentError(
                code=EMPTY_RESULT_CODE,
                message="Validation agent finished without producing a result",
            ),
        )
    return result


def _verdict(
    findings: list[ValidationFinding],
    authenticity: AuthenticityAssessment,
) -> ValidationVerdict:
    if any(item.severity == ValidationSeverity.BLOCKING for item in findings):
        return ValidationVerdict.FAIL
    if authenticity.is_suspicious or authenticity.forged_likelihood >= 0.5:
        return ValidationVerdict.FLAG_FOR_REVIEW
    if any(item.severity == ValidationSeverity.WARNING for item in findings):
        return ValidationVerdict.FLAG_FOR_REVIEW
    return ValidationVerdict.PASS


def _confidence(verdict: ValidationVerdict, *, llm_ok: bool) -> float:
    base = {
        ValidationVerdict.PASS: 0.85,
        ValidationVerdict.FLAG_FOR_REVIEW: 0.6,
        ValidationVerdict.FAIL: 0.9,
    }[verdict]
    if not llm_ok:
        base = max(0.0, round(base - 0.15, 2))
    return base


def _summary(
    verdict: ValidationVerdict,
    findings: list[ValidationFinding],
    authenticity: AuthenticityAssessment,
) -> str:
    blocking = [
        item for item in findings if item.severity == ValidationSeverity.BLOCKING
    ]
    if verdict == ValidationVerdict.FAIL:
        lead = blocking[0].description if blocking else "Blocking validation issues found."
        return f"{len(blocking)} blocking validation issue(s). {lead}"
    if verdict == ValidationVerdict.FLAG_FOR_REVIEW:
        if authenticity.is_suspicious:
            return "Claim flagged for review due to authenticity concerns."
        return "Claim flagged for review due to validation warnings."
    return "Claim passed deterministic validation checks."


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _build_contents(state: ValidationAgentState) -> str:
    request = state["request"]
    payload = {
        "claim": request.model_dump(mode="json", exclude={"persist"}),
        "deterministic_findings": [
            item.model_dump(mode="json") for item in state.get("findings") or []
        ],
        "budget": (
            state["budget"].model_dump(mode="json") if state.get("budget") else None
        ),
        "duplicate_candidates": [
            item.model_dump(mode="json") for item in state.get("duplicates") or []
        ],
    }
    return json.dumps(payload, default=str, indent=2)


@lru_cache(maxsize=1)
def get_validation_system_prompt() -> str:
    return _PROMPT_FILE.read_text(encoding="utf-8")
