"""Unit tests for the Audit Agent tools over the in-memory FakeSession."""
from decimal import Decimal

import pytest

from app.models.enums import (
    AIDecision,
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
)
from app.tools.base import AuditToolError
from app.tools.claim_tools import (
    GetClaimTool,
    UpdateAuditRunStatusTool,
    UpdateClaimResultTool,
)
from app.tools.receipt_tools import FetchReceiptTool
from app.tools.response_tools import StoreAgentResponseTool, StoreExtractionTool
from app.schemas.policy import (
    PolicyDecision,
    PolicySeverity,
    PolicyViolation,
    PolicyAgentOutput,
)
from tests.conftest import (
    build_audit_tools_for,
    make_employee_row,
    make_food_claim_row,
    make_policy_result,
    make_fake_session_factory,
)

CLAIM_ID = 101


def _store(with_claim: bool = True):
    store = {}
    if with_claim:
        store[("claims", CLAIM_ID)] = make_food_claim_row()
    store[("employees", "EMP-001")] = make_employee_row()
    return store


async def test_get_claim_returns_audit_context():
    store = _store()
    factory = make_fake_session_factory(store)

    context = await GetClaimTool(session_factory=factory).run(claim_id=CLAIM_ID)

    assert context.claim_id == CLAIM_ID
    assert context.employee_id == "EMP-001"
    assert context.employee_job_level == "L2"
    assert context.category_data["merchant_name"] == "Zulu Bistro"


async def test_get_claim_missing_returns_none():
    store = _store(with_claim=False)
    factory = make_fake_session_factory(store)

    assert await GetClaimTool(session_factory=factory).run(claim_id=CLAIM_ID) is None


async def test_update_run_status_persists_transition():
    store = _store()
    factory = make_fake_session_factory(store)

    result = await UpdateAuditRunStatusTool(session_factory=factory).run(
        claim_id=CLAIM_ID,
        claim_status=ClaimStatus.IN_AUDIT,
        ai_run_status=AIRunStatus.RUNNING,
    )

    assert result.updated_fields == ["status", "ai_run_status"]
    claim = store[("claims", CLAIM_ID)]
    assert claim.status == ClaimStatus.IN_AUDIT
    assert claim.ai_run_status == AIRunStatus.RUNNING


async def test_update_claim_result_persists_decision_priority_and_notes():
    store = _store()
    factory = make_fake_session_factory(store)

    result = await UpdateClaimResultTool(session_factory=factory).run(
        claim_id=CLAIM_ID,
        ai_decision=AIDecision.REVIEW,
        priority=ClaimPriority.HIGH,
        notes="AI summary note",
    )

    claim = store[("claims", CLAIM_ID)]
    assert claim.ai_decision == AIDecision.REVIEW
    assert claim.priority == ClaimPriority.HIGH
    assert claim.ai_run_status == AIRunStatus.COMPLETED
    # auditer_notes stays None: it is the manager's manual field, not the AI's.
    assert claim.auditer_notes is None
    assert result.updated_fields == [
        "ai_decision",
        "priority",
        "ai_run_status",
        "agent_response_notes",
    ]
    response = store[("agent_response", 1)]
    assert response.notes == "AI summary note"


async def test_store_extraction_persists_category_data():
    store = _store()
    factory = make_fake_session_factory(store)
    category_data = dict(store[("claims", CLAIM_ID)].category_data)
    category_data["merchant_name"] = "Updated Bistro"

    result = await StoreExtractionTool(session_factory=factory).run(
        claim_id=CLAIM_ID, category_data=category_data
    )

    assert result.updated_fields == ["category_data"]
    assert store[("claims", CLAIM_ID)].category_data["merchant_name"] == "Updated Bistro"


async def test_store_agent_response_creates_row_when_missing():
    store = _store()
    next_ids = {}
    factory = make_fake_session_factory(store, next_ids)
    policy_result = make_policy_result()

    record = await StoreAgentResponseTool(session_factory=factory).run(
        claim_id=CLAIM_ID, policy_result=policy_result
    )

    assert record.id == 1
    assert record.claim_id == CLAIM_ID
    row = store[("agent_response", 1)]
    assert row.policy_response["output"]["decision"] == "FLAG_FOR_REVIEW"
    assert row.confidence_score == Decimal("0.85")

    # Re-running the tool updates the same row instead of inserting another.
    record2 = await StoreAgentResponseTool(session_factory=factory).run(
        claim_id=CLAIM_ID, policy_result=policy_result
    )
    assert record2.id == 1
    agent_response_rows = [k for k in store if k[0] == "agent_response"]
    assert len(agent_response_rows) == 1


