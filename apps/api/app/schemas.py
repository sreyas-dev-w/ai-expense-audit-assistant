from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimSubmitRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    claim_name: str = Field(..., min_length=1, max_length=200)
    estimated_amount: float = Field(..., gt=0)


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: int
    employee_id: str
    claim_name: str
    estimated_amount: float
    status: str
    violations: str | None
    requires_human_review: bool
    document_path: str | None
    ocr_text: dict | None
    created_at: datetime


class SubmitResponse(BaseModel):
    claim_id: int
    status: str
    violations: list[str] = []
    requires_human_review: bool
    ocr_text: dict
    message: str


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_name: str
    job_level: str
    manager_id: str | None
    project_code: str
    is_manager: bool = False


class TeamClaimResponse(BaseModel):
    claim_id: int
    claim_name: str
    estimated_amount: float
    status: str
    violations: str | None
    requires_human_review: bool
    document_path: str | None
    ocr_text: dict | None
    created_at: datetime
    employee_id: str
    employee_name: str
    job_level: str


class ApprovalActionRequest(BaseModel):
    manager_id: str = Field(..., min_length=1)
    note: str | None = Field(default=None, max_length=500)


class ApprovalActionResponse(BaseModel):
    claim_id: int
    status: str
    message: str


class BudgetCheckResult(BaseModel):
    account_id: str
    remaining_budget: float
    claim_amount: float
    within_budget: bool
    message: str


class OcrExtractedText(BaseModel):
    merchant: str
    date: str
    total_amount: float

    @field_validator("total_amount")
    @classmethod
    def total_amount_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("total_amount must be positive")
        return value