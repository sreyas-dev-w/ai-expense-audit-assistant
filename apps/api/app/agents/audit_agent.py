"""Audit Agent — sequential LangGraph orchestrator.

Flow (see ``docs/agents/orchestration.md`` and ``docs/agents/audit-agent.md``):

    START → load_context → set_status → extract → validate → policy
          → aggregate → persist_final → END

Control returns to this agent after every sub-agent. Sub-agent ERROR envelopes
skip later specialist agents; a validation verdict of FAIL still continues to
policy. The graph never holds a database session — persist goes through
``app.tools.audit_tools.AuditTools``.
"""
from __future__ import annotations

import asyncio
import json
from functools import lru_cache, partial
from pathlib import Path
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.agents.state import AuditGraphState
from app.agents.validation_agent import run_validation_agent
from app.agents.policy_rag_agent import run_policy_agent
from app.core.config import settings
from app.models.enums import ClaimStatus
from app.schemas.audit import (
    AuditAgentError,
    AuditAgentResult,
    AuditAgentStatus,
    AuditAggregationOutput,
    AuditRecommendation,
    AuditRequest,
    AuditResult,
)
from app.schemas.extraction import OCRResponse
from app.schemas.policy import (
    PolicyAgentResult,
    PolicyAgentStatus,
    PolicyDecision,
)
from app.schemas.validation import (
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationRequest,
    ValidationVerdict,
)
from app.services.claim_to_ocr_mapper import claim_to_ocr_kwargs
from app.services.gemini_client import GeminiLLMError
from app.services.policy_request_mapper import to_policy_evaluation_request
from app.tools.audit_tools import (
    AuditTools,
    EmployeeNotFoundError,
    format_policy_violation,
    format_validation_violation,
    load_receipt_bytes,
)
from app.core.exceptions import ClaimNotFoundError

_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "audit_aggregation_prompt.txt"

EMPTY_RESULT_CODE = "missing_result"
LLM_TIMEOUT_CODE = "llm_timeout"
INVALID_LLM_OUTPUT_CODE = "invalid_llm_output"
MISSING_RECEIPT_CODE = "missing_receipt"
OCR_FAILED_CODE = "ocr_failed"


@lru_cache(maxsize=1)
def get_audit_system_prompt() -> str:
    return _PROMPT_FILE.read_text(encoding="utf-8")


def decide_recommendation(
    validation: ValidationAgentResult | None,
    policy: PolicyAgentResult | None,
) -> AuditRecommendation:
    val_verdict = (
        validation.output.verdict
        if validation is not None and validation.output is not None
        else None
    )
    pol_decision = (
        policy.output.decision
        if policy is not None and policy.output is not None
        else None
    )
    if val_verdict == ValidationVerdict.FAIL or pol_decision == PolicyDecision.REJECT:
        return AuditRecommendation.RECOMMEND_REJECT
    if (
        val_verdict == ValidationVerdict.FLAG_FOR_REVIEW
        or pol_decision == PolicyDecision.FLAG_FOR_REVIEW
    ):
        return AuditRecommendation.FLAG_FOR_REVIEW
    if val_verdict == ValidationVerdict.PASS and pol_decision == PolicyDecision.APPROVE:
        return AuditRecommendation.RECOMMEND_APPROVE
    return AuditRecommendation.FLAG_FOR_REVIEW


def _error_code(error: Any) -> str | None:
    if error is None:
        return None
    if isinstance(error, dict):
        return error.get("code")
    return getattr(error, "code", None)


def _error_agent(error: Any) -> str:
    if error is None:
        return "audit_agent"
    if isinstance(error, dict):
        return str(error.get("agent") or "audit_agent")
    return getattr(error, "agent", "audit_agent")


def _error_message(error: Any) -> str:
    if error is None:
        return ""
    if isinstance(error, dict):
        return str(error.get("message") or "")
    return str(getattr(error, "message", error))


