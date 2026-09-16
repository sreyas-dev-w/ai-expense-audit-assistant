"""Map a persisted claim + related rows onto OCR Agent process kwargs.

Claim ``ExpenseCategory.OTHER`` becomes OCR ``OTHERS``. Category JSONB is
translated onto the OCR form fields without overwriting claim amounts.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.models.enums import ExpenseCategory
from app.schemas.audit import AuditContext


class ClaimToOcrMappingError(Exception):
    def __init__(self, message: str, *, code: str = "claim_to_ocr_mapping_error"):
        super().__init__(message)
        self.code = code


def ocr_expense_category(category: ExpenseCategory | str) -> str:
    value = category.value if isinstance(category, ExpenseCategory) else str(category)
    if value in {"OTHER", "OTHERS"}:
        return "OTHERS"
    return value


def claim_to_ocr_kwargs(context: AuditContext) -> dict[str, Any]:
    """Build ``OCRAgent.process`` kwargs from loaded audit context."""
    claim = context.claim
    data = claim.category_data or {}
    kwargs: dict[str, Any] = {
        "employee_id": claim.employee_id,
        "expense_category": ocr_expense_category(claim.category),
        "spend_amount": float(claim.claim_amount) if claim.claim_amount is not None else None,
        "business_purpose": claim.business_purpose,
        "employee": context.employee.model_dump(),
        "project": context.project.model_dump() if context.project else None,
    }

    category = claim.category
    if category == ExpenseCategory.FOOD_MEALS:
        kwargs["meal_type"] = data.get("meal_type")
        kwargs["number_of_people"] = data.get("number_of_people")
    elif category == ExpenseCategory.TRAVEL:
        kwargs["travel_type"] = data.get("travel_type")
        kwargs["origin"] = data.get("origin")
        kwargs["destination"] = data.get("destination")
        kwargs["travel_class"] = data.get("travel_class")
    elif category == ExpenseCategory.ACCOMMODATION:
        kwargs["location"] = data.get("location")
        kwargs["check_in_date"] = _as_date(data.get("check_in"))
        kwargs["check_out_date"] = _as_date(data.get("check_out"))
        kwargs["number_of_days"] = data.get("number_of_nights")
        kwargs["room_type"] = data.get("room_type")
    else:
        kwargs["expense_type"] = data.get("expense_type")
        kwargs["additional_details"] = _stringify_additional(data.get("additional_details"))
    return kwargs


def _as_date(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return None


def _stringify_additional(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)
