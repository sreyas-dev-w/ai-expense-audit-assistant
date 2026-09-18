"""Audit assessment step — the Audit Agent's LLM reasoning node.

After the OCR, Policy RAG and Validation stages have produced their structured
outputs on the claim, the audit assessment step invokes the LLM once more to
summarise those three stage outputs into a single, decision-support
recommendation. It is deliberately narrow:

- input: the claim context, OCR extraction, Policy result and Validation result
  (all already Pydantic-validated elsewhere),
- output: ``AuditAssessment`` (summary, ai_decision, priority, confidence).

The step never reads or writes the database itself — persistence is handled by
the orchestrator's tools after a successful LLM response, and the
``validation_response`` / ``policy_response`` columns are never overwritten
(``docs/agents/audit-agent.md``).
"""
import asyncio
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.assessment import AuditAssessment

_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "audit_assessment_prompt.txt"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_audit_assessment_system_prompt() -> str:
    return _PROMPT_FILE.read_text()


def build_assessment_contents(
    *,
    claim: Any,
    extraction: Any,
    policy_result: Any,
    validation_result: Any,
) -> str:
    """Build the LLM ``contents`` payload from the three stage outputs.

    Mirrors the Policy RAG pattern (``_build_contents``): a markdown-framed,
    JSON-serialised snapshot of the structured state. ``None``/errored envelope
    stages are surfaced explicitly so the LLM reasons only on what exists.
    """
    sections = [
        ("# Claim under review", _json(claim)),
        ("# OCR extraction", _json(extraction)),
        ("# Policy agent result", _result_json(policy_result)),
        ("# Validation agent result", _result_json(validation_result)),
    ]
    lines: list[str] = []
    for heading, body in sections:
        lines.append(heading)
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def _result_json(result: Any) -> str:
    """Render an agent envelope's structured output (or its error) as JSON."""
    if result is None:
        return json.dumps(
            {"status": "unavailable", "note": "No result was produced for this stage."},
            indent=2,
        )
    output = getattr(result, "output", None)
    if output is not None:
        return _json(output)
    error = getattr(result, "error", None)
    if error is not None:
        return json.dumps(
            {"status": "error", "code": getattr(error, "code", None),
             "message": str(getattr(error, "message", error))},
            indent=2,
        )
    return _json(result)


def _json(value: Any) -> str:
    if value is None:
        return json.dumps({"status": "unavailable"}, indent=2)
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(), default=str, indent=2)
    return json.dumps(value, default=str, indent=2)


async def run_audit_assessment(
    *,
    claim: Any,
    extraction: Any,
    policy_result: Any,
    validation_result: Any,
    llm_client: Any,
) -> AuditAssessment:
    """Invoke the LLM and return a validated ``AuditAssessment``.

    The LLM output is untrusted until Pydantic-validated
    (``docs/backend/llm-integration.md``). Errors (timeout, Gemini client
    failures, invalid output) are surfaced to the caller — the orchestrator
    node degrades gracefully to the deterministic aggregation on any of them.
    """
    raw = await asyncio.wait_for(
        asyncio.to_thread(
            llm_client.generate_structured,
            system_instruction=get_audit_assessment_system_prompt(),
            contents=build_assessment_contents(
                claim=claim,
                extraction=extraction,
                policy_result=policy_result,
                validation_result=validation_result,
            ),
            response_schema=AuditAssessment,
        ),
        timeout=settings.gemini_llm_timeout_seconds,
    )
    return AuditAssessment.model_validate(raw)