def overall_confidence(
    validation: ValidationAgentResult | None,
    policy: PolicyAgentResult | None,
    *,
    errored: bool,
) -> float:
    scores: list[float] = []
    if validation is not None and validation.output is not None:
        scores.append(validation.output.confidence)
    if policy is not None and policy.output is not None:
        scores.append(policy.output.confidence)
    value = min(scores) if scores else 0.0
    if errored:
        value = min(value, 0.4) if scores else 0.0
    return round(value, 2)


async def load_context_node(
    state: AuditGraphState,
    *,
    tools: AuditTools,
) -> dict[str, Any]:
    request = state["request"]
    context = await tools.load_audit_context(request.claim_id)

    receipt_bytes = state.get("receipt_bytes")
    mime_type = state.get("mime_type")
    if not receipt_bytes:
        loaded_bytes, loaded_mime = load_receipt_bytes(context.claim.receipt_url)
        receipt_bytes = loaded_bytes
        mime_type = mime_type or loaded_mime

    updates: dict[str, Any] = {
        "context": context,
        "receipt_bytes": receipt_bytes,
        "mime_type": mime_type,
    }
    if not receipt_bytes:
        updates["error"] = AuditAgentError(
            code=MISSING_RECEIPT_CODE,
            message="Receipt file is required.",
            agent="ocr_agent",
        )
    return updates


async def set_status_node(
    state: AuditGraphState,
    *,
    tools: AuditTools,
) -> dict[str, Any]:
    request = state["request"]
    if not request.persist:
        return {}
    warnings = list(state.get("persist_warnings") or [])
    try:
        await tools.update_claim_status(request.claim_id, ClaimStatus.IN_AUDIT)
        row_id = await tools.create_run_row(request.claim_id)
        return {"agent_response_id": row_id, "persist_warnings": warnings}
    except Exception as exc:
        warnings.append(f"persist: failed to open audit run ({exc})")
        return {"persist_warnings": warnings}


async def extract_node(
    state: AuditGraphState,
    *,
    run_ocr: Callable[..., Any],
) -> dict[str, Any]:
    if state.get("error") is not None:
        return {}
    context = state["context"]
    kwargs = claim_to_ocr_kwargs(context)
    kwargs["receipt_bytes"] = state.get("receipt_bytes")
    kwargs["mime_type"] = state.get("mime_type")
    try:
        extraction = await run_ocr(**kwargs)
    except Exception as exc:
        message = str(exc)
        code = (
            MISSING_RECEIPT_CODE
            if "Receipt" in message
            else OCR_FAILED_CODE
        )
        return {
            "error": AuditAgentError(
                code=code,
                message=message,
                agent="ocr_agent",
            )
        }
    if not isinstance(extraction, OCRResponse):
        extraction = OCRResponse.model_validate(extraction)
    return {"extraction": extraction}


async def validate_node(
    state: AuditGraphState,
    *,
    run_validation: Callable[..., Any],
) -> dict[str, Any]:
    if state.get("error") is not None or state.get("extraction") is None:
        return {}
    extraction = state["extraction"]
    context = state.get("context")
    if (
        context is not None
        and context.account is not None
        and extraction.employee_context.account_id is None
    ):
        extraction.employee_context.account_id = context.account.account_id
    try:
        request = ValidationRequest(
            submission=extraction.submission,
            employee_context=extraction.employee_context,
            extraction=extraction.extraction,
            claim_id=state["request"].claim_id,
            persist=False,
        )
        result = await run_validation(request)
        if not isinstance(result, ValidationAgentResult):
            result = ValidationAgentResult.model_validate(result)
    except Exception as exc:
        return {
            "error": AuditAgentError(
                code=getattr(exc, "code", "validation_failed"),
                message=str(exc),
                agent="validation_agent",
            )
        }
    updates: dict[str, Any] = {"validation": result}
    if result.status == ValidationAgentStatus.ERROR:
        updates["error"] = AuditAgentError(
            code=(result.error.code if result.error else "validation_failed"),
            message=(
                result.error.message
                if result.error
                else "Validation agent failed"
            ),
            agent="validation_agent",
        )
    return updates


