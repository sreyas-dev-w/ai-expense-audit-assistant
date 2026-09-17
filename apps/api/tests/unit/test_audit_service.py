"""Unit tests for the deterministic audit aggregation (decision-support logic).

``aggregate_audit_result`` folds the stage outputs into the persisted
recommendation — decision mapping, priority derivation, warnings and notes —
and must never crash on incomplete/errored stages (``docs/backend/auditability.md``).
"""
from app.models.enums import AIDecision, AIRunStatus, ClaimPriority, ClaimStatus
from app.schemas.policy import (
    PolicyAgentError,
    PolicyAgentResult,
    PolicyAgentStatus,
    PolicyDecision,
)
from app.services.audit_service import aggregate_audit_result
from tests.conftest import (
    make_food_audit_context,
    make_policy_result,
    sample_food_extraction,
)


def _state(**overrides) -> dict:
    state = {
        "claim_id": 101,
        "claim": make_food_audit_context(),
        "extraction": sample_food_extraction(),
        "category_data": {"merchant_name": "Zulu Bistro"},
        "policy_result": make_policy_result(),
        "validation_skipped": True,
        "errors": [],
    }
    state.update(overrides)
    return state


def test_flag_for_review_maps_to_review_medium():
    result = aggregate_audit_result(_state())

    assert result.claim_id == 101
    assert result.ai_decision == AIDecision.REVIEW
    assert result.priority == ClaimPriority.MEDIUM
    assert result.status == ClaimStatus.IN_AUDIT
    assert result.ai_run_status == AIRunStatus.COMPLETED
    assert result.confidence == 0.85
    assert result.reasons and "per-meal limit" in result.reasons[0]
    assert result.errors == []
    assert result.validation is None
    assert result.extraction_summary is not None
    assert result.extraction_summary.merchant_name == "Zulu Bistro"
    assert result.notes and "review" in result.notes


def test_approve_maps_to_approve_low():
    result = aggregate_audit_result(
        _state(policy_result=make_policy_result(decision=PolicyDecision.APPROVE))
    )
    assert result.ai_decision == AIDecision.APPROVE
    assert result.priority == ClaimPriority.LOW


def test_reject_maps_to_reject_high():
    result = aggregate_audit_result(
        _state(policy_result=make_policy_result(decision=PolicyDecision.REJECT))
    )
    assert result.ai_decision == AIDecision.REJECT
    assert result.priority == ClaimPriority.HIGH


def test_warnings_bump_priority():
    result = aggregate_audit_result(
        _state(
            policy_result=make_policy_result(
                warnings=["no date", "tax zero"]
            )
        )
    )
    assert result.priority == ClaimPriority.HIGH


def test_many_warnings_escalate_to_urgent():
    result = aggregate_audit_result(
        _state(
            policy_result=make_policy_result(
                warnings=["w1", "w2", "w3"]
            )
        )
    )
    assert result.priority == ClaimPriority.URGENT


def test_policy_error_envelope_still_completes_as_review():
    result = aggregate_audit_result(
        _state(
            policy_result=PolicyAgentResult(
                status=PolicyAgentStatus.ERROR,
                error=PolicyAgentError(
                    code="gemini_unavailable", message="Gemini API unavailable"
                ),
            )
        )
    )

    assert result.ai_decision == AIDecision.REVIEW
    assert result.ai_run_status == AIRunStatus.COMPLETED
    assert result.policy is None
    assert result.errors[0].code == "gemini_unavailable"
    assert result.errors[0].agent == "policy_rag_agent"
    assert any("policy" in w.lower() for w in result.warnings)


def test_missing_policy_result_defaults_to_manual_review():
    result = aggregate_audit_result(_state(policy_result=None))

    assert result.ai_decision == AIDecision.REVIEW
    assert result.ai_run_status == AIRunStatus.COMPLETED
    assert any("manually" in w.lower() for w in result.warnings)


def test_non_receipt_confirmations_add_warning():
    extraction = sample_food_extraction()
    extraction.is_receipt = False
    result = aggregate_audit_result(_state(extraction=extraction))
    assert any("receipt" in w.lower() for w in result.warnings)


def test_missing_claim_amount_adds_warning():
    extraction = sample_food_extraction()
    extraction.claim_amount = None
    result = aggregate_audit_result(_state(extraction=extraction))
    assert any("amount" in w.lower() for w in result.warnings)


def test_aggregation_message_mentioning_both_reasons_and_warnings():
    result = aggregate_audit_result(
        _state(
            policy_result=make_policy_result(
                warnings=["vendor not on approved list"]
            )
        )
    )
    assert "Reasons:" in result.notes
    assert "Warnings:" in result.notes


def test_grounding_references_are_preserved():
    result = aggregate_audit_result(_state())
    assert [r.chunk_id for r in result.grounding_references] == [1]