"""Helpers shared by deterministic validation rules."""
from decimal import Decimal, InvalidOperation

from app.schemas.validation import (
    ValidationCheck,
    ValidationCheckStatus,
    ValidationFinding,
    ValidationFindingCategory,
    ValidationSeverity,
)


def to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")


def finding(
    *,
    rule_id: str,
    severity: ValidationSeverity,
    category: ValidationFindingCategory,
    description: str,
    detail: str | None = None,
    evidence: dict[str, str] | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=severity,
        category=category,
        description=description,
        detail=detail,
        evidence=evidence or {},
    )


def check(
    *,
    name: str,
    status: ValidationCheckStatus,
    rule_id: str | None = None,
) -> ValidationCheck:
    return ValidationCheck(check_name=name, status=status, rule_id=rule_id)


def passed(name: str, rule_id: str) -> ValidationCheck:
    return check(name=name, status=ValidationCheckStatus.PASSED, rule_id=rule_id)


def failed(name: str, rule_id: str) -> ValidationCheck:
    return check(name=name, status=ValidationCheckStatus.FAILED, rule_id=rule_id)


def not_applicable(name: str, rule_id: str) -> ValidationCheck:
    return check(
        name=name, status=ValidationCheckStatus.NOT_APPLICABLE, rule_id=rule_id
    )


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.casefold().split())