async def persist_validation_node(
    state: AuditGraphState,
    *,
    tools: AuditTools,
) -> dict[str, Any]:
    request = state["request"]
    row_id = state.get("agent_response_id")
    validation = state.get("validation")
    if not request.persist or row_id is None or validation is None:
        return {}
    warnings = list(state.get("persist_warnings") or [])
    try:
        await tools.store_validation_result(row_id=row_id, result=validation)
    except Exception as exc:
        warnings.append(f"persist: failed to store validation result ({exc})")
    return {"persist_warnings": warnings}


async def policy_node(
    state: AuditGraphState,
    *,
    run_policy: Callable[..., Any],
) -> dict[str, Any]:
    if state.get("error") is not None or state.get("extraction") is None:
        return {}
    try:
        policy_request = to_policy_evaluation_request(
            state["extraction"],
            claim_id=state["request"].claim_id,
        )
        result = await run_policy(policy_request)
    except Exception as exc:
        return {
            "error": AuditAgentError(
                code=getattr(exc, "code", "policy_failed"),
                message=str(exc),
                agent="policy_rag_agent",
            )
        }
    if not isinstance(result, PolicyAgentResult):
        result = PolicyAgentResult.model_validate(result)
    updates: dict[str, Any] = {"policy": result}
    if result.status == PolicyAgentStatus.ERROR:
        updates["error"] = AuditAgentError(
            code=(result.error.code if result.error else "policy_failed"),
            message=(
                result.error.message if result.error else "Policy agent failed"
            ),
            agent="policy_rag_agent",
        )
    return updates


async def persist_policy_node(
    state: AuditGraphState,
    *,
    tools: AuditTools,
) -> dict[str, Any]:
    request = state["request"]
    row_id = state.get("agent_response_id")
    policy = state.get("policy")
    if not request.persist or row_id is None or policy is None:
        return {}
    warnings = list(state.get("persist_warnings") or [])
    try:
        await tools.store_policy_result(row_id=row_id, result=policy)
    except Exception as exc:
        warnings.append(f"persist: failed to store policy result ({exc})")
    return {"persist_warnings": warnings}


async def aggregate_node(
    state: AuditGraphState,
    *,
    llm_client: Any,
) -> dict[str, Any]:
    validation = state.get("validation")
    policy = state.get("policy")
    error = state.get("error")
    recommendation = decide_recommendation(validation, policy)
    confidence = overall_confidence(
        validation, policy, errored=error is not None
    )
    val_output = validation.output if validation is not None else None
    pol_output = policy.output if policy is not None else None
    validation_violation = format_validation_violation(val_output)
    policy_violation = format_policy_violation(pol_output)
    warnings: list[str] = []
    if val_output is not None:
        warnings.extend(val_output.warnings)
    if pol_output is not None:
        warnings.extend(pol_output.warnings)
    if error is not None:
        warnings.append(f"{_error_agent(error)}: {_error_message(error)}")
    warnings.extend(state.get("persist_warnings") or [])

    notes, reasons = await _summarize(
        llm_client,
        recommendation=recommendation,
        validation_violation=validation_violation,
        policy_violation=policy_violation,
        validation=validation,
        policy=policy,
        error=error,
    )

    context = state.get("context")
    claim_id = state["request"].claim_id
    output = AuditResult(
        claim_id=claim_id,
        recommendation=recommendation,
        reasons=reasons,
        extraction=state.get("extraction"),
        validation=val_output,
        policy=pol_output,
        references=list(pol_output.references) if pol_output else [],
        warnings=warnings,
        confidence=confidence,
        validation_violation=validation_violation,
        policy_violation=policy_violation,
        notes=notes,
        employee=context.employee if context else None,
        account=context.account if context else None,
    )
    status = (
        AuditAgentStatus.ERROR if error is not None else AuditAgentStatus.SUCCESS
    )
    return {
        "result": AuditAgentResult(
            status=status,
            output=output,
            error=error,
        )
    }


