"""Audit Agent — the main orchestrator of the audit workflow.

Flow (LangGraph):

    START → load_claim → begin_run → fetch_receipt → run_ocr
         → store_extraction → map_requests → dispatch
         → [ run_policy | run_validation ]   (parallel branches)
         → store_responses → assess_result → aggregate_result → finish → END
    any fatal node error → mark_failed → END

``assess_result`` is the LLM reasoning node: it summarises the policy/validation
stage outputs (from state, or the stored ``agent_response`` row if a stage did
not run) into a final summary/decision/priority/confidence. Its LLM failures
degrade gracefully to the deterministic ``aggregate_result`` — the audit run
never fails just because the assessment LLM is unavailable.

Responsibilities (``docs/agents/audit-agent.md``):

- fetch the claim + employee context from the DB via a tool and keep it in state
- call the OCR & Extraction Agent with the receipt bytes + expense category
- persist the extracted category data via a tool
- map the extraction into the Policy RAG Agent (and future Validation Agent)
  input contracts via ``app/agents/mappers/``
- run the Policy RAG and Validation agents **in parallel**, persisting their
  envelopes into ``agent_response`` via a tool
- run the LLM assessment node over the stage outputs and persist its summary +
  confidence onto ``agent_response`` (never touching ``validation_response`` /
  ``policy_response``)
- aggregate the decision-support result and persist it onto the claim
- treat every failure as a first-class workflow state (``mark_failed``) and
  keep the claim's workflow/run status in sync with events

The graph is dependency-injected (sub-agents, tools, aggregator) so it can be
unit-tested without any external service or database; the production wiring
lives in ``app/services/audit_service.py``.
"""
import asyncio
import logging
from functools import partial
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.agents.mappers.category_data_mapper import (
    MapperError,
    map_extraction_to_category_data,
)
from app.agents.mappers.policy_request_mapper import map_to_policy_request
from app.agents.mappers.validation_request_mapper import map_to_validation_request
from app.agents.state import AuditAgentState
from app.core.logging import to_loggable
from app.models.enums import AIRunStatus, ClaimStatus
from app.schemas.audit import AuditAgentError, AuditResult, ClaimAuditContext
from app.services.gemini_client import GeminiLLMError
from app.tools.base import AuditTool, AuditToolError

OK_BRANCH = "ok"
FAIL_BRANCH = "mark_failed"

