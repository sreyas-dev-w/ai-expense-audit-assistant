"""Unit tests for the Validation Agent LangGraph subgraph."""
from decimal import Decimal

from app.agents.validation_agent import build_validation_agent
from app.schemas.validation import (
    AuthenticityAssessment,
    BudgetSnapshot,
    ValidationAgentStatus,
    ValidationSeverity,
    ValidationVerdict,
)
from app.services.gemini_client import GeminiLLMError
from app.services.validation_context_service import (
    ValidationContext,
    ValidationContextError,
)
from tests.unit.test_validation_rules import travel_request


class StubContextService:
    def __init__(self, budget=None, duplicates=None, warnings=None, error=None):
        self._context = ValidationContext(
            budget=budget
            or BudgetSnapshot(
                account_id="ACC-001",
                remaining_budget=Decimal("100000.00"),
                claim_amount=Decimal("51212.55"),
                currency="INR",
                within_budget=True,
            ),
            duplicates=duplicates or [],
            warnings=warnings or [],
        )
        self._error = error

    async def load(self, request):
        if self._error is not None:
            raise self._error
        return self._context


class StubValidationLLM:
    def __init__(self, payload=None, error=None):
        self._payload = payload or {
            "authenticity": {
                "is_suspicious": False,
                "forged_likelihood": 0.05,
                "reasons": ["No additional authenticity issues."],
            },
            "extra_findings": [],
            "warnings": [],
        }
        self._error = error
        self.last_contents = None

    def generate_structured(self, *, system_instruction, contents, response_schema):
        if self._error is not None:
            raise self._error
        self.last_contents = contents
        return dict(self._payload)


def _ample_budget() -> BudgetSnapshot:
    return BudgetSnapshot(
        account_id="ACC-001",
        remaining_budget=Decimal("100000.00"),
        claim_amount=Decimal("51212.55"),
        currency="INR",
        within_budget=True,
    )


async def test_travel_sample_fails_even_if_llm_is_optimistic():
    graph = build_validation_agent(
        context_service=StubContextService(budget=_ample_budget()),
        llm_client=StubValidationLLM(
            payload={
                "authenticity": {
                    "is_suspicious": False,
                    "forged_likelihood": 0.0,
                    "reasons": ["Looks fine."],
                },
                "extra_findings": [],
                "warnings": [],
            }
        ),
    )
    state = await graph.ainvoke({"request": travel_request()})
    result = state["result"]
    assert result.status == ValidationAgentStatus.SUCCESS
    assert result.output.verdict == ValidationVerdict.FAIL
    assert any(
        item.rule_id == "amount_mismatch"
        and item.severity == ValidationSeverity.BLOCKING
        for item in result.output.findings
    )


async def test_invalid_llm_output_still_returns_rule_findings():
    graph = build_validation_agent(
        context_service=StubContextService(budget=_ample_budget()),
        llm_client=StubValidationLLM(payload={"decision": "APPROVE"}),
    )
    state = await graph.ainvoke({"request": travel_request()})
    result = state["result"]
    assert result.status == ValidationAgentStatus.SUCCESS
    assert result.output.verdict == ValidationVerdict.FAIL
    assert any("authenticity_reasoning_unavailable" in warning for warning in result.output.warnings)
    assert any(item.rule_id == "amount_mismatch" for item in result.output.findings)


async def test_llm_failure_does_not_drop_blocking_rules():
    graph = build_validation_agent(
        context_service=StubContextService(budget=_ample_budget()),
        llm_client=StubValidationLLM(
            error=GeminiLLMError("gemini unavailable", code="gemini_unavailable")
        ),
    )
    state = await graph.ainvoke({"request": travel_request()})
    result = state["result"]
    assert result.status == ValidationAgentStatus.SUCCESS
    assert result.output.verdict == ValidationVerdict.FAIL
    assert result.output.authenticity == AuthenticityAssessment()


async def test_context_lookup_failure_is_a_warning_not_an_error():
    graph = build_validation_agent(
        context_service=StubContextService(
            error=ValidationContextError("db down", code="context_lookup_failed")
        ),
        llm_client=StubValidationLLM(),
    )
    state = await graph.ainvoke({"request": travel_request()})
    result = state["result"]
    assert result.status == ValidationAgentStatus.SUCCESS
    assert result.output.budget is None
    assert any("budget_check_skipped" == item.rule_id for item in result.output.findings)
    assert result.output.verdict == ValidationVerdict.FAIL
