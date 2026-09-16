"""Amount, total, and currency checks."""
from decimal import Decimal

from app.models.enums import Currency
from app.rules.constants import AMOUNT_TOLERANCE
from app.rules.helpers import failed, finding, format_decimal, not_applicable, passed
from app.rules.normalize import NormalizedExpense
from app.schemas.validation import (
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def check_amounts(
    expense: NormalizedExpense,
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    spend = expense.spend_amount
    extracted = expense.extracted_total

    if spend is None:
        findings.append(
            finding(
                rule_id="amount_claimed_missing",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.AMOUNT,
                description="Claimed spend amount is missing or not a valid number.",
            )
        )
        checks.append(failed("Claimed amount present and positive", "amount_claimed_missing"))
    elif spend <= 0:
        findings.append(
            finding(
                rule_id="amount_claimed_not_positive",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.AMOUNT,
                description="Claimed spend amount must be greater than zero.",
                evidence={"spend_amount": format_decimal(spend)},
            )
        )
        checks.append(failed("Claimed amount present and positive", "amount_claimed_not_positive"))
    else:
        checks.append(passed("Claimed amount present and positive", "amount_claimed_positive"))

    if extracted is None:
        findings.append(
            finding(
                rule_id="amount_extracted_missing",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.AMOUNT,
                description="Receipt total amount is missing or not a valid number.",
            )
        )
        checks.append(failed("Extracted amount present and positive", "amount_extracted_missing"))
    elif extracted <= 0:
        findings.append(
            finding(
                rule_id="amount_extracted_not_positive",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.AMOUNT,
                description="Receipt total amount must be greater than zero.",
                evidence={"total_amount": format_decimal(extracted)},
            )
        )
        checks.append(failed("Extracted amount present and positive", "amount_extracted_not_positive"))
    else:
        checks.append(passed("Extracted amount present and positive", "amount_extracted_positive"))

    if spend is not None and extracted is not None:
        delta = abs(spend - extracted)
        if delta > AMOUNT_TOLERANCE:
            findings.append(
                finding(
                    rule_id="amount_mismatch",
                    severity=ValidationSeverity.BLOCKING,
                    category=ValidationFindingCategory.MISMATCH,
                    description="Claimed spend amount does not match the receipt total.",
                    detail=(
                        f"Difference of {format_decimal(delta)} exceeds "
                        f"tolerance {format_decimal(AMOUNT_TOLERANCE)}."
                    ),
                    evidence={
                        "spend_amount": format_decimal(spend),
                        "total_amount": format_decimal(extracted),
                    },
                )
            )
            checks.append(failed("Claimed vs receipt amount", "amount_mismatch"))
        else:
            checks.append(passed("Claimed vs receipt amount", "amount_match"))

    if extracted is not None and expense.line_item_amounts:
        line_sum = sum(expense.line_item_amounts, Decimal("0"))
        if abs(line_sum - extracted) > AMOUNT_TOLERANCE:
            findings.append(
                finding(
                    rule_id="line_item_total_mismatch",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationFindingCategory.AMOUNT,
                    description="Sum of receipt line items does not match the receipt total.",
                    evidence={
                        "line_item_sum": format_decimal(line_sum),
                        "total_amount": format_decimal(extracted),
                    },
                )
            )
            checks.append(failed("Line items vs receipt total", "line_item_total_mismatch"))
        else:
            checks.append(passed("Line items vs receipt total", "line_item_total_match"))
    else:
        checks.append(not_applicable("Line items vs receipt total", "line_item_total"))

    if expense.currency:
        known = {item.value for item in Currency}
        if expense.currency.upper() not in known:
            findings.append(
                finding(
                    rule_id="currency_unknown",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationFindingCategory.FIELD,
                    description="Receipt currency is not a recognised currency code.",
                    evidence={"currency": expense.currency},
                )
            )
            checks.append(failed("Recognised currency", "currency_unknown"))
        else:
            checks.append(passed("Recognised currency", "currency_known"))
    else:
        checks.append(not_applicable("Recognised currency", "currency"))

    return findings, checks
