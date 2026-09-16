"""Policy RAG Agent — a LangGraph subgraph that audits a claim against policy.

Flow (see ``docs/agents/policy-rag-agent.md``):

    START → build_query → retrieve_policy
                              ├─ error                → error_terminal
                              ├─ no chunks            → insufficient_context
                              └─ chunks               → reason
                                  → END

Input contract:  ``request``  → ``PolicyEvaluationRequest``
                 (common claim details + category-specific data, discriminated
                 on ``category`` — the category schema lives in
                 ``app/schemas/expense.py`` and is reused, not duplicated).

Output contract: ``result``   → ``PolicyAgentResult``
                 (violations, passed checks, confidence, decision, reasons,
                 grounding references — or an explicit ``error``).

The graph is built as a pure subgraph via :func:`build_policy_agent`, so the
Audit Agent can invoke it directly (``graph.ainvoke({"request": ...})``); the
node closures bind the injected retrieval + LLM services so the graph stays
free of app-level dependencies.
"""
import asyncio
import json
from functools import lru_cache, partial
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.policy import (
    PolicyAgentError,
    PolicyAgentOutput,
    PolicyAgentResult,
    PolicyAgentStatus,
    PolicyCheckStatus,
    PolicyDecision,
    PolicyEvaluationRequest,
    PolicyReference,
    RetrievedPolicyChunk,
)
from app.services.gemini_client import GeminiLLMError
from app.services.rag_service import PolicyRagService, PolicyRetrievalError

_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "policy_evaluation_prompt.txt"

EMPTY_RESULT_CODE = "missing_result"
LLM_TIMEOUT_CODE = "llm_timeout"
INVALID_LLM_OUTPUT_CODE = "invalid_llm_output"
RETRIEVAL_FAILED_CODE = "retrieval_failed"


class PolicyAgentState(TypedDict):
    request: PolicyEvaluationRequest
    query: str | None
    chunks: list[RetrievedPolicyChunk]
    result: PolicyAgentResult | None
    error: PolicyAgentError | None


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


async def build_query_node(state: PolicyAgentState) -> dict[str, Any]:
    return {"query": _build_query(state["request"])}


async def retrieve_policy_node(
    state: PolicyAgentState,
    *,
    rag_service: PolicyRagService,
) -> dict[str, Any]:
    try:
        chunks = await rag_service.search(
            query=state["query"] or "",
            top_k=settings.policy_search_default_top_k,
        )
    except PolicyRetrievalError as exc:
        return {
            "error": PolicyAgentError(
                code=exc.code, message=f"Policy retrieval failed: {exc}"
            )
        }
    return {"chunks": chunks}


async def reason_node(
    state: PolicyAgentState,
    *,
    llm_client: Any,
) -> dict[str, Any]:
    chunks = state.get("chunks") or []
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(
                llm_client.generate_structured,
                system_instruction=get_policy_evaluation_system_prompt(),
                contents=_build_contents(state["request"], chunks),
                response_schema=PolicyAgentOutput,
            ),
            timeout=settings.gemini_llm_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        return {
            "result": PolicyAgentResult(
                status=PolicyAgentStatus.ERROR,
                error=PolicyAgentError(
                    code=LLM_TIMEOUT_CODE,
                    message="Timed out while generating the policy evaluation",
                ),
            )
        }
    except GeminiLLMError as exc:
        return {
            "result": PolicyAgentResult(
                status=PolicyAgentStatus.ERROR,
                error=PolicyAgentError(code=exc.code, message=str(exc)),
            )
        }

    try:
        output = PolicyAgentOutput.model_validate(raw)
    except ValidationError as exc:
        return {
            "result": PolicyAgentResult(
                status=PolicyAgentStatus.ERROR,
                error=PolicyAgentError(
                    code=INVALID_LLM_OUTPUT_CODE,
                    message=f"LLM returned invalid policy evaluation: {exc.errors()}",
                ),
            )
        }

    if not output.references:
        output.references = _references_from_chunks(chunks)
    return {
        "result": PolicyAgentResult(status=PolicyAgentStatus.SUCCESS, output=output)
    }


async def insufficient_context_node(
    state: PolicyAgentState,
) -> dict[str, Any]:
    output = PolicyAgentOutput(
        decision=PolicyDecision.FLAG_FOR_REVIEW,
        confidence=0.2,
        reasons=[
            "No relevant policy context could be retrieved for this claim."
        ],
        warnings=[
            "Policy retrieval returned no relevant policy chunks; "
            "this evaluation is not grounded in policy content."
        ],
        checks=[],
        summary=(
            "The claim cannot be evaluated against company policy because no "
            "relevant policy content was retrieved."
        ),
    )
    return {
        "result": PolicyAgentResult(status=PolicyAgentStatus.SUCCESS, output=output)
    }


