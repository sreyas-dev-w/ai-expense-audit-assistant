"""Maps the OCR/extraction output into the canonical category-data contracts.

``app/schemas/expense.py`` defines the canonical ``category_data`` shape per
expense category — reused by the claim API, the Policy RAG Agent and (once
built) the Validation Agent. Extraction output is normalized into exactly one
of those models so no agent contract can drift from the claim API contract.

The mapping is a **merge**: OCR fields take precedence, but the claim's already
validated ``category_data`` supplies any field OCR could not read, so the
result always satisfies the required fields of the category model.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.models.enums import ExpenseCategory
from app.schemas.expense import (
    AccommodationData,
    FoodMealsData,
    LineItem,
    OtherData,
    TravelData,
)
from app.schemas.extraction import (
    AccommodationExtraction,
    Extraction,
    FoodMealsExtraction,
    OtherExtraction,
    TravelExtraction,
)

_CATEGORY_DATA_MODELS = {
    ExpenseCategory.FOOD_MEALS: FoodMealsData,
    ExpenseCategory.TRAVEL: TravelData,
    ExpenseCategory.ACCOMMODATION: AccommodationData,
    ExpenseCategory.OTHER: OtherData,
}

_CATEGORY_EXTRACTION_TYPES = {
    ExpenseCategory.FOOD_MEALS: FoodMealsExtraction,
    ExpenseCategory.TRAVEL: TravelExtraction,
    ExpenseCategory.ACCOMMODATION: AccommodationExtraction,
    ExpenseCategory.OTHER: OtherExtraction,
}

_EXTRACTION_TO_CATEGORY = {cls: cat for cat, cls in _CATEGORY_EXTRACTION_TYPES.items()}


class MapperError(Exception):
    """A stage contract could not be mapped from the extraction output."""

    def __init__(self, message: str, *, code: str = "mapping_failed"):
        super().__init__(message)
        self.code = code


def normalize_category(label: str) -> ExpenseCategory:
    """Normalize an OCR input label (e.g. ``OTHERS``) to a canonical category.

    The OCR agent accepts ``OTHERS`` for the other-expense category, while the
    canonical enum is ``OTHER``.
    """
    normalized = label.strip().upper().replace("OTHERS", "OTHER")
    return ExpenseCategory(normalized)


def category_from_extraction(extraction: Extraction) -> ExpenseCategory:
    try:
        return _EXTRACTION_TO_CATEGORY[type(extraction)]
    except KeyError as exc:
        raise MapperError(
            f"Unsupported extraction type: {type(extraction).__name__}"
        ) from exc


def map_extraction_to_category_data(
    extraction: Extraction,
    *,
    category: ExpenseCategory,
    claimed_category_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge the extraction into the canonical ``category_data`` payload.

    Returns a JSON-safe dict matching exactly one category data model in
    ``app/schemas/expense.py`` (validated against it). Raises ``MapperError``
    when the extraction type contradicts the claim category or the merged
    payload does not satisfy the category model.
    """
    expected = _CATEGORY_EXTRACTION_TYPES.get(category)
    if expected is None or not isinstance(extraction, expected):
        actual = category_from_extraction(extraction)
        raise MapperError(
            f"Extraction category ({actual.value}) does not match the claim "
            f"category ({category.value})",
            code="category_mismatch",
        )

    claimed = claimed_category_data or {}
    model = _CATEGORY_DATA_MODELS[category]
    claimed_filtered = {
        key: value for key, value in claimed.items() if key in model.model_fields
    }

    if category == ExpenseCategory.FOOD_MEALS:
        payload = _food_meals(extraction, claimed_filtered)
    elif category == ExpenseCategory.TRAVEL:
        payload = _travel(extraction, claimed_filtered)
    elif category == ExpenseCategory.ACCOMMODATION:
        payload = _accommodation(extraction, claimed_filtered)
    else:
        payload = _other(extraction, claimed_filtered)

    try:
        model.model_validate(payload)
    except ValidationError as exc:
        raise MapperError(
            f"Mapped category data is invalid for {category.value}: {exc.errors()}"
        ) from exc

    return {key: _jsonable(value) for key, value in payload.items()}