async def persist_final_node(
    state: AuditGraphState,
    *,
    tools: AuditTools,
) -> dict[str, Any]:
    request = state["request"]
    row_id = state.get("agent_response_id")
    result = state.get("result")
    if (
        not request.persist
        or row_id is None
        or result is None
        or result.output is None
    ):
        return {}
    try:
        await tools.store_audit_result(row_id=row_id, result=result.output)
    except Exception as exc:
        extra = f"persist: failed to store audit result ({exc})"
        warnings = list(state.get("persist_warnings") or [])
        warnings.append(extra)
        if result.output is not None:
            result.output.warnings = list(result.output.warnings) + [extra]
        return {"persist_warnings": warnings, "result": result}
    return {}


def route_after_load(state: AuditGraphState) -> str:
    persist = bool(state.get("request") and state["request"].persist)
    missing = _error_code(state.get("error")) == MISSING_RECEIPT_CODE
    if persist:
        return "set_status"
    if missing:
        return "aggregate"
    return "extract"


def route_after_status(state: AuditGraphState) -> str:
    if _error_code(state.get("error")) == MISSING_RECEIPT_CODE:
        return "aggregate"
    return "extract"


def route_after_extract(state: AuditGraphState) -> str:
    if state.get("error") is not None:
        return "aggregate"
    return "validate"


def route_after_validate(state: AuditGraphState) -> str:
    if state.get("error") is not None:
        return "aggregate"
    return "policy"


def build_audit_agent(
    *,
    tools: AuditTools,
    run_ocr: Callable[..., Any],
    run_validation: Callable[..., Any],
    run_policy: Callable[..., Any],
    llm_client: Any,
) -> CompiledStateGraph:
    graph = StateGraph(AuditGraphState)
    graph.add_node("load_context", partial(load_context_node, tools=tools))
    graph.add_node("set_status", partial(set_status_node, tools=tools))
    graph.add_node("extract", partial(extract_node, run_ocr=run_ocr))
    graph.add_node("validate", partial(validate_node, run_validation=run_validation))
    graph.add_node(
        "persist_validation", partial(persist_validation_node, tools=tools)
    )
    graph.add_node("policy", partial(policy_node, run_policy=run_policy))
    graph.add_node("persist_policy", partial(persist_policy_node, tools=tools))
    graph.add_node("aggregate", partial(aggregate_node, llm_client=llm_client))
    graph.add_node("persist_final", partial(persist_final_node, tools=tools))

    graph.add_edge(START, "load_context")
    graph.add_conditional_edges(
        "load_context",
        route_after_load,
        {
            "set_status": "set_status",
            "extract": "extract",
            "aggregate": "aggregate",
        },
    )
    graph.add_conditional_edges(
        "set_status",
        route_after_status,
        {"extract": "extract", "aggregate": "aggregate"},
    )
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {"validate": "validate", "aggregate": "aggregate"},
    )
    graph.add_edge("validate", "persist_validation")
    graph.add_conditional_edges(
        "persist_validation",
        route_after_validate,
        {"policy": "policy", "aggregate": "aggregate"},
    )
    graph.add_edge("policy", "persist_policy")
    graph.add_edge("persist_policy", "aggregate")
    graph.add_edge("aggregate", "persist_final")
    graph.add_edge("persist_final", END)
    return graph.compile()


