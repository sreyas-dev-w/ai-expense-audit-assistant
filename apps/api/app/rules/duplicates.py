"""Exact and fuzzy duplicate scoring against prior claims."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.rules.constants import (
    DUPLICATE_AMOUNT_TOLERANCE,
    DUPLICATE_DATE_WINDOW_DAYS,
    DUPLICATE_SCORE_THRESHOLD,
    EXACT_DUPLICATE_SCORE,
)
from app.rules.helpers import failed, finding, normalize_name, not_applicable, passed
from app.rules.normalize import NormalizedExpense, claim_amount
from app.schemas.validation import (
    DuplicateCandidate,
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)

_DOCUMENT_KEYS = (
    "ticket_number",
    "bill_number",
    "booking_number",
    "receipt_number",
)


def score_duplicate_candidates(
    *,
    expense: NormalizedExpense,
    prior_claims: list[dict[str, Any]],
) -> list[DuplicateCandidate]:
    amount = claim_amount(expense)
    document = (expense.document_number or "").strip()
    merchant = normalize_name(expense.merchant_extracted or expense.merchant_submitted)
    candidates: list[DuplicateCandidate] = []

    for row in prior_claims:
        reasons: list[str] = []
        score = 0.0
        category_data = row.get("category_data") or {}
        prior_document = _document_from_category_data(category_data)
        if document and prior_document and document.casefold() == prior_document.casefold():
            return_or_add = DuplicateCandidate(
                claim_id=int(row["claim_id"]),
                score=EXACT_DUPLICATE_SCORE,
                match_reasons=["invoice_number"],
            )
            candidates.append(return_or_add)
            continue

        prior_merchant = normalize_name(row.get("merchant_name"))
        if merchant and prior_merchant and merchant == prior_merchant:
            score += 0.4
            reasons.append("merchant")

        prior_amount = row.get("claim_amount")
        if amount is not None and prior_amount is not None:
            try:
                prior_dec = prior_amount if isinstance(prior_amount, Decimal) else Decimal(str(prior_amount))
            except Exception:
                prior_dec = None
            if prior_dec is not None and abs(amount - prior_dec) <= DUPLICATE_AMOUNT_TOLERANCE:
                score += 0.4
                reasons.append("amount")

        prior_date = _expense_date_from_row(row)
        if expense.expense_date and prior_date:
            window = timedelta(days=DUPLICATE_DATE_WINDOW_DAYS)
            if abs((expense.expense_date - prior_date).days) <= window.days:
                score += 0.2
                reasons.append("date")

        if score >= DUPLICATE_SCORE_THRESHOLD and reasons:
            candidates.append(
                DuplicateCandidate(
                    claim_id=int(row["claim_id"]),
                    score=round(min(score, 1.0), 2),
                    match_reasons=reasons,
                )
            )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def check_duplicates(
    expense: NormalizedExpense,
    candidates: list[DuplicateCandidate],
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    if not candidates:
        checks.append(passed("No duplicate claims", "duplicates_none"))
        return findings, checks

    exact = [item for item in candidates if "invoice_number" in item.match_reasons]
    if exact:
        findings.append(
            finding(
                rule_id="duplicate_invoice",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DUPLICATE,
                description="A prior claim uses the same invoice/ticket/booking number.",
                evidence={
                    "document_number": expense.document_number or "",
                    "claim_ids": ",".join(str(item.claim_id) for item in exact),
                },
            )
        )
        checks.append(failed("No duplicate invoice number", "duplicate_invoice"))
    else:
        checks.append(passed("No duplicate invoice number", "duplicate_invoice"))

    fuzzy = [item for item in candidates if "invoice_number" not in item.match_reasons]
    if fuzzy:
        findings.append(
            finding(
                rule_id="duplicate_fuzzy",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.DUPLICATE,
                description="Possible duplicate claim(s) based on merchant, amount, and date.",
                evidence={
                    "claim_ids": ",".join(str(item.claim_id) for item in fuzzy),
                },
            )
        )
        checks.append(failed("No similar prior claims", "duplicate_fuzzy"))
    else:
        checks.append(not_applicable("No similar prior claims", "duplicate_fuzzy"))

    return findings, checks


def _document_from_category_data(category_data: dict[str, Any]) -> str:
    for key in _DOCUMENT_KEYS:
        value = category_data.get(key)
        if value:
            return str(value).strip()
    return ""


def _expense_date_from_row(row: dict[str, Any]) -> date | None:
    category_data = row.get("category_data") or {}
    for key in ("travel_date", "meal_date", "check_in", "expense_date"):
        value = category_data.get(key)
        if not value:
            continue
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            continue
    created = row.get("claim_created_at")
    if isinstance(created, datetime):
        return created.date()
    if isinstance(created, date):
        return created
    return None
