"""Compile and exercise the real LangGraph parent + subgraphs together."""
from app.agents.audit_agent import build_audit_agent, run_audit_agent
from app.agents.ocr_agent import OCRAgent
from app.agents.policy_rag_agent import build_policy_agent, run_policy_agent
from app.agents.validation_agent import build_validation_agent, run_validation_agent
from app.schemas.audit import AuditAgentStatus, AuditRecommendation, AuditRequest
from app.schemas.policy import PolicyAgentStatus
from app.schemas.validation import ValidationAgentStatus, ValidationVerdict
from tests.conftest import SAMPLE_CHUNK, StubLLMClient, StubRagService
from tests.unit.test_audit_agent import (
    StubTools,
    _context,
    _ocr_response,
)
from tests.unit.test_validation_agent import StubContextService, StubValidationLLM
from tests.unit.test_validation_rules import travel_request


class SchemaAwareLLM:
    """Dispatches canned payloads by response schema so one client can drive
    validation, policy, and audit aggregation in a single parent run."""

    def generate_structured(self, *, system_instruction, contents, response_schema):
        name = getattr(response_schema, "__name__", str(response_schema))
        if name == "AuditAggregationOutput":
            return {
                "notes": "Recommend reject due to amount mismatch and policy flags.",
                "reasons": ["Receipt total does not match the claimed amount."],
            }
        if name == "ValidationReasoningOutput":
            return {
                "authenticity": {
                    "is_suspicious": False,
                    "forged_likelihood": 0.05,
                    "reasons": ["No additional authenticity issues."],
                },
                "extra_findings": [],
                "warnings": [],
            }
        return {
            "decision": "FLAG_FOR_REVIEW",
            "confidence": 0.85,
            "violations": [
                {
                    "policy_reference": "Travel 4.2",
                    "severity": "warning",
                    "description": "Business class is not permitted at L3.",
                    "related_chunk_ids": [1],
                }
            ],
            "checks": [],
            "reasons": ["Travel class exceeds job-level entitlement."],
            "warnings": [],
            "references": [],
            "summary": "Travel class policy issue.",
        }


def _assert_connected(mermaid: str, *fragments: str) -> None:
    for fragment in fragments:
        assert fragment in mermaid, f"missing graph edge/node {fragment!r}\n{mermaid}"


def test_parent_and_subgraphs_compile_with_connected_edges():
    async def _ocr(**kwargs):
        return _ocr_response()

    async def _validation(request):
        return request

    async def _policy(request):
        return request

    parent = build_audit_agent(
        tools=StubTools(_context()),
        run_ocr=_ocr,
        run_validation=_validation,
        run_policy=_policy,
        llm_client=SchemaAwareLLM(),
    )
    mermaid = parent.get_graph().draw_mermaid()
    _assert_connected(
        mermaid,
        "load_context",
        "set_status",
        "extract",
        "validate",
        "persist_validation",
        "policy",
        "persist_policy",
        "aggregate",
        "persist_final",
        "load_context -.-> set_status",
        "extract -.-> validate",
        "validate --> persist_validation",
        "policy --> persist_policy",
        "aggregate --> persist_final",
        "persist_validation -.-> policy",
        "set_status -.-> extract",
    )
    assert "error_terminal" not in mermaid

    validation = build_validation_agent(
        context_service=StubContextService(),
        llm_client=StubValidationLLM(),
    )
    val_mermaid = validation.get_graph().draw_mermaid()
    _assert_connected(
        val_mermaid,
        "load_context --> run_rules",
        "run_rules --> reason",
        "reason --> assemble",
    )

    policy = build_policy_agent(
        rag_service=StubRagService(chunks=[SAMPLE_CHUNK]),
        llm_client=StubLLMClient(),
    )
    pol_mermaid = policy.get_graph().draw_mermaid()
    _assert_connected(
        pol_mermaid,
        "build_query --> retrieve_policy",
        "retrieve_policy -.-> reason",
        "retrieve_policy -.-> insufficient_context",
        "retrieve_policy -.-> error_terminal",
    )


