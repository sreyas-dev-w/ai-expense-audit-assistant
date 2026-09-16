"""Unit tests for the Audit Agent parent graph."""
from decimal import Decimal

from app.agents.audit_agent import (
    build_audit_agent,
    decide_recommendation,
    overall_confidence,
    run_audit_agent,
)
from app.models.enums import ClaimPriority, ClaimStatus, Currency, ExpenseCategory
from app.schemas.audit import (
    AccountSnapshot,
    AuditAgentStatus,
    AuditContext,
    AuditRecommendation,
    AuditRequest,
    ClaimSnapshot,
    EmployeeSnapshot,
    ProjectSnapshot,
)
from app.schemas.extraction import OCRResponse
from app.schemas.policy import (
    PolicyAgentOutput,
    PolicyAgentResult,
    PolicyAgentStatus,
    PolicyDecision,
    PolicyViolation,
)
from app.schemas.validation import (
    ValidationAgentOutput,
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
    ValidationVerdict,
)
from app.services.validation_service import ClaimNotFoundError
from app.tools.audit_tools import format_policy_violation, format_validation_violation
from tests.unit.test_validation_rules import travel_request


def _context(**overrides) -> AuditContext:
    data = dict(
        claim=ClaimSnapshot(
            claim_id=3,
            employee_id="EMP-003",
            business_purpose="Client entertainment",
            merchant_name="Air India",
            category=ExpenseCategory.TRAVEL,
            category_data={
                "travel_type": "FLIGHT",
                "origin": "Trivandrum",
                "destination": "Kochi",
                "travel_date": "2026-08-19",
                "travel_class": "BUSINESS_CLASS",
                "ticket_number": "TRAVEL-0003",
            },
            project_code="CAPSTONE-001",
            claim_amount=Decimal("40000.00"),
            currency=Currency.INR,
            status=ClaimStatus.SUBMITTED,
            priority=ClaimPriority.MEDIUM,
            receipt_url=None,
        ),
        employee=EmployeeSnapshot(
            employee_id="EMP-003",
            employee_name="Arun Kumar",
            job_level="L3",
            is_manager=False,
            manager_id="EMP-001",
            project_code="CAPSTONE-001",
        ),
        manager=EmployeeSnapshot(
            employee_id="EMP-001",
            employee_name="Manager",
            job_level="L5",
            is_manager=True,
            manager_id=None,
            project_code="CAPSTONE-001",
        ),
        project=ProjectSnapshot(
            project_code="CAPSTONE-001",
            project_name="Capstone",
            account_id="ACC-001",
            project_lead_id="EMP-001",
        ),
        account=AccountSnapshot(
            account_id="ACC-001",
            account_name="Ops",
            fiscal_year=2026,
            budget_allocated=Decimal("1000000"),
            remaining_budget=Decimal("100000"),
            currency="INR",
        ),
    )
    data.update(overrides)
    return AuditContext(**data)


class StubTools:
    def __init__(self, context: AuditContext):
        self.context = context
        self.status = None
        self.row_id = 7
        self.calls: list[tuple] = []

    async def load_audit_context(self, claim_id: int) -> AuditContext:
        if claim_id != self.context.claim.claim_id:
            raise ClaimNotFoundError(claim_id)
        return self.context

    async def update_claim_status(self, claim_id, status):
        self.status = status
        self.calls.append(("status", status))
        return status

    async def create_run_row(self, claim_id: int) -> int:
        self.calls.append(("create_row", claim_id))
        return self.row_id

    async def store_validation_result(self, **kwargs):
        self.calls.append(("validation", kwargs))

    async def store_policy_result(self, **kwargs):
        self.calls.append(("policy", kwargs))

    async def store_audit_result(self, **kwargs):
        self.calls.append(("audit", kwargs))


class StubLLM:
    def __init__(self, payload=None, error=None):
        self._payload = payload or {
            "notes": "Recommend reject: amount mismatch and policy issue.",
            "reasons": ["Amount does not match the receipt."],
        }
        self._error = error
        self.last_contents = None

    def generate_structured(self, *, system_instruction, contents, response_schema):
        if self._error is not None:
            raise self._error
        self.last_contents = contents
        return dict(self._payload)


def _ocr_response() -> OCRResponse:
    req = travel_request()
    return OCRResponse(
        submission=req.submission,
        employee_context=req.employee_context,
        extraction=req.extraction,
    )


def _failing_validation() -> ValidationAgentResult:
    return ValidationAgentResult(
        status=ValidationAgentStatus.SUCCESS,
        output=ValidationAgentOutput(
            verdict=ValidationVerdict.FAIL,
            confidence=0.9,
            findings=[
                ValidationFinding(
                    rule_id="amount_mismatch",
                    severity=ValidationSeverity.BLOCKING,
                    category=ValidationFindingCategory.AMOUNT,
                    description="Claimed spend amount does not match the receipt total.",
                    detail="claimed 40000 vs extracted 51212.55",
                )
            ],
            summary="1 blocking validation issue(s).",
        ),
    )


