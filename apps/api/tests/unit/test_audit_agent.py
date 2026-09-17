"""Graph-level tests for the Audit Agent orchestration workflow.

These exercise the compiled LangGraph end-to-end against the real tools (over an
in-memory FakeSession store) with fake OCR/Policy/Validation sub-agents, so the
status transitions, persistence and error routing are all covered without any
external service (``docs/agents/orchestration.md``).
"""
from app.agents.audit_agent import build_audit_agent, run_audit_agent
from app.models.enums import (
    AIDecision,
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
)
from app.schemas.policy import (
    FoodMealsPolicyEvaluation,
    PolicyAgentError,
    PolicyAgentResult,
    PolicyAgentStatus,
)
from app.services.audit_service import aggregate_audit_result
from tests.conftest import (
    FakeOcrAgent,
    FakePolicyRunner,
    FakeValidationRunner,
    build_audit_tools_for,
    make_employee_row,
    make_food_claim_row,
)

CLAIM_ID = 101


def _build_graph(store, next_ids=None, **overrides):
    tools = build_audit_tools_for(store, next_ids)
    return build_audit_agent(
        ocr_agent=overrides.pop("ocr", None) or FakeOcrAgent(),
        policy_runner=overrides.pop("policy", None) or FakePolicyRunner(),
        aggregator=overrides.pop("aggregator", aggregate_audit_result),
        tools=tools,
        validation_runner=overrides.pop("validation_runner", None),
    )


def _store_with_claim(tmp_path, *, claim: dict | None = None, **kwargs):
    store = {}
    next_ids = {}
    claim_row = make_food_claim_row(CLAIM_ID) if claim is None else None
    if claim_row is not None:
        store[("claims", CLAIM_ID)] = claim_row
    store[("employees", "EMP-001")] = make_employee_row()
    return store, next_ids


async def test_happy_path_completes_and_persists(tmp_path):
    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()
    next_ids = {}

    ocr = FakeOcrAgent()
    policy = FakePolicyRunner()
    graph = _build_graph(store, next_ids, ocr=ocr, policy=policy)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.claim_id == CLAIM_ID
    assert result.status == ClaimStatus.IN_AUDIT
    assert result.ai_run_status == AIRunStatus.COMPLETED
    assert result.ai_decision == AIDecision.REVIEW
    assert result.priority == ClaimPriority.MEDIUM
    assert result.confidence == 0.85
    assert result.reasons
    assert result.policy is not None
    assert result.grounding_references[0].chunk_id == 1
    assert result.extraction_summary is not None
    assert result.errors == []

    claim = store[("claims", CLAIM_ID)]
    assert claim.status == ClaimStatus.IN_AUDIT
    assert claim.ai_run_status == AIRunStatus.COMPLETED
    assert claim.ai_decision == AIDecision.REVIEW
    assert claim.priority == ClaimPriority.MEDIUM
    assert claim.auditer_notes and "review" in claim.auditer_notes
    assert claim.category_data["merchant_name"] == "Zulu Bistro"

    response = store[("agent_response", 1)]
    assert response.claim_id == CLAIM_ID
    assert response.policy_response["output"]["decision"] == "FLAG_FOR_REVIEW"
    assert response.confidence_score is not None

    final_state = await graph.ainvoke({"claim_id": CLAIM_ID})
    assert final_state["validation_skipped"] is True
    assert isinstance(policy.last_request, FoodMealsPolicyEvaluation)
    assert policy.last_request.claim.employee_id == "EMP-001"
    assert policy.last_request.category_data.merchant_name == "Zulu Bistro"
    assert ocr.last_kwargs["expense_category"] == "FOOD_MEALS"


async def test_validation_runner_is_called_when_injected(tmp_path):
    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()
    next_ids = {}

    validation = FakeValidationRunner(result={"validated": True})
    graph = _build_graph(store, next_ids, validation_runner=validation)

    final_state = await graph.ainvoke({"claim_id": CLAIM_ID})
    assert validation.called is True
    assert final_state["validation_skipped"] is False
    assert final_state["validation_result"] == {"validated": True}
    assert store[("agent_response", 1)].validation_response == {"validated": True}