async def run_audit_agent(
    request: AuditRequest,
    *,
    tools: AuditTools,
    run_ocr: Callable[..., Any],
    run_validation: Callable[..., Any] | None = None,
    run_policy: Callable[..., Any] | None = None,
    llm_client: Any,
    receipt_bytes: bytes | None = None,
    mime_type: str | None = None,
    context_service: Any = None,
    rag_service: Any = None,
) -> AuditAgentResult:
    """Run the Audit Agent once, returning its envelope result."""

    async def _run_validation(validation_request):
        if run_validation is not None:
            return await run_validation(validation_request)
        return await run_validation_agent(
            validation_request,
            context_service=context_service,
            llm_client=llm_client,
        )

    async def _run_policy(policy_request):
        if run_policy is not None:
            return await run_policy(policy_request)
        return await run_policy_agent(
            policy_request,
            rag_service=rag_service,
            llm_client=llm_client,
        )

    graph = build_audit_agent(
        tools=tools,
        run_ocr=run_ocr,
        run_validation=_run_validation,
        run_policy=_run_policy,
        llm_client=llm_client,
    )
    try:
        final_state = await graph.ainvoke(
            {
                "request": request,
                "receipt_bytes": receipt_bytes,
                "mime_type": mime_type,
            }
        )
    except (ClaimNotFoundError, EmployeeNotFoundError):
        raise
    except Exception as exc:
        return AuditAgentResult(
            status=AuditAgentStatus.ERROR,
            error=AuditAgentError(
                code="audit_failed",
                message=f"Audit agent failed: {exc}",
            ),
        )
    result = final_state.get("result")
    if result is None:
        return AuditAgentResult(
            status=AuditAgentStatus.ERROR,
            error=AuditAgentError(
                code=EMPTY_RESULT_CODE,
                message="Audit agent finished without producing a result",
            ),
        )
    return result


async def _summarize(
    llm_client: Any,
    *,
    recommendation: AuditRecommendation,
    validation_violation: str | None,
    policy_violation: str | None,
    validation: ValidationAgentResult | None,
    policy: PolicyAgentResult | None,
    error: AuditAgentError | None,
) -> tuple[str, list[str]]:
    fallback_notes = _fallback_notes(
        recommendation, validation_violation, policy_violation, error
    )
    fallback_reasons = _fallback_reasons(
        recommendation, validation_violation, policy_violation
    )
    payload = {
        "recommendation": recommendation.value,
        "validation_violation": validation_violation,
        "policy_violation": policy_violation,
        "validation_summary": (
            validation.output.summary
            if validation is not None and validation.output is not None
            else None
        ),
        "policy_summary": (
            policy.output.summary
            if policy is not None and policy.output is not None
            else None
        ),
        "error": error.model_dump() if error is not None else None,
    }
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(
                llm_client.generate_structured,
                system_instruction=get_audit_system_prompt(),
                contents=json.dumps(payload, default=str),
                response_schema=AuditAggregationOutput,
            ),
            timeout=settings.gemini_llm_timeout_seconds,
        )
        parsed = AuditAggregationOutput.model_validate(raw)
        notes = parsed.notes.strip() or fallback_notes
        reasons = parsed.reasons or fallback_reasons
        return notes, reasons
    except (asyncio.TimeoutError, GeminiLLMError, ValidationError, Exception):
        return fallback_notes, fallback_reasons


def _fallback_notes(
    recommendation: AuditRecommendation,
    validation_violation: str | None,
    policy_violation: str | None,
    error: AuditAgentError | None,
) -> str:
    parts = [f"Recommendation: {recommendation.value}."]
    if validation_violation:
        parts.append(f"Validation: {validation_violation}.")
    if policy_violation:
        parts.append(f"Policy: {policy_violation}.")
    if error is not None:
        parts.append(f"Workflow issue ({error.agent}): {error.message}.")
    if not validation_violation and not policy_violation and error is None:
        parts.append("No blocking validation or policy violations were recorded.")
    return " ".join(parts)


def _fallback_reasons(
    recommendation: AuditRecommendation,
    validation_violation: str | None,
    policy_violation: str | None,
) -> list[str]:
    reasons = [f"Deterministic recommendation is {recommendation.value}."]
    if validation_violation:
        reasons.append(validation_violation)
    if policy_violation:
        reasons.append(policy_violation)
    return reasons
