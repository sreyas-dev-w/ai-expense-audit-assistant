from datetime import date, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# CATEGORY-SPECIFIC DETAILS
# ============================================================

class FoodMealsDetails(BaseModel):
    expense_category: Literal["FOOD_MEALS"]

    spend_amount: float
    business_purpose: Optional[str] = None

    meal_type: Literal[
        "VEG",
        "NON_VEG",
        "MIXED"
    ]

    number_of_people: int


class TravelDetails(BaseModel):
    expense_category: Literal["TRAVEL"]

    spend_amount: float

    travel_type: Literal[
        "FLIGHT",
        "TRAIN",
        "BUS",
        "CAR",
        "BIKE"
    ]

    origin: str
    destination: str

    travel_class: Literal[
        "BUSINESS_CLASS",
        "ECONOMY_CLASS"
    ]

    business_purpose: Optional[str] = None


class AccommodationDetails(BaseModel):
    expense_category: Literal["ACCOMMODATION"]

    spend_amount: float
    business_purpose: Optional[str] = None

    location: str

    check_in_date: date
    check_out_date: date

    number_of_days: int

    room_type: str


class OtherDetails(BaseModel):
    expense_category: Literal["OTHERS"]

    spend_amount: float
    business_purpose: Optional[str] = None

    expense_type: str
    additional_details: Optional[str] = None


# ============================================================
# CATEGORY UNION
# ============================================================

ExpenseDetails = Union[
    FoodMealsDetails,
    TravelDetails,
    AccommodationDetails,
    OtherDetails,
]


# ============================================================
# SUBMISSION
# ============================================================

class Submission(BaseModel):
    employee_id: str

    expense_category: Literal[
        "FOOD_MEALS",
        "TRAVEL",
        "ACCOMMODATION",
        "OTHERS"
    ]

    details: ExpenseDetails

    submitted_at: datetime

    receipt_provided: bool


# ============================================================
# EMPLOYEE CONTEXT
# ============================================================

class EmployeeContext(BaseModel):
    employee_id: str
    found: bool

    employee_name: Optional[str] = None
    job_level: Optional[str] = None
    manager_id: Optional[str] = None
    project_code: Optional[str] = None
    account_id: Optional[str] = None


# ============================================================
# OCR EXTRACTION
# ============================================================

class LineItem(BaseModel):
    description: str
    amount: float
    receipt_present: bool


class FoodMealsExtraction(BaseModel):
    is_receipt: bool
    merchant_name: Optional[str] = None
    bill_number: Optional[str] = None
    meal_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    line_items: list[LineItem] = Field(
        default_factory=list
    )
class TravelExtraction(BaseModel):
    is_receipt: bool
    merchant_name: Optional[str] = None
    ticket_number: Optional[str] = None
    travel_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    line_items: list[LineItem] = Field(
        default_factory=list
    )
class AccommodationExtraction(BaseModel):
    is_receipt: bool
    hotel_name: Optional[str] = None
    booking_number: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    line_items: list[LineItem] = Field(
        default_factory=list
    )
class OtherExtraction(BaseModel):
    is_receipt: bool
    merchant_name: Optional[str] = None
    receipt_number: Optional[str] = None
    expense_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    line_items: list[LineItem] = Field(
        default_factory=list
    )

Extraction = Union[
    FoodMealsExtraction,
    TravelExtraction,
    AccommodationExtraction,
    OtherExtraction,
]

# ============================================================
# FINAL OCR RESPONSE
# ============================================================

class OCRResponse(BaseModel):
    submission: Submission
    employee_context: EmployeeContext
    extraction: Extraction