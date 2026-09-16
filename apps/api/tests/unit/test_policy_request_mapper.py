"""Tests for OCR → PolicyEvaluationRequest mapping."""
from datetime import date
from decimal import Decimal

from app.models.enums import ExpenseCategory
from app.schemas.policy import TravelPolicyEvaluation
from app.schemas.validation import ValidationRequest
from app.services.policy_request_mapper import to_policy_evaluation_request
from tests.unit.test_validation_rules import travel_payload


def test_travel_sample_maps_to_policy_travel_request():
    ocr = ValidationRequest.model_validate(travel_payload())
    request = to_policy_evaluation_request(ocr, claim_id=42)
    assert isinstance(request, TravelPolicyEvaluation)
    assert request.category == ExpenseCategory.TRAVEL
    assert request.claim.claim_id == 42
    assert request.claim.claim_amount == Decimal("51212.55")
    assert request.claim.merchant_name == "Air India"
    assert request.claim.expense_date == date(2026, 8, 19)
    assert request.category_data.origin == "Trivandrum"
    assert request.category_data.destination == "Kochi"
    assert request.category_data.travel_date == date(2026, 8, 19)
    assert request.category_data.ticket_number == "TRAVEL-0003"


def test_others_maps_to_policy_other_category():
    ocr = ValidationRequest.model_validate(
        {
            "submission": {
                "employee_id": "EMP-003",
                "expense_category": "OTHERS",
                "details": {
                    "expense_category": "OTHERS",
                    "spend_amount": 500,
                    "expense_type": "Stationery",
                    "additional_details": "Pens",
                },
                "submitted_at": "2026-09-15T20:11:53.388364Z",
                "receipt_provided": True,
            },
            "employee_context": {
                "employee_id": "EMP-003",
                "found": True,
                "job_level": "L3",
            },
            "extraction": {
                "is_receipt": True,
                "merchant_name": "Office Mart",
                "receipt_number": "R-1",
                "expense_date": "2026-09-01",
                "currency": "INR",
                "total_amount": 500,
                "payment_status": "PAID",
                "line_items": [],
            },
        }
    )
    request = to_policy_evaluation_request(ocr)
    assert request.category == ExpenseCategory.OTHER
    assert request.category_data.expense_type == "Stationery"
    assert request.claim.claim_amount == Decimal("500")
    assert request.claim.merchant_name == "Office Mart"
