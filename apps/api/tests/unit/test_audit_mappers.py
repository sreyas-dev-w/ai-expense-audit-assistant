"""Unit tests for the stage contract mappers.

Coverage: extraction → canonical category data merge (``category_data_mapper``)
and extraction + claim context → Policy RAG input (``policy_request_mapper``),
including the error paths (``MapperError``).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.agents.mappers.category_data_mapper import (
    MapperError,
    map_extraction_to_category_data,
    normalize_category,
    parse_date,
)
from app.agents.mappers.policy_request_mapper import map_to_policy_request
from app.models.enums import Currency, ExpenseCategory
from app.schemas.expense import FoodMealsData, LineItem
from app.schemas.extraction import (
    FoodMealsExtraction,
    OtherExtraction,
    TravelExtraction,
)
from tests.conftest import (
    make_food_audit_context,
    sample_food_extraction,
)

CLAIMED = {
    "meal_type": "Dinner",
    "merchant_name": "Zulu Bistro",
    "number_of_people": 2,
    "line_items": [{"item_header": "Dinner", "item_amount": "2000.00"}],
}


def _food_extraction() -> FoodMealsExtraction:
    return sample_food_extraction()


def test_merge_extraction_over_claimed_category_data():
    extraction = _food_extraction()
    extraction.merchant_name = "Updated Bistro"

    payload = map_extraction_to_category_data(
        extraction,
        category=ExpenseCategory.FOOD_MEALS,
        claimed_category_data=CLAIMED,
    )

    assert payload["merchant_name"] == "Updated Bistro"
    assert payload["meal_type"] == "NON_VEG"
    assert payload["number_of_people"] == 2
    assert payload["line_items"] == [
        {"item_header": "Dinner", "item_amount": "2000.00"}
    ]
    assert FoodMealsData.model_validate(payload) is not None


def test_line_items_fall_back_to_claimed_when_extraction_has_none():
    extraction = _food_extraction()
    extraction.line_items = []
    extraction.number_of_people = 7  # still applies OCR override for other fields

    payload = map_extraction_to_category_data(
        extraction,
        category=ExpenseCategory.FOOD_MEALS,
        claimed_category_data=CLAIMED,
    )

    assert payload["line_items"] == [
        {"item_header": "Dinner", "item_amount": "2000.00"}
    ]


def test_travel_extraction_maps_dates_and_transport():
    extraction = TravelExtraction(
        is_receipt=True,
        merchant_name="Indigo",
        mode_of_transportation="flight",
        origin="BLR",
        destination="DEL",
        travel_class="economy",
        expense_date="12-03-2026",
        line_items=[],
    )
    claimed = {
        "travel_type": "taxi",
        "origin": "BLR",
        "destination": "DEL",
        "travel_date": "2026-03-01",
        "line_items": [{"item_header": "Cab", "item_amount": "800.00"}],
    }

    payload = map_extraction_to_category_data(
        extraction,
        category=ExpenseCategory.TRAVEL,
        claimed_category_data=claimed,
    )

    assert payload["travel_type"] == "flight"
    assert payload["travel_date"] == "2026-03-12"
    assert payload["line_items"] == [
        {"item_header": "Cab", "item_amount": "800.00"}
    ]


def test_category_mismatch_raises():
    extraction = OtherExtraction(
        is_receipt=True, expense_category="Stationery", line_items=[]
    )
    with pytest.raises(MapperError) as exc_info:
        map_extraction_to_category_data(
            extraction,
            category=ExpenseCategory.FOOD_MEALS,
            claimed_category_data=CLAIMED,
        )
    assert exc_info.value.code == "category_mismatch"


def test_invalid_date_raises():
    extraction = TravelExtraction(
        is_receipt=True,
        mode_of_transportation="flight",
        expense_date="not-a-date",
        line_items=[],
    )
    with pytest.raises(MapperError) as exc_info:
        map_extraction_to_category_data(
            extraction,
            category=ExpenseCategory.TRAVEL,
            claimed_category_data={
                "travel_type": "flight",
                "origin": "A",
                "destination": "B",
                "travel_date": "2026-03-01",
                "line_items": [],
            },
        )
    assert exc_info.value.code == "invalid_date"


def test_parse_date_formats():
    assert parse_date("2026-03-01") == date(2026, 3, 1)
    assert parse_date("01-03-2026") == date(2026, 3, 1)
    assert parse_date("01/03/2026") == date(2026, 3, 1)


def test_normalize_category_labels():
    assert normalize_category("OTHERS") == ExpenseCategory.OTHER
    assert normalize_category("other") == ExpenseCategory.OTHER
    assert normalize_category("TRAVEL") == ExpenseCategory.TRAVEL


def test_map_to_policy_request_food_meals():
    from app.schemas.policy import FoodMealsPolicyEvaluation

    request = map_to_policy_request(
        _food_extraction(),
        context=make_food_audit_context(),
        category_data=map_extraction_to_category_data(
            _food_extraction(),
            category=ExpenseCategory.FOOD_MEALS,
            claimed_category_data=CLAIMED,
        ),
    )

    assert isinstance(request, FoodMealsPolicyEvaluation)
    assert request.category == ExpenseCategory.FOOD_MEALS
    assert request.claim.employee_id == "EMP-001"
    assert request.claim.claim_amount == Decimal("2000.00")
    assert request.category_data.merchant_name == "Zulu Bistro"
    assert request.category_data.line_items == [
        LineItem(item_header="Dinner", item_amount=Decimal("2000.00"))
    ]


def test_map_to_policy_request_uses_extraction_currency():
    extraction = _food_extraction()
    extraction.currency = "USD"
    request = map_to_policy_request(
        extraction,
        context=make_food_audit_context(),
        category_data=map_extraction_to_category_data(
            extraction,
            category=ExpenseCategory.FOOD_MEALS,
            claimed_category_data=CLAIMED,
        ),
    )
    assert request.claim.currency == Currency.USD


def test_map_to_policy_request_category_mismatch_raises():
    extraction = OtherExtraction(is_receipt=True, line_items=[])
    with pytest.raises(MapperError) as exc_info:
        map_to_policy_request(
            extraction,
            context=make_food_audit_context(),
            category_data=None,
        )
    assert exc_info.value.code == "category_mismatch"