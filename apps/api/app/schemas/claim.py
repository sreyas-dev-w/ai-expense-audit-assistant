"""Claim API contracts.

``category`` and ``category_data`` are coupled: the payload is a discriminated
union selected by ``category``, so ``category_data`` is always validated
against exactly one of the category data models in ``app/schemas/expense.py``.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClaimPriority, ClaimStatus, Currency, ExpenseCategory
from app.schemas.expense import (
    AccommodationData,
    FoodMealsData,
    OtherData,
    TravelData,
)


class ClaimBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    business_purpose: str | None = None
    merchant_name: str | None = None
    project_code: str | None = None
    claim_amount: Decimal
    currency: Currency = Currency.INR
    receipt_url: str | None = None


class FoodMealsClaimCreate(ClaimBase):
    category: Literal[ExpenseCategory.FOOD_MEALS]
    category_data: FoodMealsData


class TravelClaimCreate(ClaimBase):
    category: Literal[ExpenseCategory.TRAVEL]
    category_data: TravelData


class AccommodationClaimCreate(ClaimBase):
    category: Literal[ExpenseCategory.ACCOMMODATION]
    category_data: AccommodationData


class OtherClaimCreate(ClaimBase):
    category: Literal[ExpenseCategory.OTHER]
    category_data: OtherData


ClaimCreate = Annotated[
    Union[
        FoodMealsClaimCreate,
        TravelClaimCreate,
        AccommodationClaimCreate,
        OtherClaimCreate,
    ],
    Field(discriminator="category"),
]


class ClaimReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: int
    employee_id: str
    auditer_id: str | None = None
    auditer_notes: str | None = None
    project_code: str | None = None
    business_purpose: str | None = None
    merchant_name: str | None = None
    claim_amount: Decimal
    currency: Currency
    status: ClaimStatus
    priority: ClaimPriority
    receipt_url: str | None = None
    claim_created_at: datetime | None = None
    claim_updated_at: datetime | None = None
    receipt_created_at: datetime | None = None


class FoodMealsClaimRead(ClaimReadBase):
    category: Literal[ExpenseCategory.FOOD_MEALS]
    category_data: FoodMealsData


class TravelClaimRead(ClaimReadBase):
    category: Literal[ExpenseCategory.TRAVEL]
    category_data: TravelData


class AccommodationClaimRead(ClaimReadBase):
    category: Literal[ExpenseCategory.ACCOMMODATION]
    category_data: AccommodationData


class OtherClaimRead(ClaimReadBase):
    category: Literal[ExpenseCategory.OTHER]
    category_data: OtherData


ClaimRead = Annotated[
    Union[
        FoodMealsClaimRead,
        TravelClaimRead,
        AccommodationClaimRead,
        OtherClaimRead,
    ],
    Field(discriminator="category"),
]


class ClaimListItem(ClaimReadBase):
    """Table-facing row: the claim plus the latest audit run's headline fields.

    Deliberately keeps ``category_data`` opaque -- list views render the claim
    summary, and the detail endpoint returns the validated ``ClaimRead`` union.
    """

    category: ExpenseCategory
    category_data: dict[str, Any] = Field(default_factory=dict)
    employee_name: str | None = None
    has_audit: bool = False
    audit_recommendation: str | None = None
    audit_confidence: Decimal | None = None


class ClaimDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ClaimDecisionRequest(BaseModel):
    """A manager's approve/reject call. Notes are required either way."""

    model_config = ConfigDict(extra="forbid")

    decision: ClaimDecision
    notes: str = Field(min_length=1, max_length=4000)