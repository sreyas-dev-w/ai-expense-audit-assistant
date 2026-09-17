"""Validation Agent contracts.

Input reuses the OCR envelope (``OCRResponse``) so extraction and validation
cannot drift. Output is a structured, auditable result the Audit Agent
aggregates and that ``store_validation_result`` persists into
``agent_response.validation_response``.

See ``docs/agents/validation-agent.md`` and ``docs/schemas/data-contracts.md``.
"""
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.extraction import (
    AccommodationExtraction,
    FoodMealsExtraction,
    OCRResponse,
    OtherExtraction,
    TravelExtraction,
)


_EXTRACTION_BY_CATEGORY = {
    "FOOD_MEALS": FoodMealsExtraction,
    "TRAVEL": TravelExtraction,
    "ACCOMMODATION": AccommodationExtraction,
    "OTHERS": OtherExtraction,
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ValidationSeverity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class ValidationFindingCategory(str, Enum):
    AMOUNT = "amount"
    DATE = "date"
    FIELD = "field"
    MISMATCH = "mismatch"
    AUTHENTICITY = "authenticity"
    BUDGET = "budget"
    DUPLICATE = "duplicate"


class ValidationCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class ValidationVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


class ValidationAgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class ValidationRequest(OCRResponse):
    """OCR payload plus optional persist targeting.

    ``claim_id`` is required to insert into ``agent_response`` and to exclude
    the current claim from duplicate search. ``persist`` defaults to true;
    the insert is skipped when ``claim_id`` is missing.
    """

    model_config = ConfigDict(extra="ignore")

    claim_id: int | None = None
    persist: bool = True

    @model_validator(mode="before")
    @classmethod
    def _coerce_extraction_by_category(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        submission = data.get("submission")
        category = (
            submission.get("expense_category")
            if isinstance(submission, dict)
            else None
        )
        extraction = data.get("extraction")
        model = _EXTRACTION_BY_CATEGORY.get(category)
        if model is not None and isinstance(extraction, dict):
            data = dict(data)
            data["extraction"] = model.model_validate(extraction)
        return data


# ---------------------------------------------------------------------------
# Output fragments
# ---------------------------------------------------------------------------


class ValidationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: ValidationSeverity
    category: ValidationFindingCategory
    description: str
    detail: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class ValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_name: str
    status: ValidationCheckStatus
    rule_id: str | None = None


class DuplicateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: int
    score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str] = Field(default_factory=list)


class BudgetSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    remaining_budget: Decimal
    claim_amount: Decimal
    currency: str | None = None
    within_budget: bool


class AuthenticityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_suspicious: bool = False
    forged_likelihood: float = Field(default=0.0, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class ValidationReasoningOutput(BaseModel):
    """Structured LLM output for the authenticity/reason node."""

    model_config = ConfigDict(extra="forbid")

    authenticity: AuthenticityAssessment
    extra_findings: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValidationAgentOutput(BaseModel):
    """Structured decision-support produced by the Validation Agent."""

    model_config = ConfigDict(extra="forbid")

    verdict: ValidationVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    findings: list[ValidationFinding] = Field(default_factory=list)
    checks: list[ValidationCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list)
    budget: BudgetSnapshot | None = None
    authenticity: AuthenticityAssessment | None = None
    summary: str | None = None


class ValidationAgentError(BaseModel):
    code: str
    message: str
    agent: str = "validation_agent"


class ValidationAgentResult(BaseModel):
    """Envelope the subgraph returns to the Audit Agent / HTTP layer.

    Errors are first-class: either ``output`` (success) or ``error`` is set.
    """

    status: ValidationAgentStatus
    output: ValidationAgentOutput | None = None
    error: ValidationAgentError | None = None


class ValidationEvaluateResponse(ValidationAgentResult):
    """HTTP response: agent envelope plus optional persist receipt."""

    stored_agent_response_id: int | None = None
