"""Narrow Audit Agent tools: load context and persist stage outputs.

Each method opens a short-lived session and commits after the write. The
agent graph never holds a SQLAlchemy session (see ``docs/agents/agent-tools.md``).
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from app.db.session import async_session_factory
from app.models.enums import ClaimStatus, Currency, ExpenseCategory
from app.repositories.agent_response_repository import AgentResponseRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.employee_repository import EmployeeRepository
from app.rules.constants import NOTES_MAX_LENGTH
from app.schemas.audit import (
    AccountSnapshot,
    AuditContext,
    AuditResult,
    ClaimSnapshot,
    EmployeeSnapshot,
    ProjectSnapshot,
)
from app.schemas.policy import PolicyAgentOutput, PolicyAgentResult, PolicyAgentStatus
from app.schemas.validation import (
    ValidationAgentOutput,
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationSeverity,
)
from app.core.exceptions import ClaimNotFoundError

_RECEIPT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


class EmployeeNotFoundError(Exception):
    def __init__(self, employee_id: str):
        super().__init__(f"Employee {employee_id} was not found")
        self.employee_id = employee_id
        self.code = "employee_not_found"


class AuditPersistError(Exception):
    def __init__(self, message: str, *, code: str = "audit_persist_error"):
        super().__init__(message)
        self.code = code


class AuditTools:
    def __init__(self, session_factory=async_session_factory) -> None:
        self._session_factory = session_factory

    async def load_audit_context(self, claim_id: int) -> AuditContext:
        async with self._session_factory() as session:
            claim = await ClaimRepository(session).get_claim(claim_id)
            if claim is None:
                raise ClaimNotFoundError(claim_id)

            employees = EmployeeRepository(session)
            employee_row = await employees.get_employee(claim.employee_id)
            if employee_row is None:
                raise EmployeeNotFoundError(claim.employee_id)

            manager_row = None
            if employee_row.get("manager_id"):
                manager_row = await employees.get_manager(employee_row["manager_id"])

            project_code = claim.project_code or employee_row.get("project_code")
            project_row = (
                await employees.get_project(project_code) if project_code else None
            )
            account_row = None
            if project_row and project_row.get("account_id"):
                account_row = await employees.get_account(project_row["account_id"])

            return AuditContext(
                claim=_claim_snapshot(claim),
                employee=EmployeeSnapshot.model_validate(employee_row),
                manager=(
                    EmployeeSnapshot.model_validate(manager_row)
                    if manager_row
                    else None
                ),
                project=(
                    ProjectSnapshot.model_validate(project_row) if project_row else None
                ),
                account=(
                    AccountSnapshot(
                        account_id=account_row["account_id"],
                        account_name=account_row["account_name"],
                        fiscal_year=account_row["fiscal_year"],
                        budget_allocated=Decimal(str(account_row["budget_allocated"])),
                        remaining_budget=Decimal(str(account_row["remaining_budget"])),
                        currency=account_row["currency"],
                    )
                    if account_row
                    else None
                ),
            )

    async def update_claim_status(
        self, claim_id: int, status: ClaimStatus
    ) -> ClaimStatus:
        async with self._session_factory() as session:
            claims = ClaimRepository(session)
            try:
                updated = await claims.update_status(claim_id, status)
                if updated is None:
                    raise ClaimNotFoundError(claim_id)
                await session.commit()
            except ClaimNotFoundError:
                raise
            except Exception as exc:
                await session.rollback()
                raise AuditPersistError(
                    f"Failed to update claim status: {exc}"
                ) from exc
            return updated.status

    async def create_run_row(self, claim_id: int) -> int:
        async with self._session_factory() as session:
            claims = ClaimRepository(session)
            if await claims.get_claim(claim_id) is None:
                raise ClaimNotFoundError(claim_id)
            repository = AgentResponseRepository(session)
            try:
                row = await repository.insert_run(claim_id=claim_id)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                raise AuditPersistError(
                    f"Failed to create agent_response row: {exc}"
                ) from exc
            return row.id

    async def store_validation_result(
        self,
        *,
        row_id: int,
        result: ValidationAgentResult,
    ) -> None:
        if result.status != ValidationAgentStatus.SUCCESS or result.output is None:
            return
        payload = result.output.model_dump(mode="json")
        violation = format_validation_violation(result.output)
        notes = _truncate_notes(result.output.summary)
        confidence = Decimal(str(round(result.output.confidence, 2)))
        async with self._session_factory() as session:
            repository = AgentResponseRepository(session)
            try:
                updated = await repository.update_validation_response(
                    row_id=row_id,
                    validation_response=payload,
                    validation_violation=violation,
                    notes=notes,
                    confidence_score=confidence,
                )
                if updated is None:
                    raise AuditPersistError(
                        f"agent_response {row_id} was not found",
                        code="agent_response_not_found",
                    )
                await session.commit()
            except AuditPersistError:
                raise
            except Exception as exc:
                await session.rollback()
                raise AuditPersistError(
                    f"Failed to store validation result: {exc}"
                ) from exc

    async def store_policy_result(
        self,
        *,
        row_id: int,
        result: PolicyAgentResult,
    ) -> None:
        if result.status != PolicyAgentStatus.SUCCESS or result.output is None:
            return
        payload = result.output.model_dump(mode="json")
        violation = format_policy_violation(result.output)
        notes = _truncate_notes(result.output.summary)
        confidence = Decimal(str(round(result.output.confidence, 2)))
        async with self._session_factory() as session:
            repository = AgentResponseRepository(session)
            try:
                updated = await repository.update_policy_response(
                    row_id=row_id,
                    policy_response=payload,
                    policy_violation=violation,
                    notes=notes,
                    confidence_score=confidence,
                )
                if updated is None:
                    raise AuditPersistError(
                        f"agent_response {row_id} was not found",
                        code="agent_response_not_found",
                    )
                await session.commit()
            except AuditPersistError:
                raise
            except Exception as exc:
                await session.rollback()
                raise AuditPersistError(
                    f"Failed to store policy result: {exc}"
                ) from exc

    async def store_audit_result(
        self,
        *,
        row_id: int,
        result: AuditResult,
    ) -> None:
        payload = result.model_dump(mode="json")
        notes = _truncate_notes(result.notes)
        confidence = Decimal(str(round(result.confidence, 2)))
        async with self._session_factory() as session:
            repository = AgentResponseRepository(session)
            try:
                updated = await repository.update_audit_result(
                    row_id=row_id,
                    audit_response=payload,
                    validation_violation=result.validation_violation,
                    policy_violation=result.policy_violation,
                    notes=notes,
                    confidence_score=confidence,
                )
                if updated is None:
                    raise AuditPersistError(
                        f"agent_response {row_id} was not found",
                        code="agent_response_not_found",
                    )
                await session.commit()
            except AuditPersistError:
                raise
            except Exception as exc:
                await session.rollback()
                raise AuditPersistError(
                    f"Failed to store audit result: {exc}"
                ) from exc

    async def get_latest_for_claim(self, claim_id: int):
        async with self._session_factory() as session:
            claims = ClaimRepository(session)
            claim = await claims.get_claim(claim_id)
            if claim is None:
                raise ClaimNotFoundError(claim_id)
            row = await AgentResponseRepository(session).get_latest_for_claim(
                claim_id
            )
            return claim, row


def load_receipt_bytes(
    receipt_url: str | None,
) -> tuple[bytes | None, str | None]:
    """Read a local receipt path. Remote URLs are not fetched."""
    if not receipt_url:
        return None, None
    path = Path(receipt_url)
    if not path.is_file():
        return None, None
    suffix = path.suffix.lower()
    return path.read_bytes(), _RECEIPT_MIME.get(suffix)


def format_validation_violation(output: ValidationAgentOutput | None) -> str | None:
    if output is None:
        return None
    parts: list[str] = []
    for finding in output.findings:
        if finding.severity not in {
            ValidationSeverity.BLOCKING,
            ValidationSeverity.WARNING,
        }:
            continue
        text = finding.description
        if finding.detail:
            text = f"{text} ({finding.detail})"
        parts.append(text)
    return "; ".join(parts) if parts else None


def format_policy_violation(output: PolicyAgentOutput | None) -> str | None:
    if output is None or not output.violations:
        return None
    parts: list[str] = []
    for violation in output.violations:
        if violation.policy_reference:
            parts.append(f"{violation.description} [{violation.policy_reference}]")
        else:
            parts.append(violation.description)
    return "; ".join(parts) if parts else None


def _truncate_notes(notes: str | None) -> str | None:
    if not notes:
        return notes
    if len(notes) > NOTES_MAX_LENGTH:
        return notes[: NOTES_MAX_LENGTH - 1] + "…"
    return notes


def _claim_snapshot(claim: Any) -> ClaimSnapshot:
    category = claim.category
    if not isinstance(category, ExpenseCategory):
        category = ExpenseCategory(category)
    currency = claim.currency
    if not isinstance(currency, Currency):
        currency = Currency(currency)
    return ClaimSnapshot(
        claim_id=claim.claim_id,
        employee_id=claim.employee_id,
        business_purpose=claim.business_purpose,
        merchant_name=claim.merchant_name,
        category=category,
        category_data=claim.category_data or {},
        project_code=claim.project_code,
        claim_amount=claim.claim_amount,
        currency=currency,
        status=claim.status,
        priority=claim.priority,
        receipt_url=claim.receipt_url,
        auditer_id=claim.auditer_id,
    )
