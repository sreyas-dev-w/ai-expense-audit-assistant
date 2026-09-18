"""Flatten category-specific OCR fields into a single view for the rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.rules.helpers import to_decimal
from app.schemas.extraction import AccommodationExtraction
from app.schemas.validation import ValidationRequest


@dataclass
class NormalizedExpense:
    category: str
    spend_amount: Decimal | None
    extracted_total: Decimal | None
    currency: str | None
    submitted_at: datetime
    expense_date: date | None
    expense_date_raw: str | None
    check_in: date | None
    check_out: date | None
    submitted_check_in: date | None
    submitted_check_out: date | None
    number_of_days: int | None
    origin: str | None
    destination: str | None
    merchant_extracted: str | None
    merchant_submitted: str | None
    document_number: str | None
    is_receipt: bool
    receipt_provided: bool
    payment_status: str | None
    line_item_amounts: list[Decimal]
    employee_id_submission: str
    employee_id_context: str | None
    account_id: str | None
    date_parse_errors: list[str] = field(default_factory=list)


def parse_date(value: date | datetime | str | None) -> tuple[date | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    text = str(value).strip()
    if not text:
        return None, None
    try:
        return date.fromisoformat(text[:10]), None
    except ValueError:
        return None, text


def normalize_request(request: ValidationRequest) -> NormalizedExpense:
    extraction = request.extraction
    claimed = request.category_data or {}
    date_errors: list[str] = []

    spend_amount = to_decimal(request.claim_amount)
    extracted_total = to_decimal(getattr(extraction, "claim_amount", None))
    currency = getattr(extraction, "currency", None) or request.currency
    line_item_amounts = [
        amount
        for item in getattr(extraction, "line_items", []) or []
        if (amount := to_decimal(getattr(item, "amount", None))) is not None
    ]

    expense_date = None
    expense_date_raw = None
    raw_date = getattr(extraction, "expense_date", None)
    if raw_date:
        expense_date, expense_date_raw = parse_date(raw_date)
        if expense_date is None:
            date_errors.append(f"expense_date={raw_date}")

    check_in = None
    check_out = None
    if isinstance(extraction, AccommodationExtraction):
        check_in, raw_in = parse_date(extraction.check_in)
        check_out, raw_out = parse_date(extraction.check_out)
        if extraction.check_in and check_in is None:
            date_errors.append(f"check_in={raw_in or extraction.check_in}")
        if extraction.check_out and check_out is None:
            date_errors.append(f"check_out={raw_out or extraction.check_out}")
        if expense_date is None:
            expense_date = check_in

    submitted_check_in, _ = parse_date(claimed.get("check_in"))
    submitted_check_out, _ = parse_date(claimed.get("check_out"))

    return NormalizedExpense(
        category=request.category,
        spend_amount=spend_amount,
        extracted_total=extracted_total,
        currency=currency,
        submitted_at=request.submitted_at,
        expense_date=expense_date,
        expense_date_raw=expense_date_raw,
        check_in=check_in or submitted_check_in,
        check_out=check_out or submitted_check_out,
        submitted_check_in=submitted_check_in,
        submitted_check_out=submitted_check_out,
        number_of_days=_int_or_none(claimed.get("number_of_nights")),
        origin=getattr(extraction, "origin", None),
        destination=getattr(extraction, "destination", None),
        merchant_extracted=getattr(extraction, "merchant_name", None),
        merchant_submitted=_submitted_merchant(request, claimed),
        document_number=getattr(extraction, "receipt_no", None),
        is_receipt=bool(getattr(extraction, "is_receipt", False)),
        receipt_provided=request.receipt_provided,
        payment_status=getattr(extraction, "payment_status", None),
        line_item_amounts=line_item_amounts,
        employee_id_submission=request.employee_id,
        employee_id_context=request.employee_id,
        account_id=request.account_id,
        date_parse_errors=date_errors,
    )


def _submitted_merchant(request: ValidationRequest, claimed: dict[str, Any]) -> str | None:
    if request.merchant_name:
        return request.merchant_name
    return claimed.get("merchant_name") or claimed.get("hotel_name")


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def claim_amount(expense: NormalizedExpense) -> Decimal | None:
    if expense.extracted_total is not None:
        return expense.extracted_total
    return expense.spend_amount