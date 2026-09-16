"""Unit tests for deterministic validation rules."""
from datetime import datetime, timezone
from decimal import Decimal

from app.rules import run_all_rules
from app.rules.duplicates import score_duplicate_candidates
from app.rules.normalize import normalize_request
from app.schemas.validation import (
    BudgetSnapshot,
    ValidationFindingCategory,
    ValidationRequest,
    ValidationSeverity,
)


def travel_payload(**overrides) -> dict:
    payload = {
        "submission": {
            "employee_id": "EMP-003",
            "expense_category": "TRAVEL",
            "details": {
                "expense_category": "TRAVEL",
                "spend_amount": 40000,
                "travel_type": "FLIGHT",
                "origin": "Trivandrum",
                "destination": "Kochi",
                "travel_class": "BUSINESS_CLASS",
                "business_purpose": "Client entertainment",
            },
            "submitted_at": "2026-09-15T20:11:53.388364Z",
            "receipt_provided": True,
        },
        "employee_context": {
            "employee_id": "EMP-003",
            "found": True,
            "employee_name": "Arun Kumar",
            "job_level": "L3",
            "manager_id": "EMP-001",
            "project_code": "CAPSTONE-001",
            "account_id": "ACC-001",
        },
        "extraction": {
            "is_receipt": True,
            "merchant_name": "Air India",
            "ticket_number": "TRAVEL-0003",
            "travel_date": "2026-08-19",
            "currency": "INR",
            "total_amount": 51212.55,
            "payment_status": "PAID",
            "line_items": [
                {
                    "description": "Flight Ticket",
                    "amount": 43400.46,
                    "receipt_present": True,
                }
            ],
        },
    }
    payload.update(overrides)
    return payload


def travel_request(**overrides) -> ValidationRequest:
    return ValidationRequest.model_validate(travel_payload(**overrides))


def _rule_ids(findings) -> set[str]:
    return {item.rule_id for item in findings}


def test_parses_travel_ocr_sample_as_travel_extraction():
    request = travel_request()
    assert request.submission.expense_category == "TRAVEL"
    assert request.extraction.ticket_number == "TRAVEL-0003"
    assert request.extraction.total_amount == 51212.55


def test_travel_sample_amount_mismatch_is_blocking():
    findings, checks, _warnings, _expense = run_all_rules(
        travel_request(),
        budget=BudgetSnapshot(
            account_id="ACC-001",
            remaining_budget=Decimal("100000.00"),
            claim_amount=Decimal("51212.55"),
            currency="INR",
            within_budget=True,
        ),
    )
    assert "amount_mismatch" in _rule_ids(findings)
    mismatch = next(item for item in findings if item.rule_id == "amount_mismatch")
    assert mismatch.severity == ValidationSeverity.BLOCKING
    assert mismatch.category == ValidationFindingCategory.MISMATCH
    assert any(item.rule_id == "line_item_total_mismatch" for item in findings)


def test_negative_claimed_amount_is_blocking():
    payload = travel_payload()
    payload["submission"]["details"]["spend_amount"] = -10
    payload["extraction"]["total_amount"] = 100
    payload["extraction"]["line_items"] = []
    findings, _checks, _warnings, _expense = run_all_rules(
        ValidationRequest.model_validate(payload)
    )
    assert "amount_claimed_not_positive" in _rule_ids(findings)


def test_future_expense_date_is_blocking():
    payload = travel_payload()
    payload["extraction"]["travel_date"] = "2026-12-01"
    findings, _checks, _warnings, _expense = run_all_rules(
        ValidationRequest.model_validate(payload)
    )
    assert "date_in_future" in _rule_ids(findings)


def test_origin_equals_destination_is_blocking():
    payload = travel_payload()
    payload["submission"]["details"]["destination"] = "Trivandrum"
    findings, _checks, _warnings, _expense = run_all_rules(
        ValidationRequest.model_validate(payload)
    )
    assert "travel_origin_destination" in _rule_ids(findings)


def test_accommodation_nights_mismatch_is_blocking():
    request = ValidationRequest.model_validate(
        {
            "submission": {
                "employee_id": "EMP-003",
                "expense_category": "ACCOMMODATION",
                "details": {
                    "expense_category": "ACCOMMODATION",
                    "spend_amount": 8000,
                    "location": "Kochi",
                    "check_in_date": "2026-08-19",
                    "check_out_date": "2026-08-21",
                    "number_of_days": 5,
                    "room_type": "Deluxe",
                },
                "submitted_at": "2026-09-15T20:11:53.388364Z",
                "receipt_provided": True,
            },
            "employee_context": {
                "employee_id": "EMP-003",
                "found": True,
                "account_id": "ACC-001",
            },
            "extraction": {
                "is_receipt": True,
                "hotel_name": "Harbour Hotel",
                "booking_number": "HTL-1",
                "check_in_date": "2026-08-19",
                "check_out_date": "2026-08-21",
                "currency": "INR",
                "total_amount": 8000,
                "payment_status": "PAID",
                "line_items": [],
            },
        }
    )
    findings, _checks, _warnings, _expense = run_all_rules(request)
    assert "accommodation_nights_mismatch" in _rule_ids(findings)


def test_budget_overrun_is_blocking():
    findings, _checks, _warnings, _expense = run_all_rules(
        travel_request(),
        budget=BudgetSnapshot(
            account_id="ACC-001",
            remaining_budget=Decimal("100.00"),
            claim_amount=Decimal("51212.55"),
            currency="INR",
            within_budget=False,
        ),
    )
    assert "budget_exceeded" in _rule_ids(findings)


def test_duplicate_ticket_number_is_blocking():
    request = travel_request()
    expense = normalize_request(request)
    candidates = score_duplicate_candidates(
        expense=expense,
        prior_claims=[
            {
                "claim_id": 5,
                "merchant_name": "Air India",
                "claim_amount": Decimal("51212.55"),
                "category_data": {"ticket_number": "TRAVEL-0003"},
                "claim_created_at": datetime(2026, 8, 20, tzinfo=timezone.utc),
            }
        ],
    )
    assert candidates
    assert candidates[0].score == 1.0
    findings, _checks, _warnings, _expense = run_all_rules(
        request, duplicates=candidates
    )
    assert "duplicate_invoice" in _rule_ids(findings)