logger = logging.getLogger(__name__)


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
    logger.info(
        "Audit agent loaded claim %s: category=%s employee=%s",
        claim.claim_id,
        claim.category.value,
        claim.employee_id,
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
    logger.info("Audit agent started run for claim %s.", state["claim_id"])
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
    logger.info(
        "Audit agent fetched receipt for claim %s: mime_type=%s bytes=%d",
        state["claim_id"],
        receipt.mime_type,
        len(receipt.content),
    )
    return {"receipt": receipt}


async def run_ocr_node(
    state: AuditAgentState, *, ocr_agent: Any
) -> dict:
    """Call the OCR & Extraction Agent with the receipt + category."""
    claim: ClaimAuditContext = state["claim"]
    receipt = state["receipt"]
    logger.info(
        "Audit agent calling OCR agent for claim %s (category=%s).",
        claim.claim_id,
        claim.category.value,
    )
    try:
        extraction = await ocr_agent.process(
            expense_category=_ocr_expense_label(claim.category),
            receipt_bytes=receipt.content,
            mime_type=receipt.mime_type,
        )
    except Exception as exc:
        logger.exception("OCR agent failed for claim %s.", claim.claim_id)
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
    logger.info(
        "Audit agent stored category data for claim %s: %s",
        claim.claim_id,
        to_loggable(category_data),
    )
    return {"category_data": category_data}


async def map_requests_node(
    state: AuditAgentState,
    *,
    map_policy_request: Callable,
    map_validation_request: Callable,
) -> dict:
    """Map the stored extraction into the downstream agent request contracts."""
    try:
        policy_request = map_policy_request(
            state["extraction"],
            context=state["claim"],
            category_data=state.get("category_data"),
        )
    except MapperError as exc:
        return _fatal("audit_mappers", exc.code, str(exc))
    try:
        validation_request = map_validation_request(
            state["extraction"],
            context=state["claim"],
            category_data=state.get("category_data"),
        )
    except MapperError as exc:
        return _fatal("audit_mappers", exc.code, str(exc))
    logger.info(
        "Audit agent mapped policy and validation requests for claim %s.",
        state["claim_id"],
    )
    return {
        "policy_request": policy_request,
        "validation_request": validation_request,
    }


async def dispatch_node(state: AuditAgentState) -> dict:
    """Fan out: run the Policy RAG and Validation agents in parallel."""
    return {}


async def run_policy_node(state: AuditAgentState, *, policy_runner: Callable) -> dict:
    logger.info("Audit agent dispatching Policy agent for claim %s.", state["claim_id"])
    try:
        result = await policy_runner(state["policy_request"])
    except Exception as exc:
        logger.exception("Policy agent raised for claim %s.", state["claim_id"])
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
    logger.info(
        "Audit agent received Policy result for claim %s: status=%s",
        state["claim_id"],
        getattr(result, "status", None),
    )
    return {"policy_result": result}


async def run_validation_node(
    state: AuditAgentState, *, validation_runner: Callable | None = None
) -> dict:
    """Run the Validation Agent in the parallel dispatch superstep.

    Consumes the ``validation_request`` mapped in ``map_requests_node``.
    When no ``validation_runner`` is injected the node is a no-op that
    records ``validation_skipped`` (used by tests and minimal setups).
    """
    if validation_runner is None:
        logger.info(
            "Audit agent skipped Validation agent for claim %s (no runner wired).",
            state["claim_id"],
        )
        return {"validation_result": None, "validation_skipped": True}
    logger.info("Audit agent dispatching Validation agent for claim %s.", state["claim_id"])
    try:
        result = await validation_runner(state.get("validation_request"))
    except Exception as exc:
        logger.exception("Validation agent raised for claim %s.", state["claim_id"])
        return _fatal(
            "validation_agent",
            "validation_agent_crashed",
            f"Validation agent raised: {exc}",
            retryable=True,
        )
    if result is None:
        logger.warning(
            "Validation agent returned no result for claim %s; "
            "validation_response will not be persisted.",
            state["claim_id"],
        )
    else:
        logger.info(
            "Audit agent received Validation result for claim %s: status=%s",
            state["claim_id"],
            getattr(result, "status", None),
        )
    return {"validation_result": result, "validation_skipped": False}


async def store_responses_node(state: AuditAgentState, *, tools: dict[str, AuditTool]) -> dict:
    """Write the policy/validation envelopes onto the claim's ``agent_response`` row."""
    policy_result = state.get("policy_result")
    validation_result = state.get("validation_result")
    logger.info(
        "Audit agent storing agent response for claim %s: policy=%s validation=%s",
        state["claim_id"],
        policy_result is not None,
        validation_result is not None,
    )
    tool = _require_tool(tools, "store_agent_response")
    try:
        record = await tool.run(
            claim_id=state["claim_id"],
            policy_result=policy_result,
            validation_result=validation_result,
        )
    except AuditToolError as exc:
        return _tool_failure(exc)
    return {"agent_response_id": record.id}


async def assess_result_node(
    state: AuditAgentState,
    *,
    assessment_runner: Callable | None,
    tools: dict[str, AuditTool],
) -> dict:
    """LLM assessment node: summarise the stage outputs into a recommendation.

    Gathers the OCR extraction + policy/validation results from state when
    present, otherwise falls back to the stored ``agent_response`` row via the
    ``get_agent_response`` read tool. LLM failures (timeout, client error,
    invalid output) degrade gracefully — the run continues to the deterministic
    ``aggregate_result`` with ``assessment=None``. On success the summary and
    confidence are persisted onto ``agent_response`` via the
    ``store_assessment`` tool; ``validation_response`` / ``policy_response``
    are never touched.
    """
    claim_id = state["claim_id"]
    if assessment_runner is None:
        logger.info(
            "Audit agent skipped LLM assessment for claim %s (no runner wired).",
            claim_id,
        )
        return {"assessment": None, "assessment_skipped": True}

    try:
        sources = await _assessment_sources(state, tools=tools)
    except AuditToolError as exc:
        return _tool_failure(exc)
    logger.info("Audit agent running LLM assessment for claim %s.", claim_id)
    try:
        assessment = await assessment_runner(**sources)
    except asyncio.TimeoutError:
        return _assessment_unavailable("llm_timeout", "Timed out while generating the audit assessment")
    except GeminiLLMError as exc:
        return _assessment_unavailable(exc.code, str(exc))
    except ValidationError as exc:
        return _assessment_unavailable(
            "invalid_llm_output",
            f"LLM returned invalid audit assessment: {exc.errors()}",
        )

    tool = _require_tool(tools, "store_assessment")
    try:
        await tool.run(claim_id=claim_id, assessment=assessment)
    except AuditToolError as exc:
        return _tool_failure(exc)
    logger.info(
        "Audit agent stored assessment for claim %s: decision=%s priority=%s confidence=%s",
        claim_id,
        assessment.ai_decision.value,
        assessment.priority.value,
        assessment.confidence,
    )
    return {"assessment": assessment, "assessment_skipped": False}


async def aggregate_result_node(
    state: AuditAgentState, *, aggregator: Callable
) -> dict:
    """Aggregate stage outputs into the final decision-support result."""
    try:
        result = aggregator(state)
    except Exception as exc:
        logger.exception("Result aggregation failed for claim %s.", state["claim_id"])
        return _fatal(
            "audit_agent", "aggregation_failed", f"Result aggregation failed: {exc}"
        )
    logger.info(
        "Audit agent aggregated result for claim %s: decision=%s priority=%s errors=%d",
        state["claim_id"],
        getattr(result.ai_decision, "value", result.ai_decision),
        getattr(result.priority, "value", result.priority),
        len(result.errors),
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
    logger.info("Audit agent completed run for claim %s.", result.claim_id)
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
    logger.warning(
        "Audit agent marking claim %s as failed: %s",
        claim_id,
        _failure_notes(error),
    )

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
    map_validation_request: Callable = map_to_validation_request,
    validation_runner: Callable | None = None,
    assessment_runner: Callable | None = None,
) -> CompiledStateGraph:
    """Compile the Audit Agent orchestration graph with injected dependencies.

    ``assessment_runner`` is the LLM assessment callable (e.g.
    ``functools.partial(run_audit_assessment, llm_client=...)``). When it is
    ``None`` the assessment node is skipped and the deterministic aggregator
    produces the result exactly as before.
    """
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
            map_validation_request=map_validation_request,
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
        "assess_result",
        partial(assess_result_node, assessment_runner=assessment_runner, tools=tools),
    )
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

    graph.add_conditional_edges("store_responses", *route_after_error("assess_result"))
    graph.add_conditional_edges("assess_result", *route_after_error("aggregate_result"))
    graph.add_conditional_edges("aggregate_result", *route_after_error("finish"))
    graph.add_conditional_edges("finish", *route_after_error(END))

    graph.add_edge("mark_failed", END)

    return graph.compile()


