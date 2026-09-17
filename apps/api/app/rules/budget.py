"""Account remaining-budget check (not a policy limit)."""
from app.rules.helpers import failed, finding, format_decimal, not_applicable, passed
from app.rules.normalize import NormalizedExpense, claim_amount
from app.schemas.validation import (
    BudgetSnapshot,
    ValidationCheck,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def check_budget(
    expense: NormalizedExpense,
    budget: BudgetSnapshot | None,
    context_warnings: list[str],
) -> tuple[list[ValidationFinding], list[ValidationCheck]]:
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []

    if budget is None:
        findings.append(
            finding(
                rule_id="budget_check_skipped",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.BUDGET,
                description="Remaining budget could not be checked for this claim.",
                detail="; ".join(context_warnings)
                or "No account budget snapshot was loaded.",
                evidence={"account_id": expense.account_id or ""},
            )
        )
        checks.append(
            not_applicable("Claim within remaining budget", "budget_check_skipped")
        )
        return findings, checks

    amount = claim_amount(expense)
    if amount is None:
        checks.append(not_applicable("Claim within remaining budget", "budget_amount_missing"))
        return findings, checks

    if not budget.within_budget:
        findings.append(
            finding(
                rule_id="budget_exceeded",
                severity=ValidationSeverity.BLOCKING,
                category=ValidationFindingCategory.BUDGET,
                description="Claim amount exceeds the account remaining budget.",
                evidence={
                    "claim_amount": format_decimal(amount),
                    "remaining_budget": format_decimal(budget.remaining_budget),
                    "account_id": budget.account_id,
                },
            )
        )
        checks.append(failed("Claim within remaining budget", "budget_exceeded"))
    else:
        checks.append(passed("Claim within remaining budget", "budget_ok"))

    if (
        budget.currency
        and expense.currency
        and budget.currency.upper() != expense.currency.upper()
    ):
        findings.append(
            finding(
                rule_id="budget_currency_mismatch",
                severity=ValidationSeverity.WARNING,
                category=ValidationFindingCategory.BUDGET,
                description="Account currency does not match the receipt currency.",
                evidence={
                    "account_currency": budget.currency,
                    "receipt_currency": expense.currency,
                },
            )
        )
        checks.append(failed("Budget currency match", "budget_currency_mismatch"))
    else:
        checks.append(passed("Budget currency match", "budget_currency"))

    return findings, checks
