from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    AUDITOR = "AUDITOR"
    ADMIN = "ADMIN"


class DocumentType(str, Enum):
    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    REIMBURSEMENT_FORM = "REIMBURSEMENT_FORM"


class ExpenseCategory(str, Enum):
    MEALS = "MEALS"
    HOTEL = "HOTEL"
    TRAVEL = "TRAVEL"
    SUPPLIES = "SUPPLIES"
    ACCOMMODATION = "ACCOMMODATION"
    OTHER = "OTHER"


class ClaimStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    AUDITED = "AUDITED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class Decision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class ErrorResponse(BaseModel):
    detail: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    employee_id: str | None
    name: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class HealthResponse(BaseModel):
    status: str
    api: str
    mysql: str
    timestamp: datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    original_filename: str
    storage_path: str
    sha256_hash: str
    upload_status: str


class PolicyUploadResponse(BaseModel):
    policy_id: str
    policy_version: str
    indexing_status: str
    message: str


class ExpenseLineCreate(BaseModel):
    expense_date: date
    expense_category: ExpenseCategory
    merchant_name: str
    claimed_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    description: str | None = None
    receipt_document_id: str


class ClaimCreate(BaseModel):
    policy_version: str
    purpose: str = Field(min_length=1)
    project_code: str = Field(min_length=1)
    expense_lines: list[ExpenseLineCreate] = Field(min_length=1)
    reimbursement_form_document_id: str | None = None


class ClaimCreateResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    employee_id: str | None
    total_claimed_amount: str
    currency: str
    created_at: datetime


class EmployeeResponse(BaseModel):
    employee_id: str | None
    name: str
    department: str


class ExpenseLineResponse(BaseModel):
    line_id: str
    expense_date: date
    expense_category: ExpenseCategory
    merchant_name: str
    claimed_amount: str
    currency: str
    description: str | None = None
    receipt_document_id: str


class LinkedDocumentResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    original_filename: str


class ClaimDetailResponse(BaseModel):
    claim_id: str
    employee: EmployeeResponse
    purpose: str
    project_code: str
    policy_version: str
    status: ClaimStatus
    total_claimed_amount: str
    currency: str
    expense_lines: list[ExpenseLineResponse]
    documents: list[LinkedDocumentResponse]


class SubmitClaimResponse(BaseModel):
    claim_id: str
    audit_id: str
    claim_status: ClaimStatus
    message: str


class FindingResponse(BaseModel):
    finding_id: str | None = None
    finding_type: str
    rule_code: str | None = None
    severity: str
    status: str | None = None
    evidence: dict[str, Any] | None = None
    policy_citation: dict[str, Any] | None = None
    duplicate_score: int | None = None
    matched_claim_id: str | None = None
    recommended_action: str


class AuditResultResponse(BaseModel):
    claim_id: str
    audit_id: str
    audit_status: str
    claim_status: ClaimStatus
    message: str | None = None
    risk_score: int | None = None
    summary: str | None = None
    findings: list[FindingResponse] | None = None


class AuditorDecision(BaseModel):
    decision: Decision
    comment: str = Field(min_length=1)
    resolved_finding_ids: list[str] = Field(default_factory=list)


class DecisionByResponse(BaseModel):
    user_id: str
    name: str


class AuditorDecisionResponse(BaseModel):
    audit_id: str
    claim_id: str
    final_status: ClaimStatus
    decision_by: DecisionByResponse
    decision_at: datetime
    message: str


class DashboardFiltersResponse(BaseModel):
    from_date: date | None
    to_date: date | None
    department: str | None


class DashboardTotalsResponse(BaseModel):
    total_claims: int
    draft_claims: int
    processing_claims: int
    approved_claims: int
    rejected_claims: int
    needs_clarification_claims: int
    duplicate_cases: int
    policy_violations: int
    total_claimed_amount: str
    flagged_amount: str
    currency: str


class ViolationCategoryResponse(BaseModel):
    expense_category: ExpenseCategory
    count: int


class RiskDistributionResponse(BaseModel):
    risk_level: str
    count: int


class DashboardSummaryResponse(BaseModel):
    filters: DashboardFiltersResponse
    summary: DashboardTotalsResponse
    violations_by_category: list[ViolationCategoryResponse]
    risk_distribution: list[RiskDistributionResponse]


def documented_errors(*status_codes: int) -> dict[int, dict[str, object]]:
    """Generate consistent OpenAPI error response metadata."""
    descriptions = {
        401: "Missing, invalid, or expired access token",
        403: "Authenticated user is not allowed to perform this action",
        404: "Requested resource was not found",
        409: "Request conflicts with the current resource state",
        413: "Uploaded file exceeds the configured size limit",
        415: "Uploaded file type is not supported",
        422: "Request data failed validation",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions[code]}
        for code in status_codes
    }