async def test_missing_claim_marks_run_failed():
    store = {}
    next_ids = {}
    graph = _build_graph(store, next_ids)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.status == ClaimStatus.SUBMITTED
    assert result.ai_run_status == AIRunStatus.FAILED
    assert result.errors[0].code == "claim_not_found"
    assert "claim_not_found" in result.warnings[0]


async def test_missing_receipt_url_marks_run_failed():
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=None)}
    store[("employees", "EMP-001")] = make_employee_row()
    graph = _build_graph(store, {})

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_run_status == AIRunStatus.FAILED
    assert result.status == ClaimStatus.SUBMITTED
    assert result.errors[0].code == "missing_receipt_url"
    assert store[("claims", CLAIM_ID)].ai_run_status == AIRunStatus.FAILED
    assert store[("claims", CLAIM_ID)].status == ClaimStatus.SUBMITTED


async def test_ocr_failure_routes_to_mark_failed(tmp_path):
    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()

    ocr = FakeOcrAgent(error=RuntimeError("gemini down"))
    graph = _build_graph(store, {}, ocr=ocr)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_run_status == AIRunStatus.FAILED
    assert result.status == ClaimStatus.SUBMITTED
    assert result.errors[0].code == "ocr_failed"
    assert result.errors[0].agent == "ocr_extraction_agent"
    assert result.errors[0].retryable is True


async def test_category_mismatch_fails_run(tmp_path):
    from app.schemas.extraction import OtherExtraction

    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()

    ocr = FakeOcrAgent(
        extraction=OtherExtraction(
            is_receipt=True,
            expense_category="Stationery",
            merchant_name="Stationery Co",
            line_items=[],
        )
    )
    graph = _build_graph(store, {}, ocr=ocr)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_run_status == AIRunStatus.FAILED
    assert result.errors[0].code == "category_mismatch"
    assert result.errors[0].retryable is False


async def test_policy_error_envelope_is_decision_support_not_failure(tmp_path):
    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()
    next_ids = {}

    policy = FakePolicyRunner(
        result=PolicyAgentResult(
            status=PolicyAgentStatus.ERROR,
            error=PolicyAgentError(
                code="gemini_unavailable",
                message="Gemini API unavailable",
            ),
        )
    )
    graph = _build_graph(store, next_ids, policy=policy)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_run_status == AIRunStatus.COMPLETED
    assert result.status == ClaimStatus.IN_AUDIT
    assert result.ai_decision == AIDecision.REVIEW
    assert result.policy is None
    assert result.errors[0].code == "gemini_unavailable"
    assert any("policy" in w.lower() for w in result.warnings)

    claim = store[("claims", CLAIM_ID)]
    assert claim.ai_run_status == AIRunStatus.COMPLETED
    assert store[("agent_response", 1)].policy_response["status"] == "error"


async def test_policy_runner_crash_routes_to_mark_failed(tmp_path):
    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()

    policy = FakePolicyRunner(error=RuntimeError("boom"))
    graph = _build_graph(store, {}, policy=policy)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_run_status == AIRunStatus.FAILED
    assert result.errors[0].code == "policy_agent_crashed"
    assert result.errors[0].retryable is True


async def test_aggregation_warnings_bump_priority(tmp_path):
    from tests.conftest import make_policy_result

    receipt = tmp_path / "receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    store = {("claims", CLAIM_ID): make_food_claim_row(receipt_url=str(receipt))}
    store[("employees", "EMP-001")] = make_employee_row()

    policy = FakePolicyRunner(
        result=make_policy_result(warnings=["no receipt date", "tax missing"])
    )
    graph = _build_graph(store, {}, policy=policy)

    result = await run_audit_agent(graph, CLAIM_ID)

    assert result.ai_decision == AIDecision.REVIEW
    assert result.priority == ClaimPriority.HIGH