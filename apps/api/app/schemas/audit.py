"""Audit workflow contracts.

The Audit Agent (``app/agents/audit_agent.py``) orchestrates the sub-agents
and tools. This module defines the contracts that cross that boundary:

- tool inputs/outputs used to fetch and persist claim workflow data
  (``ClaimAuditContext``, ``ReceiptData``, ``ClaimWriteResult``,
  ``AgentResponseRecord``)
- first-class error envelopes for workflow failures (``AuditAgentError``)
- the final, decision-support result returned to the caller (``AuditResult``)

``AuditResult`` preserves each stage's structured output (extraction, policy,
future validation) so the human auditor/manager can trace the recommendation
(see ``docs/backend/auditability.md``).
"""
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AIDecision,
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
    Currency,
    ExpenseCategory,
    JobLevel,
)
from app.schemas.policy import PolicyAgentOutput, PolicyReference
from app.schemas.validation import ValidationAgentOutput


class ClaimAuditContext(BaseModel):
    """Minimal claim + employee context the workflow needs to run an audit."""

    model_config = ConfigDict(extra="forbid")

    claim_id: int
    category: ExpenseCategory
    category_data: dict[str, Any]
    receipt_url: str | None = None
    merchant_name: str | None = None
    claim_amount: Decimal
    tax_amount: Decimal = Decimal("0")
    currency: Currency = Currency.INR
    business_purpose: str | None = None
    project_code: str | None = None
    employee_id: str
    employee_job_level: JobLevel | None = None
    priority: ClaimPriority | None = None


class ReceiptData(BaseModel):
    """Raw receipt bytes + MIME type resolved by the receipt tool."""

    content: bytes
    mime_type: str
    source: str


class ClaimWriteResult(BaseModel):
    """Outcome of a mutating claim write tool."""

    claim_id: int
    updated_fields: list[str] = Field(default_factory=list)


class AgentResponseRecord(BaseModel):
    """The claim's ``agent_response`` row written by the audit run."""

    id: int
    claim_id: int


class AuditAgentError(BaseModel):
    """First-class workflow error with enough context to route and record it.

    Mirrors the envelope pattern in ``app/schemas/policy.py``: errors carry the
    failing agent, an error code, the message and whether a retry is safe
    (``docs/backend/reliability.md``).
    """

    agent: str
    code: str
    message: str
    retryable: bool = False


class ExtractionSummary(BaseModel):
    """Human-readable summary of the OCR extraction result."""

    is_receipt: bool | None = None
    merchant_name: str | None = None
    claim_amount: Decimal | None = None
    currency: Currency | None = None
    expense_date: str | None = None
    receipt_no: str | None = None
    payment_status: str | None = None


class AuditResult(BaseModel):
    """Final, decision-support result returned to the caller.

    Decision support, not autonomous approval: the human auditor/manager makes
    the final call. The result preserves each stage's structured output for
    auditability.
    """

    claim_id: int
    status: ClaimStatus
    ai_run_status: AIRunStatus
    ai_decision: AIDecision | None = None
    priority: ClaimPriority | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: str | None = None
    extraction_summary: ExtractionSummary | None = None
    category_data: dict[str, Any] | None = None
    policy: PolicyAgentOutput | None = None
    grounding_references: list[PolicyReference] = Field(default_factory=list)
    validation: ValidationAgentOutput | None = Field(
        default=None,
        description="Structured Validation Agent output for auditability.",
    )
    errors: list[AuditAgentError] = Field(default_factory=list)