def _passing_validation() -> ValidationAgentResult:
    return ValidationAgentResult(
        status=ValidationAgentStatus.SUCCESS,
        output=ValidationAgentOutput(
            verdict=ValidationVerdict.PASS,
            confidence=0.95,
            findings=[],
            summary="All checks passed.",
        ),
    )


def _policy_flag() -> PolicyAgentResult:
    return PolicyAgentResult(
        status=PolicyAgentStatus.SUCCESS,
        output=PolicyAgentOutput(
            decision=PolicyDecision.FLAG_FOR_REVIEW,
            confidence=0.8,
            violations=[
                PolicyViolation(
                    policy_reference="Travel 4.2",
                    description="Business class is not permitted at L3.",
                )
            ],
            reasons=["Travel class exceeds job-level entitlement."],
            summary="Travel class policy issue.",
        ),
    )


def _policy_approve() -> PolicyAgentResult:
    return PolicyAgentResult(
        status=PolicyAgentStatus.SUCCESS,
        output=PolicyAgentOutput(
            decision=PolicyDecision.APPROVE,
            confidence=0.88,
            violations=[],
            reasons=["Within policy."],
            summary="No policy violations.",
        ),
    )


async def _run(
    *,
    tools,
    ocr=None,
    validation=None,
    policy=None,
    llm=None,
    persist=True,
    receipt_bytes=b"receipt",
    mime_type="image/png",
    claim_id=3,
):
    ocr_calls = []

    async def run_ocr(**kwargs):
        ocr_calls.append(kwargs)
        if ocr is not None:
            return await ocr(**kwargs)
        return _ocr_response()

    async def run_validation(request):
        return validation if validation is not None else _failing_validation()

    async def run_policy(request):
        return policy if policy is not None else _policy_flag()

    graph = build_audit_agent(
        tools=tools,
        run_ocr=run_ocr,
        run_validation=run_validation,
        run_policy=run_policy,
        llm_client=llm or StubLLM(),
    )
    state = await graph.ainvoke(
        {
            "request": AuditRequest(claim_id=claim_id, persist=persist),
            "receipt_bytes": receipt_bytes,
            "mime_type": mime_type,
        }
    )
    return state, ocr_calls


async def test_happy_path_persists_violations_notes_and_confidence():
    tools = StubTools(_context())
    state, ocr_calls = await _run(tools=tools)
    result = state["result"]
    assert result.status == AuditAgentStatus.SUCCESS
    assert result.output.recommendation == AuditRecommendation.RECOMMEND_REJECT
    assert result.output.validation_violation is not None
    assert "does not match" in result.output.validation_violation
    assert result.output.policy_violation is not None
    assert "Business class" in result.output.policy_violation
    assert result.output.notes
    assert result.output.confidence == 0.8
    kinds = [name for name, _ in tools.calls]
    assert "validation" in kinds
    assert "policy" in kinds
    assert "audit" in kinds
    audit_call = [c for c in tools.calls if c[0] == "audit"][0][1]
    stored = audit_call["result"]
    assert stored.validation_violation == result.output.validation_violation
    assert stored.notes
    assert ocr_calls and ocr_calls[0]["expense_category"] == "TRAVEL"
    assert tools.status == ClaimStatus.IN_AUDIT


async def test_pass_with_no_violations_leaves_violation_text_empty():
    tools = StubTools(_context())
    state, _ = await _run(
        tools=tools,
        validation=_passing_validation(),
        policy=_policy_approve(),
        llm=StubLLM(
            payload={
                "notes": "Looks clean; recommend approve.",
                "reasons": ["No issues found."],
            }
        ),
    )
    result = state["result"]
    assert result.output.recommendation == AuditRecommendation.RECOMMEND_APPROVE
    assert result.output.validation_violation is None
    assert result.output.policy_violation is None


async def test_missing_receipt_skips_sub_agents_and_still_aggregates():
    tools = StubTools(_context())
    ocr_called = False

    async def boom_ocr(**kwargs):
        nonlocal ocr_called
        ocr_called = True
        raise AssertionError("OCR should not run")

    async def boom_validation(request):
        raise AssertionError("validation should not run")

    async def boom_policy(request):
        raise AssertionError("policy should not run")

    graph = build_audit_agent(
        tools=tools,
        run_ocr=boom_ocr,
        run_validation=boom_validation,
        run_policy=boom_policy,
        llm_client=StubLLM(),
    )
    state = await graph.ainvoke(
        {
            "request": AuditRequest(claim_id=3, persist=True),
            "receipt_bytes": None,
            "mime_type": None,
        }
    )
    result = state["result"]
    assert ocr_called is False
    assert result.status == AuditAgentStatus.ERROR
    assert result.error.code == "missing_receipt"
    assert result.output is not None
    assert any("ocr_agent" in w for w in result.output.warnings)
    assert any(c[0] == "audit" for c in tools.calls)


