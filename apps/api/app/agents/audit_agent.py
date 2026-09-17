"""Audit Agent — the main orchestrator of the audit workflow.

Flow (LangGraph):

    START → load_claim → begin_run → fetch_receipt → run_ocr
         → store_extraction → map_requests → dispatch
         → [ run_policy | run_validation ]   (parallel branches)
         → store_responses → aggregate_result → finish → END
    any fatal node error → mark_failed → END

Responsibilities (``docs/agents/audit-agent.md``):

- fetch the claim + employee context from the DB via a tool and keep it in state
- call the OCR & Extraction Agent with the receipt bytes + expense category
- persist the extracted category data via a tool
- map the extraction into the Policy RAG Agent (and future Validation Agent)
  input contracts via ``app/agents/mappers/``
- run the Policy RAG and Validation agents **in parallel**, persisting their
  envelopes into ``agent_response`` via a tool
- aggregate the decision-support result and persist it onto the claim
- treat every failure as a first-class workflow state (``mark_failed``) and
  keep the claim's workflow/run status in sync with events

The graph is dependency-injected (sub-agents, tools, aggregator) so it can be
unit-tested without any external service or database; the production wiring
lives in ``app/services/audit_service.py``.
"""
from functools import partial
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.mappers.category_data_mapper import (
    MapperError,
    map_extraction_to_category_data,
)
from app.agents.mappers.policy_request_mapper import map_to_policy_request
from app.agents.state import AuditAgentState
from app.models.enums import AIRunStatus, ClaimStatus
from app.schemas.audit import AuditAgentError, AuditResult, ClaimAuditContext
from app.tools.base import AuditTool, AuditToolError

OK_BRANCH = "ok"
FAIL_BRANCH = "mark_failed"


def _fatal(agent: str, code: str, message: str, *, retryable: bool = False) -> dict:
    error = AuditAgentError(
        agent=agent, code=code, message=message, retryable=retryable
    )
    return {"fatal": error, "errors": [error]}


def _require_tool(tools: dict[str, AuditTool], name: str) -> AuditTool:
    tool = tools.get(name)
    if tool is None:
        raise ValueError(f"Missing required audit tool: {name}")
    return tool