def _food_meals(
    extraction: FoodMealsExtraction, claimed: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(claimed)
    if extraction.merchant_name:
        payload["merchant_name"] = extraction.merchant_name
    if extraction.meal_type:
        payload["meal_type"] = extraction.meal_type
    if extraction.number_of_people is not None:
        payload["number_of_people"] = extraction.number_of_people
    payload["line_items"] = _line_items(
        extraction.line_items, payload.get("line_items")
    )
    return payload


def _travel(
    extraction: TravelExtraction, claimed: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(claimed)
    if extraction.mode_of_transportation:
        payload["travel_type"] = extraction.mode_of_transportation
    if extraction.origin:
        payload["origin"] = extraction.origin
    if extraction.destination:
        payload["destination"] = extraction.destination
    if extraction.expense_date:
        payload["travel_date"] = parse_date(extraction.expense_date)
    if extraction.travel_class:
        payload["travel_class"] = extraction.travel_class
    payload["line_items"] = _line_items(
        extraction.line_items, payload.get("line_items")
    )
    return payload


def _accommodation(
    extraction: AccommodationExtraction, claimed: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(claimed)
    if extraction.merchant_name:
        payload["hotel_name"] = extraction.merchant_name
    if extraction.location:
        payload["location"] = extraction.location
    if extraction.check_in:
        payload["check_in"] = parse_date(extraction.check_in)
    if extraction.check_out:
        payload["check_out"] = parse_date(extraction.check_out)
    if extraction.number_of_nights is not None:
        payload["number_of_nights"] = extraction.number_of_nights
    if extraction.no_of_rooms is not None:
        payload["no_of_rooms"] = extraction.no_of_rooms
    if extraction.room_type:
        payload["room_type"] = extraction.room_type
    payload["line_items"] = _line_items(
        extraction.line_items, payload.get("line_items")
    )
    return payload


def _other(extraction: OtherExtraction, claimed: dict[str, Any]) -> dict[str, Any]:
    payload = dict(claimed)
    if extraction.expense_category:
        payload["expense_type"] = extraction.expense_category
    if extraction.merchant_name:
        payload["merchant_name"] = extraction.merchant_name
    payload["line_items"] = _line_items(
        extraction.line_items, payload.get("line_items")
    )
    return payload


def parse_date(value: str) -> date:
    """Parse an OCR date string into a ``date``.

    Supports ISO format plus the common slash/dash day-first formats OCR
    engines tend to emit. Failure is explicit (``MapperError``).
    """
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError as exc:
        raise MapperError(
            f"Could not parse date from OCR output: {value!r}",
            code="invalid_date",
        ) from exc


def _line_items(
    extraction_items: list | None, claimed_items: Any
) -> list[dict[str, Any]]:
    extracted = [
        {
            "item_header": item.description,
            "item_amount": _money(item.amount),
        }
        for item in extraction_items or []
        if item.description and item.amount is not None
    ]
    if extracted:
        return extracted

    claimed = [
        {
            "item_header": str(item.get("item_header", "")),
            "item_amount": _money(item.get("item_amount")),
        }
        for item in (claimed_items or [])
        if item.get("item_header")
    ]
    return claimed


def _money(value: Any) -> Decimal:
    """Decimal normalized to the 2-dp money precision used by the DB models."""
    try:
        return _decimal(value).quantize(Decimal("0.01"))
    except Exception as exc:  # pragma: no cover - _decimal already guards
        raise MapperError(f"Invalid amount in extraction: {value!r}") from exc


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError) as exc:
        raise MapperError(f"Invalid amount in extraction: {value!r}") from exc


def _jsonable(value: Any) -> Any:
    """Recursively convert mapped values into a DB(JSON)-safe representation."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value