async def test_validation_fail_still_runs_policy():
    tools = StubTools(_context())
    policy_seen = []

    async def run_ocr(**kwargs):
        return _ocr_response()

    async def run_validation(request):
        return _failing_validation()

    async def run_policy(request):
        policy_seen.append(request)
        return _policy_flag()

    graph = build_audit_agent(
        tools=tools,
        run_ocr=run_ocr,
        run_validation=run_validation,
        run_policy=run_policy,
        llm_client=StubLLM(),
    )
    await graph.ainvoke(
        {
            "request": AuditRequest(claim_id=3, persist=False),
            "receipt_bytes": b"x",
            "mime_type": "image/png",
        }
    )
    assert policy_seen


async def test_ocr_error_skips_validation_and_policy():
    tools = StubTools(_context())
    ran = {"val": False, "pol": False}

    async def run_ocr(**kwargs):
        raise ValueError("Receipt file is required.")

    async def run_validation(request):
        ran["val"] = True
        return _passing_validation()

    async def run_policy(request):
        ran["pol"] = True
        return _policy_approve()

    graph = build_audit_agent(
        tools=tools,
        run_ocr=run_ocr,
        run_validation=run_validation,
        run_policy=run_policy,
        llm_client=StubLLM(),
    )
    state = await graph.ainvoke(
        {
            "request": AuditRequest(claim_id=3, persist=False),
            "receipt_bytes": b"x",
            "mime_type": "image/png",
        }
    )
    assert ran["val"] is False
    assert ran["pol"] is False
    assert state["result"].status == AuditAgentStatus.ERROR
    assert state["result"].error.agent == "ocr_agent"


async def test_recommendation_guardrail_rejects_on_validation_fail():
    rec = decide_recommendation(_failing_validation(), _policy_approve())
    assert rec == AuditRecommendation.RECOMMEND_REJECT
    rec = decide_recommendation(_passing_validation(), _policy_flag())
    assert rec == AuditRecommendation.FLAG_FOR_REVIEW
    rec = decide_recommendation(_passing_validation(), _policy_approve())
    assert rec == AuditRecommendation.RECOMMEND_APPROVE


async def test_unknown_claim_bubbles_not_found():
    tools = StubTools(_context())

    async def run_ocr(**kwargs):
        return _ocr_response()

    async def run_validation(request):
        return _passing_validation()

    async def run_policy(request):
        return _policy_approve()

    try:
        await run_audit_agent(
            AuditRequest(claim_id=99, persist=False),
            tools=tools,
            run_ocr=run_ocr,
            run_validation=run_validation,
            run_policy=run_policy,
            llm_client=StubLLM(),
            receipt_bytes=b"x",
            mime_type="image/png",
        )
        assert False, "expected ClaimNotFoundError"
    except ClaimNotFoundError as exc:
        assert exc.claim_id == 99


async def test_violation_formatters():
    text = format_validation_violation(_failing_validation().output)
    assert "does not match" in text
    assert format_validation_violation(_passing_validation().output) is None
    text = format_policy_violation(_policy_flag().output)
    assert "Travel 4.2" in text
    assert format_policy_violation(_policy_approve().output) is None


async def test_confidence_is_min_of_stages():
    assert overall_confidence(_failing_validation(), _policy_flag(), errored=False) == 0.8
    assert overall_confidence(_failing_validation(), _policy_flag(), errored=True) == 0.4


def test_run_response_exposes_approver_fields():
    from types import SimpleNamespace

    from app.services.audit_service import _to_run_response
    from app.schemas.audit import AuditAgentResult, AuditResult, AuditAgentStatus

    output = AuditResult(
        claim_id=3,
        recommendation=AuditRecommendation.RECOMMEND_REJECT,
        confidence=0.8,
        validation_violation="amount mismatch",
        policy_violation="class not allowed",
        notes="Please review this claim.",
    )
    row = SimpleNamespace(
        id=7,
        confidence_score=Decimal("0.80"),
        validation_violation="amount mismatch",
        policy_violation="class not allowed",
        notes="Please review this claim.",
        validation_response={"verdict": "FAIL"},
        policy_response={"decision": "FLAG_FOR_REVIEW"},
        audit_response={"claim_id": 3},
    )
    response = _to_run_response(
        AuditAgentResult(status=AuditAgentStatus.SUCCESS, output=output),
        claim_status=ClaimStatus.IN_AUDIT,
        row=row,
    )
    assert response.agent_response_id == 7
    assert response.validation_violation == "amount mismatch"
    assert response.policy_violation == "class not allowed"
    assert response.notes == "Please review this claim."
    assert response.confidence_score == Decimal("0.80")
    assert response.claim_status == ClaimStatus.IN_AUDIT
