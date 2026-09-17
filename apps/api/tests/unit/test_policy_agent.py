"""Unit tests for the Policy RAG Agent LangGraph subgraph."""
from app.agents.policy_rag_agent import build_policy_agent, _build_query
from app.models.enums import ExpenseCategory
from app.schemas.policy import (
    PolicyAgentStatus,
    PolicyDecision,
)
from app.services.gemini_client import GeminiLLMError
from app.services.rag_service import PolicyRetrievalError

from tests.conftest import (
    SAMPLE_CHUNK,
    StubLLMClient,
    StubRagService,
)


async def test_success_path(food_meals_request):
    rag = StubRagService(chunks=[SAMPLE_CHUNK])
    llm = StubLLMClient()

    graph = build_policy_agent(rag_service=rag, llm_client=llm)
    state = await graph.ainvoke({"request": food_meals_request})

    result = state["result"]
    assert result.status == PolicyAgentStatus.SUCCESS
    assert result.output.decision in {PolicyDecision.APPROVE, PolicyDecision.REJECT, PolicyDecision.FLAG_FOR_REVIEW}
    assert result.output.confidence == 0.85
    assert result.output.violations[0].related_chunk_ids == [1]
    # references were back-filled from retrieval when the model returned none
    assert [r.chunk_id for r in result.output.references] == [1]
    # the LLM actually received the retrieved policy context
    assert SAMPLE_CHUNK.content in llm.last_contents


async def test_insufficient_context_path(food_meals_request):
    rag = StubRagService(chunks=[])
    llm = StubLLMClient()

    graph = build_policy_agent(rag_service=rag, llm_client=llm)
    state = await graph.ainvoke({"request": food_meals_request})

    result = state["result"]
    assert result.status == PolicyAgentStatus.SUCCESS
    assert result.output.decision == PolicyDecision.FLAG_FOR_REVIEW
    assert result.output.confidence == 0.2
    assert result.output.warnings, "expected a grounding warning"
    assert not result.output.violations


async def test_retrieval_failure_is_explicit_error(food_meals_request):
    rag = StubRagService(error=PolicyRetrievalError("db unavailable", code="pgvector_down"))
    llm = StubLLMClient()

    graph = build_policy_agent(rag_service=rag, llm_client=llm)
    state = await graph.ainvoke({"request": food_meals_request})

    result = state["result"]
    assert result.status == PolicyAgentStatus.ERROR
    assert result.error is not None
    assert result.error.code == "pgvector_down"
    assert result.output is None


async def test_invalid_llm_output_is_explicit_error(food_meals_request):
    rag = StubRagService(chunks=[SAMPLE_CHUNK])
    llm = StubLLMClient(payload={"decision": "APPROVE"})  # missing confidence etc.

    graph = build_policy_agent(rag_service=rag, llm_client=llm)
    state = await graph.ainvoke({"request": food_meals_request})

    result = state["result"]
    assert result.status == PolicyAgentStatus.ERROR
    assert result.error.code == "invalid_llm_output"


async def test_llm_failure_is_explicit_error(food_meals_request):
    rag = StubRagService(chunks=[SAMPLE_CHUNK])
    llm = StubLLMClient(error=GeminiLLMError("gemini unavailable", code="gemini_unavailable"))

    graph = build_policy_agent(rag_service=rag, llm_client=llm)
    state = await graph.ainvoke({"request": food_meals_request})

    result = state["result"]
    assert result.status == PolicyAgentStatus.ERROR
    assert result.error.code == "gemini_unavailable"


def test_query_building_includes_category_and_merchant(food_meals_request):
    query = _build_query(food_meals_request)
    assert "meal" in query.lower()
    assert "zulu bistro" in query.lower()
    assert "2 people" in query.lower()


def test_query_building_for_other_category():
    from app.models.enums import ExpenseCategory
    from app.schemas.expense import OtherData
    from app.schemas.policy import OtherPolicyEvaluation, PolicyClaimContext

    request = OtherPolicyEvaluation(
        category=ExpenseCategory.OTHER,
        claim=PolicyClaimContext(
            employee_id="E",
            claim_amount=100,
            merchant_name="Stationery Co",
        ),
        category_data=OtherData(
            expense_type="Stationery",
            merchant_name="Stationery Co",
            line_items=[
                {"item_header": "Notebooks", "item_amount": 100}
            ],
        ),
    )
    query = _build_query(request)
    assert "stationery co" in query.lower()
    assert "expense" in query.lower()