from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# ============================================================
# OCR EXTRACTION LINE ITEMS
# ============================================================

class LineItem(BaseModel):
    description: str
    amount: Optional[float] = None


# ============================================================
# OCR EXTRACTION BY CATEGORY
# ============================================================

class FoodMealsExtraction(BaseModel):
    is_receipt: bool
    receipt_no: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[str] = None
    claim_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    currency: Optional[str] = None
    payment_status: Optional[str] = None
    meal_type: Optional[Literal["VEG", "NON_VEG", "MIXED"]] = None


class TravelExtraction(BaseModel):
    is_receipt: bool
    receipt_no: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[str] = None
    claim_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    currency: Optional[str] = None
    payment_status: Optional[str] = None
    mode_of_transportation: Optional[str] = None


class AccommodationExtraction(BaseModel):
    is_receipt: bool
    receipt_no: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[str] = None
    claim_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    currency: Optional[str] = None
    payment_status: Optional[str] = None


class OtherExtraction(BaseModel):
    is_receipt: bool
    receipt_no: Optional[str] = None
    expense_category: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[str] = None
    claim_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    currency: Optional[str] = None
    payment_status: Optional[str] = None


Extraction = Union[
    FoodMealsExtraction,
    TravelExtraction,
    AccommodationExtraction,
    OtherExtraction,
]