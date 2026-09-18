"""Policy domain contracts.

Three groups of schemas live here:

- **Ingestion / search contracts** — the HTTP API for loading PDFs into the
  vector store and for searching the policy store (``app/api/policies.py`` and
  ``app/services/policy_document_service.py`` / ``app/services/rag_service.py``).
- **Policy agent input** — the structured claim the Policy RAG Agent receives.
  Category-specific data reuses ``app/schemas/expense.py`` (defined once),
  discriminated on ``category`` exactly like the claim API. Common claim
  details mirror the ``claims`` + ``employees`` DB models.
- **Policy agent output** — the grounded, decision-support result the agent
  returns, covering violations, passed checks, confidence, decision, reasons
  and grounding references.

See ``docs/agents/policy-rag-agent.md`` and ``docs/backend/auditability.md``.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Currency, ExpenseCategory, JobLevel
from app.schemas.expense import (
    AccommodationData,
    FoodMealsData,
    OtherData,
    TravelData,
)


# ---------------------------------------------------------------------------
# Ingestion / search contracts
# ---------------------------------------------------------------------------


class PolicyDocumentSummary(BaseModel):
    """A row in ``policy_documents`` as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    policy_id: int
    filename: str
    policy_version: str | None = None
    status: str
    error: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class PolicyIngestResult(BaseModel):
    """Result of a PDF ingestion request."""

    policy_id: int
    filename: str
    doc_hash: str
    chunk_count: int
    reingested: bool = False


class PolicySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    policy_id: int | None = None
    similarity_threshold: float = Field(default=0.0, ge=-1.0, le=1.0)


class RetrievedPolicyChunk(BaseModel):
    chunk_id: int
    policy_id: int
    policy_filename: str | None = None
    content: str
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    similarity_score: float

    model_config = ConfigDict(populate_by_name=True)


class PolicySearchResponse(BaseModel):
    query: str
    top_k: int
    count: int
    results: list[RetrievedPolicyChunk]


# ---------------------------------------------------------------------------
# Policy agent input
# ---------------------------------------------------------------------------


class PolicyClaimContext(BaseModel):
    """Common claim details shared by every category evaluation.

    Mirrors the relevant ``claims`` / ``employees`` model columns; category is
    carried by the outer discriminated union.
    """

    model_config = ConfigDict(extra="forbid")

    claim_id: int | None = None
    employee_id: str
    employee_job_level: JobLevel | None = None
    business_purpose: str | None = None
    merchant_name: str | None = None
    project_code: str | None = None
    claim_amount: Decimal
    currency: Currency = Currency.INR
    expense_date: date | None = None


class PolicyEvaluationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: PolicyClaimContext


class FoodMealsPolicyEvaluation(PolicyEvaluationBase):
    category: Literal[ExpenseCategory.FOOD_MEALS]
    category_data: FoodMealsData


class TravelPolicyEvaluation(PolicyEvaluationBase):
    category: Literal[ExpenseCategory.TRAVEL]
    category_data: TravelData


class AccommodationPolicyEvaluation(PolicyEvaluationBase):
    category: Literal[ExpenseCategory.ACCOMMODATION]
    category_data: AccommodationData


class OtherPolicyEvaluation(PolicyEvaluationBase):
    category: Literal[ExpenseCategory.OTHER]
    category_data: OtherData


PolicyEvaluationRequest = Annotated[
    Union[
        FoodMealsPolicyEvaluation,
        TravelPolicyEvaluation,
        AccommodationPolicyEvaluation,
        OtherPolicyEvaluation,
    ],
    Field(discriminator="category"),
]


# ---------------------------------------------------------------------------
# Policy agent output
# ---------------------------------------------------------------------------


class PolicySeverity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class PolicyDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


class PolicyCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class PolicyViolation(BaseModel):
    policy_reference: str | None = None
    severity: PolicySeverity = PolicySeverity.WARNING
    description: str
    detail: str | None = None
    related_chunk_ids: list[int] = Field(default_factory=list)


class PolicyCheck(BaseModel):
    check_name: str
    status: PolicyCheckStatus
    policy_reference: str | None = None
    related_chunk_ids: list[int] = Field(default_factory=list)


class PolicyReference(BaseModel):
    """Grounding reference to a retrieved policy chunk."""

    chunk_id: int
    policy_id: int
    policy_filename: str | None = None
    content: str
    similarity_score: float | None = None


class PolicyAgentOutput(BaseModel):
    """Structured, grounded decision support produced by the Policy RAG Agent."""

    decision: PolicyDecision
    confidence: float = Field(ge=0.0, le=1.0)
    violations: list[PolicyViolation] = Field(default_factory=list)
    checks: list[PolicyCheck] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    references: list[PolicyReference] = Field(default_factory=list)
    summary: str | None = None


class PolicyAgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class PolicyAgentError(BaseModel):
    code: str
    message: str
    agent: str = "policy_rag_agent"


class PolicyAgentResult(BaseModel):
    """Envelope the subgraph returns to the Audit Agent.

    Errors are first-class workflow states: either ``output`` (success) or
    ``error`` is set; never both, never neither.
    """

    status: PolicyAgentStatus
    output: PolicyAgentOutput | None = None
    error: PolicyAgentError | None = None