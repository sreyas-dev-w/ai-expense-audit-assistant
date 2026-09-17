"""Maps the OCR extraction + claim context into the Policy RAG Agent input.

Input:  ``Extraction`` (OCR output) + ``ClaimAuditContext`` (claim/employee)
Output: ``PolicyEvaluationRequest`` (``app/schemas/policy.py``) — the
discriminated union the Policy RAG Agent consumes.

The canonical category data models from ``app/schemas/expense.py`` are reused
(defined once); this mapper only transforms between stage contracts.
"""
from decimal import Decimal
from typing import Any

from app.agents.mappers.category_data_mapper import (
    MapperError,
    category_from_extraction,
    map_extraction_to_category_data,
    parse_date,
)
from app.models.enums import Currency, ExpenseCategory
from app.schemas.audit import ClaimAuditContext
from app.schemas.extraction import Extraction
from app.schemas.policy import (
    AccommodationPolicyEvaluation,
    FoodMealsPolicyEvaluation,
    OtherPolicyEvaluation,
    PolicyClaimContext,
    PolicyEvaluationRequest,
    TravelPolicyEvaluation,
)

_EVALUATORS = {
    ExpenseCategory.FOOD_MEALS: FoodMealsPolicyEvaluation,
    ExpenseCategory.TRAVEL: TravelPolicyEvaluation,
    ExpenseCategory.ACCOMMODATION: AccommodationPolicyEvaluation,
    ExpenseCategory.OTHER: OtherPolicyEvaluation,
}


def map_to_policy_request(
    extraction: Extraction,
    *,
    context: ClaimAuditContext,
    category_data: dict[str, Any] | None = None,
) -> PolicyEvaluationRequest:
    """Build the Policy RAG Agent request from the OCR output + claim context.

    ``category_data`` (the already-mapped canonical payload) may be supplied to
    avoid double mapping when it was persisted earlier in the workflow;
    otherwise it is derived here.
    """
    if category_from_extraction(extraction) != context.category:
        raise MapperError(
            f"Extraction category does not match the claim category "
            f"({context.category.value})",
            code="category_mismatch",
        )

    merged = (
        category_data
        if category_data is not None
        else map_extraction_to_category_data(
            extraction,
            category=context.category,
            claimed_category_data=context.category_data,
        )
    )

    claim_context = PolicyClaimContext(
        claim_id=context.claim_id,
        employee_id=context.employee_id,
        employee_job_level=context.employee_job_level,
        business_purpose=context.business_purpose,
        merchant_name=_merchant_name(extraction, context),
        project_code=context.project_code,
        claim_amount=(
            Decimal(str(extraction.claim_amount))
            if getattr(extraction, "claim_amount", None) is not None
            else context.claim_amount
        ),
        currency=_currency(extraction, context),
        expense_date=_expense_date(extraction),
    )

    evaluator = _EVALUATORS[context.category]
    return evaluator(
        category=context.category,
        claim=claim_context,
        category_data=merged,
    )


def _merchant_name(extraction: Extraction, context: ClaimAuditContext) -> str | None:
    if getattr(extraction, "merchant_name", None):
        return extraction.merchant_name
    if context.category == ExpenseCategory.ACCOMMODATION and context.merchant_name is None:
        hotel = context.category_data.get("hotel_name")
        if hotel:
            return hotel
    return context.merchant_name


def _currency(extraction: Extraction, context: ClaimAuditContext) -> Currency:
    value = getattr(extraction, "currency", None)
    if value:
        try:
            return Currency(value)
        except ValueError:
            pass
    return context.currency


def _expense_date(extraction: Extraction) -> Any:
    value = getattr(extraction, "expense_date", None)
    if not value:
        return None
    return parse_date(value)