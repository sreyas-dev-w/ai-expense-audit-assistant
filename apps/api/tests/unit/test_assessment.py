"""Unit tests for the Audit Agent's LLM assessment step.

``run_audit_assessment`` must produce a Pydantic-validated ``AuditAssessment``
from LLM output and surface every failure mode (timeout, client error, invalid
JSON) so the orchestrator can degrade gracefully
(``docs/backend/llm-integration.md``).
"""
import asyncio
import time

import pytest
from pydantic import ValidationError

from app.agents.audit_assessment import (
    build_assessment_contents,
    run_audit_assessment,
)
from app.models.enums import AIDecision, ClaimPriority
from app.schemas.assessment import AuditAssessment
from app.services.gemini_client import GeminiLLMError
from tests.conftest import (
    StubLLMClient,
    make_food_audit_context,
    make_policy_result,
    sample_food_extraction,
)


def _default_payload() -> dict:
    return {
        "summary": "The dinner claim exceeds the per-meal limit; review needed.",
        "ai_decision": "REVIEW",
        "priority": "MEDIUM",
        "confidence": 0.8,
    }


def _kwargs():
    return {
        "claim": make_food_audit_context(),
        "extraction": sample_food_extraction(),
        "policy_result": make_policy_result(),
        "validation_result": None,
    }


async def test_run_audit_assessment_validates_llm_output():
    llm = StubLLMClient(payload=_default_payload())

    assessment = await run_audit_assessment(**_kwargs(), llm_client=llm)

    assert isinstance(assessment, AuditAssessment)
    assert assessment.summary == _default_payload()["summary"]
    assert assessment.ai_decision == AIDecision.REVIEW
    assert assessment.priority == ClaimPriority.MEDIUM
    assert assessment.confidence == 0.8
    # The contents passed to the LLM framed all the stage outputs.
    assert "# Claim under review" in llm.last_contents
    assert "# Policy agent result" in llm.last_contents
    assert "# Validation agent result" in llm.last_contents


async def test_run_audit_assessment_rejects_invalid_llm_output():
    payload = {"summary": "Partial", "confidence": 0.5}  # ai_decision/priority omitted
    llm = StubLLMClient(payload=payload)

    with pytest.raises(ValidationError):
        await run_audit_assessment(**_kwargs(), llm_client=llm)


async def test_run_audit_assessment_raises_client_errors():
    llm = StubLLMClient(error=GeminiLLMError("down", code="gemini_unavailable"))

    with pytest.raises(GeminiLLMError):
        await run_audit_assessment(**_kwargs(), llm_client=llm)


async def test_run_audit_assessment_times_out(monkeypatch):
    class SlowLLM:
        def generate_structured(self, **kwargs):
            time.sleep(0.5)
            return _default_payload()

    monkeypatch.setattr(
        "app.agents.audit_assessment.settings.gemini_llm_timeout_seconds", 0.05
    )

    with pytest.raises(asyncio.TimeoutError):
        await run_audit_assessment(**_kwargs(), llm_client=SlowLLM())


async def test_run_audit_assessment_coerces_enum_case():
    payload = dict(_default_payload())
    payload["ai_decision"] = "APPROVE"
    payload["priority"] = "urgent"
    llm = StubLLMClient(payload=payload)

    assessment = await run_audit_assessment(**_kwargs(), llm_client=llm)

    assert assessment.ai_decision == AIDecision.APPROVE
    assert assessment.priority == ClaimPriority.URGENT


def test_build_contents_renders_stored_payload_dicts():
    contents = build_assessment_contents(
        claim=make_food_audit_context(),
        extraction=None,
        policy_result=None,
        validation_result={
            "status": "error",
        },
    )

    assert "unavailable" in contents
    assert '"status": "error"' in contents