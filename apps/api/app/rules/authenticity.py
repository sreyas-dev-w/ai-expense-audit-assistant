"""Heuristic authenticity flags that seed the LLM reason node."""
from decimal import Decimal

from app.rules.helpers import failed, finding, passed
from app.rules.normalize import NormalizedExpense
from app.schemas.validation import (
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def check_authenticity_heuristics(
    expense: NormalizedExpense,
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    if expense.receipt_provided and not expense.is_receipt:
        findings.append(
            finding(
                rule_id="authenticity_not_a_receipt",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.AUTHENTICITY,
                description="Employee marked a receipt as provided but OCR did not classify the file as a receipt.",
            )
        )
        checks.append(failed("Document classified as a receipt", "authenticity_not_a_receipt"))
    else:
        checks.append(passed("Document classified as a receipt", "authenticity_receipt"))

    missing_merchant = not (expense.merchant_extracted or "").strip()
    missing_document = not (expense.document_number or "").strip()
    if expense.is_receipt and missing_merchant and missing_document:
        findings.append(
            finding(
                rule_id="authenticity_missing_identifiers",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.AUTHENTICITY,
                description="Receipt has neither a merchant/hotel name nor a document number.",
            )
        )
        checks.append(failed("Receipt identifiers present", "authenticity_missing_identifiers"))
    else:
        checks.append(passed("Receipt identifiers present", "authenticity_identifiers"))

    if _is_round_amount_without_lines(expense):
        findings.append(
            finding(
                rule_id="authenticity_round_amount",
                severity=ValidationSeverity.INFO,
                category=ValidationFindingCategory.AUTHENTICITY,
                description="Claim uses a round amount with no receipt line items.",
                evidence={
                    "spend_amount": str(expense.spend_amount or ""),
                    "total_amount": str(expense.extracted_total or ""),
                },
            )
        )
        checks.append(failed("Non-round or itemised amount", "authenticity_round_amount"))
    else:
        checks.append(passed("Non-round or itemised amount", "authenticity_amount_shape"))

    return findings, checks


def _is_round_amount_without_lines(expense: NormalizedExpense) -> bool:
    if expense.line_item_amounts:
        return False
    amount = expense.extracted_total or expense.spend_amount
    if amount is None:
        return False
    return amount == amount.to_integral_value() and amount % Decimal("100") == 0