async def error_terminal_node(state: PolicyAgentState) -> dict[str, Any]:
    return _error_result(state["error"].code, state["error"].message)


def route_after_retrieve(state: PolicyAgentState) -> str:
    if state.get("error") is not None:
        return "error_terminal"
    if not state.get("chunks"):
        return "insufficient_context"
    return "reason"


def _error_result(code: str, message: str) -> dict[str, Any]:
    return {
        "result": PolicyAgentResult(
            status=PolicyAgentStatus.ERROR,
            error=PolicyAgentError(code=code, message=message),
        )
    }


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------


def build_policy_agent(
    *,
    rag_service: PolicyRagService,
    llm_client: Any,
) -> CompiledStateGraph:
    """Compile the Policy RAG Agent subgraph with injected services."""
    graph = StateGraph(PolicyAgentState)
    graph.add_node("build_query", build_query_node)
    graph.add_node(
        "retrieve_policy",
        partial(retrieve_policy_node, rag_service=rag_service),
    )
    graph.add_node(
        "reason",
        partial(reason_node, llm_client=llm_client),
    )
    graph.add_node("insufficient_context", insufficient_context_node)
    graph.add_node("error_terminal", error_terminal_node)

    graph.add_edge(START, "build_query")
    graph.add_edge("build_query", "retrieve_policy")
    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_retrieve,
        {
            "error_terminal": "error_terminal",
            "insufficient_context": "insufficient_context",
            "reason": "reason",
        },
    )
    graph.add_edge("reason", END)
    graph.add_edge("insufficient_context", END)
    graph.add_edge("error_terminal", END)
    return graph.compile()


async def run_policy_agent(
    request: PolicyEvaluationRequest,
    *,
    rag_service: PolicyRagService,
    llm_client: Any,
) -> PolicyAgentResult:
    """Run the Policy RAG Agent once, returning its envelope result."""
    graph = build_policy_agent(rag_service=rag_service, llm_client=llm_client)
    final_state = await graph.ainvoke({"request": request})
    result = final_state.get("result")
    if result is None:
        return PolicyAgentResult(
            status=PolicyAgentStatus.ERROR,
            error=PolicyAgentError(
                code=EMPTY_RESULT_CODE,
                message="Policy agent finished without producing a result",
            ),
        )
    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "FOOD_MEALS": [
        "meal",
        "meal type",
        "per-meal limit",
        "daily limit",
        "number of people",
        "alcohol",
    ],
    "TRAVEL": [
        "travel",
        "flight",
        "train",
        "taxi",
        "per-ticket limit",
        "business purpose",
    ],
    "ACCOMMODATION": [
        "accommodation",
        "hotel",
        "room",
        "per-night limit",
        "check-in",
        "check-out",
    ],
    "OTHER": ["expense", "prohibited", "limit", "receipt", "business purpose"],
}


def _build_query(request: PolicyEvaluationRequest) -> str:
    category = request.category
    claim = request.claim
    data = request.category_data

    facts: list[str] = []
    if claim.merchant_name:
        facts.append(claim.merchant_name)
    if category.value == "FOOD_MEALS":
        facts.extend([data.meal_type, f"{data.number_of_people} people"])
    elif category.value == "TRAVEL":
        facts.extend([data.travel_type, data.origin, data.destination])
    elif category.value == "ACCOMMODATION":
        facts.extend([data.hotel_name, data.location])
    else:
        facts.append(data.expense_type)

    facts.extend(_CATEGORY_KEYWORDS[category.value])
    query = " ".join(fact for fact in facts if fact)
    return query or f"{category.value} expense policy"


def _build_contents(
    request: PolicyEvaluationRequest, chunks: list[RetrievedPolicyChunk]
) -> str:
    lines = ["# Retrieved policy context", ""]
    if chunks:
        for i, chunk in enumerate(chunks, start=1):
            lines.append(
                f"[{i}] chunk_id={chunk.chunk_id} policy_id={chunk.policy_id} "
                f"similarity={chunk.similarity_score:.3f}"
            )
            lines.append(chunk.content)
            lines.append("")
    else:
        lines.append("(no policy chunks retrieved)")
        lines.append("")

    lines.append("# Claim under review")
    lines.append("")
    lines.append(json.dumps(request.model_dump(), default=str, indent=2))
    return "\n".join(lines)


def _references_from_chunks(
    chunks: list[RetrievedPolicyChunk],
) -> list[PolicyReference]:
    return [
        PolicyReference(
            chunk_id=chunk.chunk_id,
            policy_id=chunk.policy_id,
            content=chunk.content,
            similarity_score=chunk.similarity_score,
        )
        for chunk in chunks
    ]


@lru_cache(maxsize=1)
def get_policy_evaluation_system_prompt() -> str:
    return _PROMPT_FILE.read_text()