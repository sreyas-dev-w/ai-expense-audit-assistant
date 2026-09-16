"""Audit Agent contracts.

The orchestrator reuses OCR, validation, and policy schemas rather than
duplicating them. This module owns the workflow request/result, the
approver-facing denormalized fields, and the DB-backed context snapshot
loaded from claims / employees / projects / accounts.
"""
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClaimPriority, ClaimStatus, Currency, ExpenseCategory
from app.schemas.extraction import OCRResponse
from app.schemas.policy import PolicyAgentOutput, PolicyReference
from app.schemas.validation import ValidationAgentOutput


class AuditRecommendation(str, Enum):
    RECOMMEND_APPROVE = "RECOMMEND_APPROVE"
    RECOMMEND_REJECT = "RECOMMEND_REJECT"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


class AuditAgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: int
    persist: bool = True


class ClaimSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: int
    employee_id: str
    business_purpose: str | None = None
    merchant_name: str | None = None
    category: ExpenseCategory
    category_data: dict[str, Any] = Field(default_factory=dict)
    project_code: str | None = None
    claim_amount: Decimal
    currency: Currency = Currency.INR
    status: ClaimStatus
    priority: ClaimPriority = ClaimPriority.MEDIUM
    receipt_url: str | None = None
    auditer_id: str | None = None


class EmployeeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    employee_name: str
    job_level: str
    is_manager: bool = False
    manager_id: str | None = None
    project_code: str | None = None


class ProjectSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_code: str
    project_name: str
    account_id: str
    project_lead_id: str | None = None


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_name: str
    fiscal_year: int
    budget_allocated: Decimal
    remaining_budget: Decimal
    currency: str


class AuditContext(BaseModel):
    """Relational snapshot the orchestrator loads before invoking sub-agents."""

    model_config = ConfigDict(extra="forbid")

    claim: ClaimSnapshot
    employee: EmployeeSnapshot
    manager: EmployeeSnapshot | None = None
    project: ProjectSnapshot | None = None
    account: AccountSnapshot | None = None


class AuditAggregationOutput(BaseModel):
    """Structured LLM output: approver notes plus explanation reasons only."""

    model_config = ConfigDict(extra="forbid")

    notes: str
    reasons: list[str] = Field(default_factory=list)


class AuditResult(BaseModel):
    """Decision-support aggregate persisted as ``agent_response.audit_response``."""

    model_config = ConfigDict(extra="forbid")

    claim_id: int
    recommendation: AuditRecommendation
    reasons: list[str] = Field(default_factory=list)
    extraction: OCRResponse | None = None
    validation: ValidationAgentOutput | None = None
    policy: PolicyAgentOutput | None = None
    references: list[PolicyReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    validation_violation: str | None = None
    policy_violation: str | None = None
    notes: str | None = None
    employee: EmployeeSnapshot | None = None
    account: AccountSnapshot | None = None


class AuditAgentError(BaseModel):
    code: str
    message: str
    agent: str = "audit_agent"


class AuditAgentResult(BaseModel):
    """Envelope the parent graph returns to the HTTP layer."""

    status: AuditAgentStatus
    output: AuditResult | None = None
    error: AuditAgentError | None = None


class AuditRunResponse(AuditAgentResult):
    """HTTP response for a run or the latest stored audit."""

    agent_response_id: int | None = None
    claim_status: ClaimStatus | None = None
    validation_violation: str | None = None
    policy_violation: str | None = None
    notes: str | None = None
    confidence_score: Decimal | None = None
    validation_response: dict[str, Any] | None = None
    policy_response: dict[str, Any] | None = None
    audit_response: dict[str, Any] | None = None
