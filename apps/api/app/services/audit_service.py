"""Audit workflow orchestration layer.

``AuditService`` is the entry point the API (``app/api/audits.py``) and any
other caller uses to run an audit for a claim. It wires production services and
tools into the Audit Agent graph and wraps the graph invocation.

``aggregate_audit_result`` is the deterministic "reasoning" step that turns the
stage outputs (extraction, policy evaluation, ...) into the final
decision-support result persisted onto the claim (ai_decision, priority, notes,
confidence). It is pure and unit-testable; a language-model reasoning node can
be swapped in later without changing the surrounding workflow
(``docs/backend/auditability.md``).
"""
from decimal import Decimal
from functools import partial
from typing import Any

from app.agents.audit_agent import build_audit_agent, run_audit_agent
from app.agents.ocr_agent import OCRAgent
from app.agents.policy_rag_agent import run_policy_agent
from app.models.enums import (
    AIDecision,
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
    Currency,
)
from app.schemas.audit import (
    AuditAgentError,
    AuditResult,
    ExtractionSummary,
)
from app.schemas.policy import (
    PolicyAgentResult,
    PolicyAgentStatus,
    PolicyDecision,
)
from app.tools import build_audit_tools


# ---------------------------------------------------------------------------
# Deterministic aggregation / "reasoning"
# ---------------------------------------------------------------------------


def aggregate_audit_result(state: dict[str, Any]) -> AuditResult:
    """Combine the stage outputs into the final decision-support AuditResult.

    Maps the Policy RAG decision onto the AI recommendation, folds extraction
    quality signals into warnings, derives a priority and builds human-readable
    notes. Policy errors are preserved as first-class errors while the run
    still completes (decision support, not autonomous approval).
    """
    claim = state.get("claim")
    claim_id = state.get("claim_id")
    extraction = state.get("extraction")
    category_data = state.get("category_data")
    policy_result: PolicyAgentResult | None = state.get("policy_result")

    errors = list(state.get("errors") or [])
    reasons: list[str] = []
    warnings: list[str] = []
    grounding = []
    policy_output = None
    confidence = 0.0

    if (
        policy_result is not None
        and policy_result.status == PolicyAgentStatus.SUCCESS
        and policy_result.output is not None
    ):
        output = policy_result.output
        ai_decision = _decision_from_policy(output.decision)
        reasons = list(output.reasons)
        warnings = list(output.warnings)
        grounding = list(output.references)
        confidence = max(0.0, min(1.0, float(output.confidence)))
        policy_output = output
    elif (
        policy_result is not None
        and policy_result.status == PolicyAgentStatus.ERROR
        and policy_result.error is not None
    ):
        ai_decision = AIDecision.REVIEW
        reasons = ["The policy evaluation could not be completed."]
        warnings = [
            f"Policy agent error [{policy_result.error.code}]: "
            f"{policy_result.error.message}"
        ]
        errors.append(
            AuditAgentError(
                agent=policy_result.error.agent,
                code=policy_result.error.code,
                message=policy_result.error.message,
            )
        )
    else:
        ai_decision = AIDecision.REVIEW
        reasons = ["No policy evaluation was produced for this claim."]
        warnings = ["The claim should be reviewed manually."]

    if extraction is not None:
        if not getattr(extraction, "is_receipt", True):
            warnings.append("The provided file could not be verified as a receipt.")
        if getattr(extraction, "claim_amount", None) is None:
            warnings.append("No claim amount could be read from the receipt.")

    priority = _derive_priority(ai_decision, len(warnings))
    notes = _build_notes(claim_id, ai_decision, priority, reasons, warnings)

    return AuditResult(
        claim_id=claim_id,
        status=ClaimStatus.IN_AUDIT,
        ai_run_status=AIRunStatus.COMPLETED,
        ai_decision=ai_decision,
        priority=priority,
        confidence=confidence,
        reasons=reasons,
        warnings=warnings,
        notes=notes,
        extraction_summary=_extraction_summary(extraction),
        category_data=category_data,
        policy=policy_output,
        grounding_references=grounding,
        validation=None,  # reserved for the Validation Agent output
        errors=errors,
    )


def _decision_from_policy(decision: PolicyDecision) -> AIDecision:
    mapping = {
        PolicyDecision.APPROVE: AIDecision.APPROVE,
        PolicyDecision.REJECT: AIDecision.REJECT,
        PolicyDecision.FLAG_FOR_REVIEW: AIDecision.REVIEW,
    }
    return mapping.get(decision, AIDecision.REVIEW)


_PRIORITY_RANK = {
    ClaimPriority.LOW: 0,
    ClaimPriority.MEDIUM: 1,
    ClaimPriority.HIGH: 2,
    ClaimPriority.URGENT: 3,
}
_PRIORITY_BY_RANK = {rank: p for p, rank in _PRIORITY_RANK.items()}

_BASE_PRIORITY = {
    AIDecision.APPROVE: ClaimPriority.LOW,
    AIDecision.REVIEW: ClaimPriority.MEDIUM,
    AIDecision.REJECT: ClaimPriority.HIGH,
}


def _derive_priority(ai_decision: AIDecision, warning_count: int) -> ClaimPriority:
    base_rank = _PRIORITY_RANK[_BASE_PRIORITY[ai_decision]]
    if warning_count >= 3:
        return ClaimPriority.URGENT
    if warning_count >= 1:
        return _PRIORITY_BY_RANK[min(base_rank + 1, 3)]
    return _PRIORITY_BY_RANK[base_rank]


def _build_notes(
    claim_id: int,
    ai_decision: AIDecision,
    priority: ClaimPriority,
    reasons: list[str],
    warnings: list[str],
) -> str:
    lines = [
        f"AI recommendation for claim {claim_id}: {ai_decision.value} "
        f"(priority {priority.value})."
    ]
    if reasons:
        lines.append("Reasons: " + "; ".join(reasons))
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    return "\n".join(lines)


def _extraction_summary(extraction) -> ExtractionSummary | None:
    if extraction is None:
        return None
    return ExtractionSummary(
        is_receipt=getattr(extraction, "is_receipt", None),
        merchant_name=getattr(extraction, "merchant_name", None),
        claim_amount=_decimal_or_none(getattr(extraction, "claim_amount", None)),
        currency=_currency_or_none(getattr(extraction, "currency", None)),
        expense_date=getattr(extraction, "expense_date", None),
        receipt_no=getattr(extraction, "receipt_no", None),
        payment_status=getattr(extraction, "payment_status", None),
    )


def _decimal_or_none(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None


def _currency_or_none(value) -> Currency | None:
    if not value:
        return None
    try:
        return Currency(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Production wiring
# ---------------------------------------------------------------------------


def build_default_audit_graph():
    """Wire production services (OCR + Policy agents, DB tools) into the graph."""
    from app.core.dependencies import get_llm_client, get_policy_rag_service

    rag_service = get_policy_rag_service()
    llm_client = get_llm_client()
    policy_runner = partial(
        run_policy_agent, rag_service=rag_service, llm_client=llm_client
    )
    return build_audit_agent(
        ocr_agent=OCRAgent(),
        policy_runner=policy_runner,
        tools=build_audit_tools(),
        aggregator=aggregate_audit_result,
    )


class AuditService:
    """Application-level entry point for running a claim audit."""

    def __init__(self, *, graph=None):
        self._graph = graph if graph is not None else build_default_audit_graph()

    async def run_audit(self, claim_id: int) -> AuditResult:
        return await run_audit_agent(self._graph, claim_id)