async def run_audit_agent(graph: CompiledStateGraph, claim_id: int) -> AuditResult:
    """Run the compiled audit graph once and return its final result."""
    logger.info("Audit agent starting graph run for claim %s.", claim_id)
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
    logger.info(
        "Audit agent finished graph run for claim %s: run_status=%s decision=%s",
        claim_id,
        getattr(result.ai_run_status, "value", result.ai_run_status),
        getattr(result.ai_decision, "value", result.ai_decision),
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


def _assessment_unavailable(code: str, message: str) -> dict:
    """Non-fatal LLM degradation for the assessment node.

    The deterministic ``aggregate_result`` runs unchanged when the assessment
    is unavailable, so the audit still completes (decision support, not
    autonomous approval). The failure is recorded as a first-class error.
    """
    error = AuditAgentError(agent="audit_agent", code=code, message=message, retryable=True)
    logger.warning("Audit assessment unavailable: %s", message)
    return {"assessment": None, "assessment_skipped": False, "errors": [error]}


async def _assessment_sources(
    state: AuditAgentState, *, tools: dict[str, AuditTool]
) -> dict:
    """Collect the assessment inputs, preferring state and falling back to DB.

    The policy/validation envelopes come from state when available; missing ones
    are loaded from the stored ``agent_response`` row via the read
    ``get_agent_response`` tool (agents never touch SQL directly). If no OCR
    extraction is in state a derived claim snapshot is used instead.
    """
    claim = state.get("claim")
    extraction = state.get("extraction")
    policy_result = state.get("policy_result")
    validation_result = state.get("validation_result")

    if policy_result is None or validation_result is None:
        record = await _load_stored_response(state, tools=tools)
        if policy_result is None:
            policy_result = _stored_payload(record, "policy_response")
        if validation_result is None:
            validation_result = _stored_payload(record, "validation_response")

    if claim is not None and extraction is None:
        extraction = {
            "source": "claim category_data (no OCR extraction in state)",
            "category": claim.category.value,
            "merchant_name": claim.merchant_name,
            "claim_amount": str(claim.claim_amount),
            "currency": claim.currency.value,
            "category_data": claim.category_data,
        }

    return {
        "claim": claim,
        "extraction": extraction,
        "policy_result": policy_result,
        "validation_result": validation_result,
    }


async def _load_stored_response(
    state: AuditAgentState, *, tools: dict[str, AuditTool]
) -> Any | None:
    tool = _require_tool(tools, "get_agent_response")
    return await tool.run(claim_id=state["claim_id"])


def _stored_payload(record: Any, attribute: str) -> Any:
    if record is None:
        return None
    return getattr(record, attribute, None)