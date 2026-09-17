"""Date validity, age, and category-specific date math."""
from datetime import date

from app.rules.constants import MAX_CLAIM_AGE_DAYS
from app.rules.helpers import failed, finding, not_applicable, passed
from app.rules.normalize import NormalizedExpense
from app.schemas.validation import (
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def check_dates(
    expense: NormalizedExpense,
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    for raw in expense.date_parse_errors:
        findings.append(
            finding(
                rule_id="date_invalid",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DATE,
                description="Expense date on the receipt is not a valid date.",
                evidence={"invalid_value": raw},
            )
        )
    if expense.date_parse_errors:
        checks.append(failed("Valid expense date", "date_invalid"))
    elif expense.expense_date is None and expense.category != "ACCOMMODATION":
        findings.append(
            finding(
                rule_id="date_missing",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DATE,
                description="Expense date is missing from the receipt extraction.",
            )
        )
        checks.append(failed("Valid expense date", "date_missing"))
    else:
        checks.append(passed("Valid expense date", "date_valid"))

    submitted_day = expense.submitted_at.date()
    if expense.expense_date is not None:
        if expense.expense_date > submitted_day:
            findings.append(
                finding(
                    rule_id="date_in_future",
                    severity=ValidationSeverity.BLOCKING,
                    category=ValidationFindingCategory.DATE,
                    description="Expense date is after the claim submission date.",
                    evidence={
                        "expense_date": expense.expense_date.isoformat(),
                        "submitted_at": submitted_day.isoformat(),
                    },
                )
            )
            checks.append(failed("Expense date not in the future", "date_in_future"))
        else:
            checks.append(passed("Expense date not in the future", "date_not_future"))

        age_days = (submitted_day - expense.expense_date).days
        if age_days > MAX_CLAIM_AGE_DAYS:
            findings.append(
                finding(
                    rule_id="date_too_old",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationFindingCategory.DATE,
                    description=(
                        f"Expense date is more than {MAX_CLAIM_AGE_DAYS} days "
                        "before submission."
                    ),
                    evidence={
                        "expense_date": expense.expense_date.isoformat(),
                        "age_days": str(age_days),
                    },
                )
            )
            checks.append(failed("Expense date within allowed age", "date_too_old"))
        else:
            checks.append(passed("Expense date within allowed age", "date_age"))
    else:
        checks.append(not_applicable("Expense date not in the future", "date_in_future"))
        checks.append(not_applicable("Expense date within allowed age", "date_age"))

    if expense.category == "TRAVEL":
        findings.extend(_travel_route(expense, checks))
    else:
        checks.append(not_applicable("Travel origin differs from destination", "travel_route"))

    if expense.category == "ACCOMMODATION":
        findings.extend(_accommodation_stay(expense, checks))
    else:
        checks.append(not_applicable("Accommodation stay dates", "accommodation_stay"))

    return findings, checks


def _travel_route(
    expense: NormalizedExpense, checks: list[ValidationCheck]
) -> list[ValidationFinding]:
    origin = (expense.origin or "").strip()
    destination = (expense.destination or "").strip()
    if not origin or not destination:
        checks.append(failed("Travel origin differs from destination", "travel_route_missing"))
        return [
            finding(
                rule_id="travel_route_missing",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.FIELD,
                description="Travel origin and destination are required.",
                evidence={"origin": origin, "destination": destination},
            )
        ]
    if origin.casefold() == destination.casefold():
        checks.append(failed("Travel origin differs from destination", "travel_origin_destination"))
        return [
            finding(
                rule_id="travel_origin_destination",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DATE,
                description="Travel origin and destination must be different.",
                evidence={"origin": origin, "destination": destination},
            )
        ]
    checks.append(passed("Travel origin differs from destination", "travel_route"))
    return []


def _accommodation_stay(
    expense: NormalizedExpense, checks: list[ValidationCheck]
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    check_in = expense.check_in
    check_out = expense.check_out
    if check_in is None or check_out is None:
        checks.append(failed("Accommodation stay dates", "accommodation_dates_missing"))
        findings.append(
            finding(
                rule_id="accommodation_dates_missing",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DATE,
                description="Accommodation check-in and check-out dates are required.",
            )
        )
        return findings

    if check_out <= check_in:
        checks.append(failed("Accommodation stay dates", "accommodation_checkout_order"))
        findings.append(
            finding(
                rule_id="accommodation_checkout_order",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.DATE,
                description="Check-out date must be after check-in date.",
                evidence={
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                },
            )
        )
        return findings

    nights = (check_out - check_in).days
    checks.append(passed("Accommodation stay dates", "accommodation_stay"))
    if expense.number_of_days is not None and expense.number_of_days != nights:
        checks.append(failed("Submitted nights vs date range", "accommodation_nights_mismatch"))
        findings.append(
            finding(
                rule_id="accommodation_nights_mismatch",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.MISMATCH,
                description="Submitted number of days does not match check-in/check-out.",
                evidence={
                    "number_of_days": str(expense.number_of_days),
                    "computed_nights": str(nights),
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                },
            )
        )
    else:
        checks.append(passed("Submitted nights vs date range", "accommodation_nights"))

    if (
        expense.submitted_check_in
        and expense.check_in
        and expense.submitted_check_in != expense.check_in
    ) or (
        expense.submitted_check_out
        and expense.check_out
        and expense.submitted_check_out != expense.check_out
    ):
        findings.append(
            finding(
                rule_id="accommodation_date_mismatch",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.MISMATCH,
                description="Submitted stay dates do not match the receipt.",
                evidence={
                    "submitted_check_in": _iso(expense.submitted_check_in),
                    "extracted_check_in": _iso(expense.check_in),
                    "submitted_check_out": _iso(expense.submitted_check_out),
                    "extracted_check_out": _iso(expense.check_out),
                },
            )
        )
        checks.append(failed("Submitted vs receipt stay dates", "accommodation_date_mismatch"))
    else:
        checks.append(passed("Submitted vs receipt stay dates", "accommodation_date_match"))
    return findings


def _iso(value: date | None) -> str:
    return value.isoformat() if value else ""
