"""Maps the OCR extraction + claim context into the Validation Agent input.

Input:  ``Extraction`` (OCR output) + ``ClaimAuditContext`` (claim/employee)
Output: ``ValidationRequest`` (``app/schemas/validation.py``) — the contract
the Validation Agent consumes.

Mirrors ``policy_request_mapper``: the canonical category data models from
``app/schemas/expense.py`` are reused (defined once); this mapper only
transforms between stage contracts (``docs/agents/validation-agent.md``).
"""
from datetime import datetime, timezone
from typing import Any

from app.agents.mappers.category_data_mapper import (
    MapperError,
    category_from_extraction,
)
from app.schemas.audit import ClaimAuditContext
from app.schemas.extraction import Extraction
from app.schemas.validation import ValidationRequest


def map_to_validation_request(
    extraction: Extraction,
    *,
    context: ClaimAuditContext,
    category_data: dict[str, Any] | None = None,
) -> ValidationRequest:
    """Build the Validation Agent input from the OCR output + claim context.

    ``category_data`` (the already-mapped canonical payload) may be supplied to
    avoid double mapping when it was persisted earlier in the workflow;
    otherwise the claim's stored ``category_data`` is used.
    """
    if category_from_extraction(extraction) != context.category:
        raise MapperError(
            f"Extraction category does not match the claim category "
            f"({context.category.value})",
            code="category_mismatch",
        )

    return ValidationRequest(
        claim_id=context.claim_id,
        category=context.category.value,
        employee_id=context.employee_id,
        submitted_at=_submitted_at(context),
        claim_amount=context.claim_amount,
        currency=context.currency.value,
        merchant_name=context.merchant_name,
        receipt_provided=context.receipt_url is not None,
        category_data=(
            category_data if category_data is not None else context.category_data
        ),
        extraction=extraction,
    )


def _submitted_at(context: ClaimAuditContext) -> datetime:
    """Claim submission timestamp for rule date math.

    ``ClaimAuditContext`` does not carry ``claim_created_at``, so the audit
    run time is used; the rules only rely on it for date-age comparisons.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)