"""Claim API contracts.

``category`` and ``category_data`` are coupled: the payload is a discriminated
union selected by ``category``, so ``category_data`` is always validated
against exactly one of the category data models in ``app/schemas/expense.py``.
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
    Currency,
    ExpenseCategory,
)
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


class ClaimSubmissionResponse(BaseModel):
    """The 201 resource-created payload returned once a claim is persisted.

    ``status`` is ``SUBMITTED`` and ``ai_run_status`` is ``PENDING``: the Audit
    Agent is handed off in the background and transitions the claim as it runs.
    """

    message: str = "Claim submitted successfully"
    claim_id: int
    status: ClaimStatus
    ai_run_status: AIRunStatus = AIRunStatus.PENDING
    receipt_url: str | None = None


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


# ============================================================
# EMPLOYEE CLAIM DETAILS RESPONSE
# ============================================================

class ClaimDetailsResponse(BaseModel):
    claim_id: int
    business_purpose: str | None
    merchant_name: str | None
    category: str
    category_data: dict

    employee_id: str
    auditer_id: str | None
    auditer_notes: str | None

    project_code: str | None

    claim_amount: Decimal
    tax_amount: Decimal
    currency: str

    status: str
    priority: str

    ai_run_status: str
    ai_decision: str | None

    receipt_url: str | None

    claim_created_at: datetime | None
    claim_updated_at: datetime | None
    receipt_created_at: datetime | None

class ClaimAuditUpdate(BaseModel):
    status: ClaimStatus
    priority: ClaimPriority
    auditer_id: str
    auditer_notes: str | None = None

    model_config = ConfigDict(extra="forbid")