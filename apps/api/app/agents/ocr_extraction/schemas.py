from typing import Optional

from pydantic import BaseModel, Field


class Submission(BaseModel):
    employee_id: str
    declared_category: str
    business_purpose: Optional[str] = None
    submitted_at: str
    receipt_provided: bool


class EmployeeContext(BaseModel):
    employee_id: str
    found: bool
    employee_name: Optional[str] = None
    job_level: Optional[str] = None
    manager_id: Optional[str] = None
    project_code: Optional[str] = None
    account_id: Optional[str] = None


class Receipt(BaseModel):
    sha256: str


class LineItem(BaseModel):
    description: str
    amount: float
    receipt_present: bool


class Extraction(BaseModel):
    is_receipt: bool
    merchant_name: Optional[str] = None
    invoice_number: Optional[str] = None
    expense_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None

    line_items: list[LineItem] = Field(
        default_factory=list
    )


class OCRResponse(BaseModel):
    submission: Submission
    employee_context: EmployeeContext
    receipt: Receipt
    extraction: Extraction