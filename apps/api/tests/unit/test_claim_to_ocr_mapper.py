"""Tests for claim → OCR Agent kwarg mapping."""
from decimal import Decimal
from datetime import date

from app.models.enums import ClaimPriority, ClaimStatus, Currency, ExpenseCategory
from app.schemas.audit import (
    AuditContext,
    ClaimSnapshot,
    EmployeeSnapshot,
    ProjectSnapshot,
)
from app.services.claim_to_ocr_mapper import claim_to_ocr_kwargs, ocr_expense_category


def _employee() -> EmployeeSnapshot:
    return EmployeeSnapshot(
        employee_id="EMP-009",
        employee_name="Test User",
        job_level="L2",
        is_manager=False,
        manager_id="EMP-001",
        project_code="P-1",
    )


def test_other_category_maps_to_ocr_others():
    assert ocr_expense_category(ExpenseCategory.OTHER) == "OTHERS"
    assert ocr_expense_category(ExpenseCategory.TRAVEL) == "TRAVEL"


def test_food_meals_kwargs():
    context = AuditContext(
        claim=ClaimSnapshot(
            claim_id=1,
            employee_id="EMP-009",
            business_purpose="Team lunch",
            category=ExpenseCategory.FOOD_MEALS,
            category_data={
                "meal_type": "VEG",
                "merchant_name": "Cafe",
                "number_of_people": 3,
            },
            claim_amount=Decimal("1500.00"),
            currency=Currency.INR,
            status=ClaimStatus.SUBMITTED,
            priority=ClaimPriority.MEDIUM,
        ),
        employee=_employee(),
        project=ProjectSnapshot(
            project_code="P-1",
            project_name="Project",
            account_id="ACC-001",
        ),
    )
    kwargs = claim_to_ocr_kwargs(context)
    assert kwargs["expense_category"] == "FOOD_MEALS"
    assert kwargs["meal_type"] == "VEG"
    assert kwargs["number_of_people"] == 3
    assert kwargs["spend_amount"] == 1500.0
    assert kwargs["employee"]["employee_id"] == "EMP-009"
    assert kwargs["project"]["account_id"] == "ACC-001"


def test_other_kwargs_stringify_additional_details():
    context = AuditContext(
        claim=ClaimSnapshot(
            claim_id=2,
            employee_id="EMP-009",
            category=ExpenseCategory.OTHER,
            category_data={
                "expense_type": "Software",
                "merchant_name": "Vendor",
                "additional_details": {"sku": "ABC"},
            },
            claim_amount=Decimal("99.00"),
            currency=Currency.INR,
            status=ClaimStatus.DRAFT,
        ),
        employee=_employee(),
    )
    kwargs = claim_to_ocr_kwargs(context)
    assert kwargs["expense_category"] == "OTHERS"
    assert kwargs["expense_type"] == "Software"
    assert '"sku"' in kwargs["additional_details"]


def test_accommodation_maps_check_in_and_nights():
    context = AuditContext(
        claim=ClaimSnapshot(
            claim_id=4,
            employee_id="EMP-009",
            category=ExpenseCategory.ACCOMMODATION,
            category_data={
                "hotel_name": "Hilton",
                "location": "Bengaluru",
                "check_in": "2026-03-01",
                "check_out": "2026-03-03",
                "number_of_nights": 2,
                "no_of_rooms": 1,
                "room_type": "Deluxe",
            },
            claim_amount=Decimal("8000.00"),
            currency=Currency.INR,
            status=ClaimStatus.SUBMITTED,
        ),
        employee=_employee(),
    )
    kwargs = claim_to_ocr_kwargs(context)
    assert kwargs["location"] == "Bengaluru"
    assert kwargs["check_in_date"] == date(2026, 3, 1)
    assert kwargs["check_out_date"] == date(2026, 3, 3)
    assert kwargs["number_of_days"] == 2
    assert kwargs["room_type"] == "Deluxe"
