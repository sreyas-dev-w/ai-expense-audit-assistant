"""Deterministic validation rules invoked by the Validation Agent.

Keep this package free of LLM calls and database sessions. Context snapshots
(budget, duplicate candidates) are loaded by the service layer and passed in.
"""
from app.rules.amounts import check_amounts
from app.rules.authenticity import check_authenticity_heuristics
from app.rules.budget import check_budget
from app.rules.cross_check import check_cross_fields
from app.rules.dates import check_dates
from app.rules.duplicates import check_duplicates, score_duplicate_candidates
from app.rules.normalize import NormalizedExpense, normalize_request
from app.schemas.validation import (
    BudgetSnapshot,
    DuplicateCandidate,
    ValidationCheck,
    ValidationFinding,
    ValidationRequest,
)


def run_all_rules(
    request: ValidationRequest,
    *,
    budget: BudgetSnapshot | None = None,
    duplicates: list[DuplicateCandidate] | None = None,
    context_warnings: list[str] | None = None,
) -> tuple[list[ValidationFinding], list[ValidationCheck], list[str], NormalizedExpense]:
    expense = normalize_request(request)
    findings: list[ValidationFinding] = []
    checks: list[ValidationCheck] = []
    warnings = list(context_warnings or [])
    candidates = list(duplicates or [])

    for runner in (
        lambda: check_amounts(expense),
        lambda: check_dates(expense),
        lambda: check_cross_fields(expense),
        lambda: check_budget(expense, budget, warnings),
        lambda: check_duplicates(expense, candidates),
        lambda: check_authenticity_heuristics(expense),
    ):
        part_findings, part_checks = runner()
        findings.extend(part_findings)
        checks.extend(part_checks)

    for item in findings:
        if item.severity.value == "warning" and item.description not in warnings:
            warnings.append(item.description)

    return findings, checks, warnings, expense


__all__ = [
    "run_all_rules",
    "normalize_request",
    "score_duplicate_candidates",
]
