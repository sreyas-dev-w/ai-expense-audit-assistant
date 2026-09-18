"""Typed LangGraph state for the Audit Agent orchestration workflow.

The state holds the structured inputs/outputs the workflow and its nodes
exchange (``docs/agents/orchestration.md``): the loaded claim, the fetched
receipt, the OCR extraction, the downstream agent requests/results and the
final decision-support result. ``errors`` accumulates first-class workflow
errors via a reducer; ``fatal`` marks a terminal failure that routes the run to
``mark_failed``.
"""
import operator
from typing import Annotated, Any, TypedDict

from app.schemas.assessment import AuditAssessment
from app.schemas.audit import (
    AuditAgentError,
    AuditResult,
    ClaimAuditContext,
    ReceiptData,
)
from app.schemas.extraction import Extraction
from app.schemas.policy import PolicyAgentResult, PolicyEvaluationRequest


class AuditAgentState(TypedDict, total=False):
    claim_id: int
    claim: ClaimAuditContext | None
    receipt: ReceiptData | None
    extraction: Extraction | None
    category_data: dict | None
    policy_request: PolicyEvaluationRequest | None
    validation_request: Any | None  # reserved for the Validation Agent
    policy_result: PolicyAgentResult | None
    validation_result: Any | None  # reserved for the Validation Agent
    validation_skipped: bool
    agent_response_id: int | None
    assessment: AuditAssessment | None
    assessment_skipped: bool
    final_result: AuditResult | None
    errors: Annotated[list[AuditAgentError], operator.add]
    fatal: AuditAgentError | None