def _tool_failure(exc: AuditToolError) -> dict:
    return _fatal(
        "audit_agent", exc.code, exc.message, retryable=exc.retryable
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def load_claim_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    tool = _require_tool(tools, "get_claim")
    try:
        claim = await tool.run(claim_id=state["claim_id"])
    except AuditToolError as exc:
        return _tool_failure(exc)
    if claim is None:
        return _fatal(
            "audit_agent",
            "claim_not_found",
            f"Claim {state['claim_id']} was not found",
        )
    return {"claim": claim}


async def begin_run_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Transition the claim into the audit workflow (in_audit + running)."""
    tool = _require_tool(tools, "update_audit_run_status")
    try:
        await tool.run(
            claim_id=state["claim_id"],
            claim_status=ClaimStatus.IN_AUDIT,
            ai_run_status=AIRunStatus.RUNNING,
        )
    except AuditToolError as exc:
        return _tool_failure(exc)
    return {}


async def fetch_receipt_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    claim: ClaimAuditContext = state["claim"]
    if not claim.receipt_url:
        return _fatal(
            "audit_agent",
            "missing_receipt_url",
            f"Claim {claim.claim_id} has no receipt_url configured",
        )
    tool = _require_tool(tools, "fetch_receipt")
    try:
        receipt = await tool.run(receipt_url=claim.receipt_url)
    except AuditToolError as exc:
        return _tool_failure(exc)
    if receipt is None or not receipt.content:
        return _fatal(
            "audit_agent", "empty_receipt", "Receipt was fetched but contained no content"
        )
    return {"receipt": receipt}


async def run_ocr_node(
    state: AuditAgentState, *, ocr_agent: Any
) -> dict:
    """Call the OCR & Extraction Agent with the receipt + category."""
    claim: ClaimAuditContext = state["claim"]
    receipt = state["receipt"]
    try:
        extraction = await ocr_agent.process(
            expense_category=_ocr_expense_label(claim.category),
            receipt_bytes=receipt.content,
            mime_type=receipt.mime_type,
        )
    except Exception as exc:
        return _fatal(
            "ocr_extraction_agent",
            "ocr_failed",
            f"OCR extraction failed: {exc}",
            retryable=True,
        )
    if extraction is None:
        return _fatal(
            "ocr_extraction_agent",
            "empty_extraction",
            "OCR agent returned no extraction result",
            retryable=True,
        )
    return {"extraction": extraction}


async def store_extraction_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Map the extraction into canonical category data and persist it."""
    claim: ClaimAuditContext = state["claim"]
    try:
        category_data = map_extraction_to_category_data(
            state["extraction"],
            category=claim.category,
            claimed_category_data=claim.category_data,
        )
    except MapperError as exc:
        return _fatal("audit_mappers", exc.code, str(exc))
    tool = _require_tool(tools, "store_extraction")
    try:
        await tool.run(claim_id=claim.claim_id, category_data=category_data)
    except AuditToolError as exc:
        return _tool_failure(exc)
    return {"category_data": category_data}


async def map_requests_node(
    state: AuditAgentState, *, map_policy_request: Callable
) -> dict:
    """Map the stored extraction into the downstream agent request contracts.

    The Validation Agent input is intentionally not mapped yet
    (``validation_request_mapper`` is reserved); when it lands, wire it here.
    """
    try:
        policy_request = map_policy_request(
            state["extraction"],
            context=state["claim"],
            category_data=state.get("category_data"),
        )
    except MapperError as exc:
        return _fatal("audit_mappers", exc.code, str(exc))
    return {"policy_request": policy_request}


async def dispatch_node(state: AuditAgentState) -> dict:
    """Fan out: run the Policy RAG and Validation agents in parallel."""
    return {}


async def run_policy_node(state: AuditAgentState, *, policy_runner: Callable) -> dict:
    try:
        result = await policy_runner(state["policy_request"])
    except Exception as exc:
        return _fatal(
            "policy_rag_agent",
            "policy_agent_crashed",
            f"Policy agent raised: {exc}",
            retryable=True,
        )
    if result is None:
        return _fatal(
            "policy_rag_agent",
            "empty_policy_result",
            "Policy agent returned no result",
            retryable=True,
        )
    return {"policy_result": result}


async def run_validation_node(
    state: AuditAgentState, *, validation_runner: Callable | None = None
) -> dict:
    """Reserved parallel branch for the Validation Agent.

    The Validation Agent is not implemented yet, so by default this node is a
    no-op that records ``validation_skipped``. To activate it, pass a
    ``validation_runner`` when building the graph:

        result = await validation_runner(state["validation_request"])
        return {"validation_result": result, "validation_skipped": False}
    """
    if validation_runner is None:
        return {"validation_result": None, "validation_skipped": True}
    try:
        result = await validation_runner(state.get("validation_request"))
    except Exception as exc:
        return _fatal(
            "validation_agent",
            "validation_agent_crashed",
            f"Validation agent raised: {exc}",
            retryable=True,
        )
    return {"validation_result": result, "validation_skipped": False}


async def store_responses_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Persist the policy/validation envelopes into ``agent_response``."""
    tool = _require_tool(tools, "store_agent_response")
    try:
        record = await tool.run(
            claim_id=state["claim_id"],
            policy_result=state.get("policy_result"),
            validation_result=state.get("validation_result"),
        )
    except AuditToolError as exc:
        return _tool_failure(exc)
    return {"agent_response_id": record.id}


async def aggregate_result_node(
    state: AuditAgentState, *, aggregator: Callable
) -> dict:
    """Aggregate stage outputs into the final decision-support result."""
    try:
        result = aggregator(state)
    except Exception as exc:
        return _fatal(
            "audit_agent", "aggregation_failed", f"Result aggregation failed: {exc}"
        )
    return {"final_result": result}


async def finish_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Persist the final AI decision/priority/notes onto the claim."""
    result: AuditResult = state["final_result"]
    tool = _require_tool(tools, "update_claim_result")
    try:
        await tool.run(
            claim_id=result.claim_id,
            ai_decision=result.ai_decision,
            priority=result.priority,
            ai_run_status=AIRunStatus.COMPLETED,
            notes=result.notes,
        )
    except AuditToolError as exc:
        return _tool_failure(exc)
    return {}


async def mark_failed_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Terminal failure state: mark the run failed and surface the error.

    The claim is moved back to ``submitted`` so it can be re-run after the
    cause is fixed. Persistence errors here are swallowed intentionally — we
    are already failing and the caller still receives the error result.
    """
    claim_id = state["claim_id"]
    errors = state.get("errors") or []
    error = state.get("fatal") or (errors[-1] if errors else None)

    tool = _require_tool(tools, "update_audit_run_status")
    try:
        await tool.run(
            claim_id=claim_id,
            claim_status=ClaimStatus.SUBMITTED,
            ai_run_status=AIRunStatus.FAILED,
            notes=_failure_notes(error),
        )
    except AuditToolError:
        pass

    return {
        "final_result": AuditResult(
            claim_id=claim_id,
            status=ClaimStatus.SUBMITTED,
            ai_run_status=AIRunStatus.FAILED,
            errors=[error] if error is not None else [],
            warnings=[_failure_notes(error)] if error is not None else [],
            reasons=["The audit run did not complete."],
            notes=_failure_notes(error),
        )
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_after_error(when_ok: str) -> tuple[Callable, dict[str, str]]:
    """Route to ``when_ok`` unless the state holds a fatal error marker."""

    def router(state: AuditAgentState) -> str:
        return OK_BRANCH if state.get("fatal") is None else FAIL_BRANCH

    return router, {OK_BRANCH: when_ok, FAIL_BRANCH: "mark_failed"}


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------


def build_audit_agent(
    *,
    ocr_agent: Any,
    policy_runner: Callable,
    aggregator: Callable[[AuditAgentState], AuditResult],
    tools: dict[str, AuditTool],
    map_policy_request: Callable = map_to_policy_request,
    validation_runner: Callable | None = None,
) -> CompiledStateGraph:
    """Compile the Audit Agent orchestration graph with injected dependencies."""
    graph = StateGraph(AuditAgentState)

    graph.add_node("load_claim", partial(load_claim_node, tools=tools))
    graph.add_node("begin_run", partial(begin_run_node, tools=tools))
    graph.add_node("fetch_receipt", partial(fetch_receipt_node, tools=tools))
    graph.add_node("run_ocr", partial(run_ocr_node, ocr_agent=ocr_agent))
    graph.add_node("store_extraction", partial(store_extraction_node, tools=tools))
    graph.add_node(
        "map_requests",
        partial(
            map_requests_node,
            map_policy_request=map_policy_request,
        ),
    )
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("run_policy", partial(run_policy_node, policy_runner=policy_runner))
    graph.add_node(
        "run_validation",
        partial(run_validation_node, validation_runner=validation_runner),
    )
    graph.add_node("store_responses", partial(store_responses_node, tools=tools))
    graph.add_node(
        "aggregate_result",
        partial(aggregate_result_node, aggregator=aggregator),
    )
    graph.add_node("finish", partial(finish_node, tools=tools))
    graph.add_node("mark_failed", partial(mark_failed_node, tools=tools))

    graph.add_edge(START, "load_claim")
    graph.add_conditional_edges("load_claim", *route_after_error("begin_run"))
    graph.add_conditional_edges("begin_run", *route_after_error("fetch_receipt"))
    graph.add_conditional_edges("fetch_receipt", *route_after_error("run_ocr"))
    graph.add_conditional_edges("run_ocr", *route_after_error("store_extraction"))
    graph.add_conditional_edges("store_extraction", *route_after_error("map_requests"))
    graph.add_conditional_edges("map_requests", *route_after_error("dispatch"))

    # Parallel fan-out/join: policy and validation run in the same superstep.
    graph.add_edge("dispatch", "run_policy")
    graph.add_edge("dispatch", "run_validation")
    graph.add_edge("run_policy", "store_responses")
    graph.add_edge("run_validation", "store_responses")

    graph.add_conditional_edges("store_responses", *route_after_error("aggregate_result"))
    graph.add_conditional_edges("aggregate_result", *route_after_error("finish"))
    graph.add_conditional_edges("finish", *route_after_error(END))

    graph.add_edge("mark_failed", END)

    return graph.compile()


async def run_audit_agent(graph: CompiledStateGraph, claim_id: int) -> AuditResult:
    """Run the compiled audit graph once and return its final result."""
    final_state = await graph.ainvoke({"claim_id": claim_id})
    result = final_state.get("final_result")
    if result is None:
        result = AuditResult(
            claim_id=claim_id,
            status=ClaimStatus.SUBMITTED,
            ai_run_status=AIRunStatus.FAILED,
            errors=[
                AuditAgentError(
                    agent="audit_agent",
                    code="missing_result",
                    message="Audit graph finished without producing a final result",
                )
            ],
            reasons=["The audit run did not complete."],
        )
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ocr_expense_label(category) -> str:
    """The OCR agent's input label for ``OTHER`` is ``OTHERS``."""
    return "OTHERS" if category.value == "OTHER" else category.value


def _failure_notes(error: AuditAgentError | None) -> str:
    if error is None:
        return "Audit run failed with an unknown error."
    return f"Audit run failed [{error.code}]: {error.message}"