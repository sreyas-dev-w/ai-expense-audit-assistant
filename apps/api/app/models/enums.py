import enum


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AUD = "AUD"
    CAD = "CAD"
    JPY = "JPY"


class JobLevel(str, enum.Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"


class ClaimCategory(str, enum.Enum):
    """Legacy claim categories, kept only for Alembic migration history.

    Current claims use ExpenseCategory.
    """

    MEALS = "meals"
    TRAVEL = "travel"
    LODGING = "lodging"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    OFFICE_SUPPLIES = "office_supplies"
    SOFTWARE = "software"
    SERVICES = "services"
    OTHER = "other"


class ExpenseCategory(str, enum.Enum):
    FOOD_MEALS = "FOOD_MEALS"
    TRAVEL = "TRAVEL"
    ACCOMMODATION = "ACCOMMODATION"
    OTHER = "OTHER"


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_AUDIT = "in_audit"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ClaimPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AIRunStatus(str, enum.Enum):
    """Whether the AI reasoning pipeline has completed for a claim."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AIDecision(str, enum.Enum):
    """Recommendation produced by the AI reasoning pipeline."""

    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"