async def test_store_agent_response_updates_existing_row():
    from app.models.agent_response import AgentResponse

    store = _store()
    store[("agent_response", 5)] = AgentResponse(id=5, claim_id=CLAIM_ID)
    factory = make_fake_session_factory(store)
    policy_result = make_policy_result()
    validation_result = {"validated": True}

    record = await StoreAgentResponseTool(session_factory=factory).run(
        claim_id=CLAIM_ID,
        policy_result=policy_result,
        validation_result=validation_result,
    )

    assert record.id == 5
    assert record.claim_id == CLAIM_ID
    row = store[("agent_response", 5)]
    assert row.policy_response["output"]["decision"] == "FLAG_FOR_REVIEW"
    assert row.validation_response == {"validated": True}
    assert row.confidence_score == Decimal("0.85")
    agent_response_rows = [k for k in store if k[0] == "agent_response"]
    assert len(agent_response_rows) == 1


@pytest.mark.parametrize(
    "tool",
    [
        lambda f: UpdateAuditRunStatusTool(session_factory=f).run(
            claim_id=CLAIM_ID,
            claim_status=ClaimStatus.IN_AUDIT,
            ai_run_status=AIRunStatus.RUNNING,
        ),
        lambda f: UpdateClaimResultTool(session_factory=f).run(
            claim_id=CLAIM_ID,
            ai_decision=AIDecision.APPROVE,
            priority=ClaimPriority.LOW,
        ),
        lambda f: StoreExtractionTool(session_factory=f).run(
            claim_id=CLAIM_ID, category_data={"meal_type": "Dinner"}
        ),
    ],
)
async def test_write_tools_raise_not_found(tool):
    store = _store(with_claim=False)
    factory = make_fake_session_factory(store)
    with pytest.raises(AuditToolError) as exc_info:
        await tool(factory)
    assert exc_info.value.code == "claim_not_found"


async def test_fetch_receipt_local_jpeg(tmp_path):
    path = tmp_path / "receipt.jpg"
    path.write_bytes(b"fake-jpeg")

    data = await FetchReceiptTool().run(receipt_url=str(path))

    assert data.content == b"fake-jpeg"
    assert data.mime_type == "image/jpeg"


async def test_fetch_receipt_missing_file(tmp_path):
    with pytest.raises(AuditToolError) as exc_info:
        await FetchReceiptTool().run(
            receipt_url=str(tmp_path / "does-not-exist.jpg")
        )
    assert exc_info.value.code == "receipt_read_failed"


async def test_fetch_receipt_unsupported_format(tmp_path):
    path = tmp_path / "receipt.txt"
    path.write_bytes(b"hello")
    with pytest.raises(AuditToolError) as exc_info:
        await FetchReceiptTool().run(receipt_url=str(path))
    assert exc_info.value.code == "unsupported_receipt_format"


async def test_fetch_receipt_empty_content(tmp_path):
    path = tmp_path / "empty.jpg"
    path.write_bytes(b"")
    with pytest.raises(AuditToolError) as exc_info:
        await FetchReceiptTool().run(receipt_url=str(path))
    assert exc_info.value.code == "empty_receipt"


def test_build_audit_tools_registry():
    tools = build_audit_tools_for(_store())
    assert set(tools) == {
        "get_claim",
        "fetch_receipt",
        "update_audit_run_status",
        "store_extraction",
        "store_agent_response",
        "update_claim_result",
    }


def test_store_agent_response_serializes_policy_output():
    output = PolicyAgentOutput(
        decision=PolicyDecision.APPROVE,
        confidence=0.9,
        violations=[
            PolicyViolation(
                policy_reference="S1",
                severity=PolicySeverity.INFO,
                description="ok",
            )
        ],
    )
    assert output.model_dump(mode="json")["decision"] == "APPROVE"
    assert output.model_dump(mode="json")["violations"][0]["severity"] == "info"