def test_ocr_subgraph_compiles(monkeypatch):
    monkeypatch.setattr(
        "app.agents.ocr_agent.GeminiService",
        lambda: object(),
    )
    agent = OCRAgent()
    mermaid = agent.graph.get_graph().draw_mermaid()
    _assert_connected(
        mermaid,
        "validate_input --> fetch_employee",
        "fetch_employee --> fetch_project",
        "fetch_project --> validate_category_specific",
        "validate_category_specific --> create_submission",
        "create_submission --> extract_receipt",
        "extract_receipt --> create_response",
    )


async def test_parent_invokes_real_validation_and_policy_subgraphs():
    tools = StubTools(_context())
    llm = SchemaAwareLLM()

    async def run_ocr(**kwargs):
        assert kwargs["expense_category"] == "TRAVEL"
        assert kwargs["receipt_bytes"]
        return _ocr_response()

    async def run_validation(request):
        return await run_validation_agent(
            request,
            context_service=StubContextService(),
            llm_client=llm,
        )

    async def run_policy(request):
        return await run_policy_agent(
            request,
            rag_service=StubRagService(chunks=[SAMPLE_CHUNK]),
            llm_client=llm,
        )

    result = await run_audit_agent(
        AuditRequest(claim_id=3, persist=True),
        tools=tools,
        run_ocr=run_ocr,
        run_validation=run_validation,
        run_policy=run_policy,
        llm_client=llm,
        receipt_bytes=b"fake-png",
        mime_type="image/png",
    )
    assert result.status == AuditAgentStatus.SUCCESS
    assert result.output is not None
    assert result.output.validation is not None
    assert result.output.validation.verdict == ValidationVerdict.FAIL
    assert result.output.policy is not None
    assert result.output.recommendation == AuditRecommendation.RECOMMEND_REJECT
    assert result.output.notes
    kinds = [name for name, _ in tools.calls]
    assert kinds.count("validation") == 1
    assert kinds.count("policy") == 1
    assert kinds.count("audit") == 1


async def test_real_subgraphs_themselves_return_envelopes():
    validation = await run_validation_agent(
        travel_request(),
        context_service=StubContextService(),
        llm_client=StubValidationLLM(),
    )
    assert validation.status == ValidationAgentStatus.SUCCESS
    assert validation.output.verdict == ValidationVerdict.FAIL

    from tests.conftest import sample_food_meals_request

    policy = await run_policy_agent(
        sample_food_meals_request(),
        rag_service=StubRagService(chunks=[SAMPLE_CHUNK]),
        llm_client=StubLLMClient(),
    )
    assert policy.status == PolicyAgentStatus.SUCCESS
    assert policy.output is not None


async def test_persist_failure_does_not_abort_the_graph():
    tools = StubTools(_context())

    async def boom(**kwargs):
        raise RuntimeError("db down")

    tools.store_audit_result = boom  # type: ignore[method-assign]

    async def run_ocr(**kwargs):
        return _ocr_response()

    async def run_validation(request):
        return await run_validation_agent(
            request,
            context_service=StubContextService(),
            llm_client=SchemaAwareLLM(),
        )

    async def run_policy(request):
        return await run_policy_agent(
            request,
            rag_service=StubRagService(chunks=[SAMPLE_CHUNK]),
            llm_client=SchemaAwareLLM(),
        )

    result = await run_audit_agent(
        AuditRequest(claim_id=3, persist=True),
        tools=tools,
        run_ocr=run_ocr,
        run_validation=run_validation,
        run_policy=run_policy,
        llm_client=SchemaAwareLLM(),
        receipt_bytes=b"fake-png",
        mime_type="image/png",
    )
    assert result.output is not None
    assert any("persist" in warning for warning in result.output.warnings)
