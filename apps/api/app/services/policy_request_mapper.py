"""Build a Policy RAG input from an OCR envelope.

Policy RAG does not consume validation findings. This mapper is the typed
handoff the Audit Agent (or a client) uses after OCR / validation.
"""
from datetime import date
from decimal import Decimal

from app.models.enums import Currency, ExpenseCategory, JobLevel
from app.rules.helpers import to_decimal
from app.rules.normalize import parse_date
from app.schemas.expense import (
    AccommodationData,
    FoodMealsData,
    OtherData,
    TravelData,
)
from app.schemas.extraction import (
    AccommodationDetails,
    AccommodationExtraction,
    FoodMealsDetails,
    OCRResponse,
    OtherDetails,
    OtherExtraction,
    TravelDetails,
    TravelExtraction,
)
from app.schemas.policy import (
    AccommodationPolicyEvaluation,
    FoodMealsPolicyEvaluation,
    OtherPolicyEvaluation,
    PolicyClaimContext,
    PolicyEvaluationRequest,
    TravelPolicyEvaluation,
)


class PolicyRequestMappingError(Exception):
    def __init__(self, message: str, *, code: str = "policy_request_mapping_error"):
        super().__init__(message)
        self.code = code


def to_policy_evaluation_request(
    ocr: OCRResponse,
    *,
    claim_id: int | None = None,
) -> PolicyEvaluationRequest:
    details = ocr.submission.details
    extraction = ocr.extraction
    category = ocr.submission.expense_category
    amount = _claim_amount(details, extraction)
    merchant = _merchant_name(extraction)
    expense_date = _expense_date(ocr) or ocr.submission.submitted_at.date()
    job_level = _job_level(ocr.employee_context.job_level)
    currency = _currency(getattr(extraction, "currency", None))

    claim = PolicyClaimContext(
        claim_id=claim_id,
        employee_id=ocr.submission.employee_id,
        employee_job_level=job_level,
        business_purpose=getattr(details, "business_purpose", None),
        merchant_name=merchant,
        project_code=ocr.employee_context.project_code,
        claim_amount=amount,
        currency=currency,
        expense_date=expense_date,
    )

    if category == "FOOD_MEALS" and isinstance(details, FoodMealsDetails):
        return FoodMealsPolicyEvaluation(
            category=ExpenseCategory.FOOD_MEALS,
            claim=claim,
            category_data=FoodMealsData(
                meal_type=details.meal_type,
                merchant_name=merchant or "Unknown merchant",
                number_of_people=details.number_of_people,
            ),
        )

    if category == "TRAVEL" and isinstance(details, TravelDetails):
        travel = extraction if isinstance(extraction, TravelExtraction) else None
        travel_date, _ = parse_date(travel.travel_date if travel else None)
        return TravelPolicyEvaluation(
            category=ExpenseCategory.TRAVEL,
            claim=claim,
            category_data=TravelData(
                travel_type=details.travel_type,
                origin=details.origin,
                destination=details.destination,
                travel_date=travel_date or expense_date,
                travel_class=details.travel_class,
                ticket_number=travel.ticket_number if travel else None,
            ),
        )

    if category == "ACCOMMODATION" and isinstance(details, AccommodationDetails):
        stay = extraction if isinstance(extraction, AccommodationExtraction) else None
        check_in, _ = parse_date(stay.check_in_date if stay else None)
        check_out, _ = parse_date(stay.check_out_date if stay else None)
        check_in = check_in or details.check_in_date
        check_out = check_out or details.check_out_date
        nights = details.number_of_days
        if check_out > check_in:
            nights = max(nights, (check_out - check_in).days)
        nights = max(nights, 1)
        return AccommodationPolicyEvaluation(
            category=ExpenseCategory.ACCOMMODATION,
            claim=claim,
            category_data=AccommodationData(
                hotel_name=(stay.hotel_name if stay and stay.hotel_name else None)
                or "Unknown hotel",
                location=details.location,
                check_in=check_in,
                check_out=check_out if check_out > check_in else date.fromordinal(
                    check_in.toordinal() + nights
                ),
                number_of_nights=nights,
                no_of_rooms=1,
                room_type=details.room_type,
            ),
        )

    if category in {"OTHERS", "OTHER"} and isinstance(details, OtherDetails):
        other = extraction if isinstance(extraction, OtherExtraction) else None
        additional = None
        if details.additional_details:
            additional = {"details": details.additional_details}
        return OtherPolicyEvaluation(
            category=ExpenseCategory.OTHER,
            claim=claim,
            category_data=OtherData(
                expense_type=details.expense_type,
                merchant_name=other.merchant_name if other else merchant,
                additional_details=additional,
            ),
        )

    raise PolicyRequestMappingError(
        f"Cannot map OCR category {category!r} to a policy evaluation request"
    )


def _claim_amount(details, extraction) -> Decimal:
    extracted = to_decimal(getattr(extraction, "total_amount", None))
    if extracted is not None:
        return extracted
    spend = to_decimal(getattr(details, "spend_amount", None))
    return spend if spend is not None else Decimal("0.00")


def _merchant_name(extraction) -> str | None:
    return getattr(extraction, "merchant_name", None) or getattr(
        extraction, "hotel_name", None
    )


def _expense_date(ocr: OCRResponse) -> date | None:
    extraction = ocr.extraction
    for attr in (
        "travel_date",
        "meal_date",
        "check_in_date",
        "expense_date",
    ):
        parsed, _ = parse_date(getattr(extraction, attr, None))
        if parsed is not None:
            return parsed
    details = ocr.submission.details
    if isinstance(details, AccommodationDetails):
        return details.check_in_date
    return None


def _job_level(value: str | None) -> JobLevel | None:
    if not value:
        return None
    try:
        return JobLevel(value)
    except ValueError:
        return None


def _currency(value: str | None) -> Currency:
    if not value:
        return Currency.INR
    try:
        return Currency(value.upper())
    except ValueError:
        return Currency.INR
