"""Claim lifecycle application service.

Owns the rules the routers must not carry: who may see a claim, which status a
claim moves into, and where an uploaded receipt is persisted. The agent
workflow is triggered separately via ``POST /api/v1/audits`` -- it reads the
receipt back off ``claims.receipt_url``.

Lifecycle: SUBMITTED on create, IN_AUDIT while the Audit Agent runs, then
APPROVED or REJECTED once a manager decides.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClaimNotFoundError
from app.models.claims import Claim
from app.models.employees import Employee
from app.models.enums import ClaimStatus
from app.repositories.claim_repository import ClaimRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.claim import (
    ClaimCreate,
    ClaimDecision,
    ClaimDecisionRequest,
    ClaimListItem,
    ClaimRead,
)
from app.services.file_service import UnsupportedReceiptError, store_receipt

claim_create_adapter: TypeAdapter = TypeAdapter(ClaimCreate)
claim_read_adapter: TypeAdapter = TypeAdapter(ClaimRead)

_DECISION_STATUS = {
    ClaimDecision.APPROVE: ClaimStatus.APPROVED,
    ClaimDecision.REJECT: ClaimStatus.REJECTED,
}
_DECIDED = {ClaimStatus.APPROVED, ClaimStatus.REJECTED}


class ClaimAccessError(Exception):
    def __init__(self, message: str = "You cannot access this claim") -> None:
        super().__init__(message)
        self.code = "claim_forbidden"


class ClaimPayloadError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "invalid_claim_payload"


class ClaimAlreadyDecidedError(Exception):
    def __init__(self, claim_id: int, status: ClaimStatus) -> None:
        super().__init__(
            f"Claim {claim_id} was already {status.value} and cannot be changed"
        )
        self.code = "claim_already_decided"


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._claims = ClaimRepository(session)
        self._employees = EmployeeRepository(session)

    # -- create ------------------------------------------------------------

    async def create(
        self,
        *,
        employee: Employee,
        payload: str,
        receipt_filename: str | None,
        receipt_bytes: bytes | None,
    ) -> dict[str, Any]:
        try:
            parsed = claim_create_adapter.validate_json(payload)
        except ValidationError as exc:
            raise ClaimPayloadError(exc.json()) from exc

        if parsed.employee_id != employee.employee_id:
            raise ClaimAccessError("A claim can only be filed for yourself")

        receipt_url: str | None = None
        if receipt_bytes:
            try:
                receipt_url = str(
                    store_receipt(receipt_filename or "receipt", receipt_bytes)
                )
            except UnsupportedReceiptError as exc:
                raise ClaimPayloadError(str(exc)) from exc

        claim = Claim(
            employee_id=employee.employee_id,
            business_purpose=parsed.business_purpose,
            merchant_name=parsed.merchant_name,
            category=parsed.category,
            category_data=parsed.category_data.model_dump(mode="json"),
            project_code=parsed.project_code or employee.project_code,
            claim_amount=parsed.claim_amount,
            currency=parsed.currency,
            status=ClaimStatus.SUBMITTED,
            receipt_url=receipt_url,
        )
        created = await self._claims.create(claim)
        await self._session.commit()
        return _to_read(created)

    # -- read --------------------------------------------------------------

    async def list_for(
        self, *, employee: Employee, scope: str
    ) -> list[ClaimListItem]:
        if scope == "team":
            if not employee.is_manager:
                raise ClaimAccessError("Only managers can list team claims")
            employee_ids = await self._employees.get_report_ids(
                employee.employee_id
            )
        else:
            employee_ids = [employee.employee_id]

        rows = await self._claims.list_by_employees(employee_ids)
        return [_to_list_item(claim, name, run) for claim, name, run in rows]

    async def get(self, *, employee: Employee, claim_id: int) -> dict[str, Any]:
        claim = await self._require_visible_claim(employee, claim_id)
        return _to_read(claim)

    # -- decide ------------------------------------------------------------

    async def decide(
        self,
        *,
        manager: Employee,
        claim_id: int,
        request: ClaimDecisionRequest,
    ) -> dict[str, Any]:
        claim = await self._claims.get_claim(claim_id)
        if claim is None:
            raise ClaimNotFoundError(claim_id)
        if not await self._manages(manager, claim.employee_id):
            raise ClaimAccessError("You do not manage the employee who filed this claim")
        if claim.status in _DECIDED:
            raise ClaimAlreadyDecidedError(claim_id, claim.status)

        updated = await self._claims.record_decision(
            claim_id,
            status=_DECISION_STATUS[request.decision],
            auditer_id=manager.employee_id,
            auditer_notes=request.notes.strip(),
        )
        await self._session.commit()
        return _to_read(updated)

    # -- helpers -----------------------------------------------------------

    async def resolve_receipt_claim(
        self, *, employee: Employee, stored_name: str
    ) -> Claim | None:
        """The claim whose receipt is ``stored_name``, if this employee may see it."""
        scope = "team" if employee.is_manager else "mine"
        employee_ids = (
            await self._employees.get_report_ids(employee.employee_id)
            if scope == "team"
            else []
        )
        employee_ids = [*employee_ids, employee.employee_id]
        for claim, _, _ in await self._claims.list_by_employees(employee_ids):
            if claim.receipt_url and claim.receipt_url.endswith(stored_name):
                return claim
        return None

    async def _require_visible_claim(
        self, employee: Employee, claim_id: int
    ) -> Claim:
        claim = await self._claims.get_claim(claim_id)
        if claim is None:
            raise ClaimNotFoundError(claim_id)
        if claim.employee_id == employee.employee_id:
            return claim
        if await self._manages(employee, claim.employee_id):
            return claim
        raise ClaimAccessError()

    async def _manages(self, employee: Employee, employee_id: str) -> bool:
        if not employee.is_manager:
            return False
        reports = await self._employees.get_report_ids(employee.employee_id)
        return employee_id in reports


def _to_read(claim: Claim) -> dict[str, Any]:
    """Validate through the discriminated ``ClaimRead`` union before responding."""
    return claim_read_adapter.dump_python(
        claim_read_adapter.validate_python(claim, from_attributes=True),
        mode="json",
    )


def _to_list_item(claim: Claim, employee_name: str | None, run) -> ClaimListItem:
    recommendation: str | None = None
    if run is not None and run.audit_response:
        recommendation = run.audit_response.get("recommendation")
    confidence: Decimal | None = None
    if run is not None and run.confidence_score is not None:
        confidence = run.confidence_score
    return ClaimListItem(
        claim_id=claim.claim_id,
        employee_id=claim.employee_id,
        employee_name=employee_name,
        auditer_id=claim.auditer_id,
        auditer_notes=claim.auditer_notes,
        project_code=claim.project_code,
        business_purpose=claim.business_purpose,
        merchant_name=claim.merchant_name,
        category=claim.category,
        category_data=claim.category_data or {},
        claim_amount=claim.claim_amount,
        currency=claim.currency,
        status=claim.status,
        priority=claim.priority,
        receipt_url=claim.receipt_url,
        claim_created_at=claim.claim_created_at,
        claim_updated_at=claim.claim_updated_at,
        receipt_created_at=claim.receipt_created_at,
        has_audit=run is not None and run.audit_response is not None,
        audit_recommendation=recommendation,
        audit_confidence=confidence,
    )
