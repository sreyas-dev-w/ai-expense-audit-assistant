"""Cross-checks between the employee submission and receipt extraction."""
from app.rules.helpers import failed, finding, normalize_name, not_applicable, passed
from app.rules.normalize import NormalizedExpense
from app.schemas.validation import (
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def check_cross_fields(
    expense: NormalizedExpense,
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    if expense.receipt_provided != expense.is_receipt:
        findings.append(
            finding(
                rule_id="receipt_presence_mismatch",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.MISMATCH,
                description="Receipt-provided flag does not match OCR is_receipt.",
                evidence={
                    "receipt_provided": str(expense.receipt_provided),
                    "is_receipt": str(expense.is_receipt),
                },
            )
        )
        checks.append(failed("Receipt presence consistency", "receipt_presence_mismatch"))
    else:
        checks.append(passed("Receipt presence consistency", "receipt_presence"))

    submitted_id = (expense.employee_id_submission or "").strip()
    context_id = (expense.employee_id_context or "").strip()
    if context_id and submitted_id != context_id:
        findings.append(
            finding(
                rule_id="employee_id_mismatch",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.MISMATCH,
                description="Submission employee_id does not match employee context.",
                evidence={
                    "submission_employee_id": submitted_id,
                    "context_employee_id": context_id,
                },
            )
        )
        checks.append(failed("Employee id consistency", "employee_id_mismatch"))
    else:
        checks.append(passed("Employee id consistency", "employee_id"))

    extracted_name = normalize_name(expense.merchant_extracted)
    submitted_name = normalize_name(expense.merchant_submitted)
    if extracted_name and submitted_name and extracted_name != submitted_name:
        findings.append(
            finding(
                rule_id="merchant_mismatch",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.MISMATCH,
                description="Submitted merchant/location does not match the receipt.",
                evidence={
                    "submitted": expense.merchant_submitted or "",
                    "extracted": expense.merchant_extracted or "",
                },
            )
        )
        checks.append(failed("Merchant / location match", "merchant_mismatch"))
    elif extracted_name or submitted_name:
        checks.append(passed("Merchant / location match", "merchant_match"))
    else:
        checks.append(not_applicable("Merchant / location match", "merchant"))

    needs_document = expense.receipt_provided or expense.is_receipt
    if needs_document and not (expense.document_number or "").strip():
        findings.append(
            finding(
                rule_id="document_number_missing",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.FIELD,
                description="Receipt is present but invoice/ticket/booking number is missing.",
            )
        )
        checks.append(failed("Document number present", "document_number_missing"))
    elif needs_document:
        checks.append(passed("Document number present", "document_number"))
    else:
        checks.append(not_applicable("Document number present", "document_number"))

    status = (expense.payment_status or "").strip().upper()
    if status and status not in {"PAID", "SUCCESS", "COMPLETED", "SETTLED"}:
        findings.append(
            finding(
                rule_id="payment_status_not_paid",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.FIELD,
                description="Receipt payment status is not PAID.",
                evidence={"payment_status": expense.payment_status or ""},
            )
        )
        checks.append(failed("Payment status PAID", "payment_status_not_paid"))
    elif status:
        checks.append(passed("Payment status PAID", "payment_status"))
    else:
        checks.append(not_applicable("Payment status PAID", "payment_status"))

    return findings, checks
