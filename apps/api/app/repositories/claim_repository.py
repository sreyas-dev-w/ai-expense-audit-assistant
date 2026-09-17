<<<<<<< HEAD
"""Data access for claims used by the Audit Agent tools.

Persistence-only: the tool layer owns session lifecycle and transaction
boundaries so no session is ever held across an LLM/agent call
(``docs/backend/reliability.md``). Methods are deliberately narrow — they use
``session.get`` and direct field updates only.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims import Claim
from app.models.employees import Employee
from app.models.enums import AIDecision, AIRunStatus, ClaimPriority, ClaimStatus
from app.rules.constants import EMPLOYEE_CLAIM_SCAN_LIMIT

def _now() -> datetime:
    return datetime.now(timezone.utc)

class ClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get(self, claim_id: int) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def get_employee(self, employee_id: str) -> Employee | None:
        return await self._session.get(Employee, employee_id)

    async def update_run_status(
        self,
        claim_id: int,
        *,
        claim_status: ClaimStatus,
        ai_run_status: AIRunStatus,
        notes: str | None = None,
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.status = claim_status
        claim.ai_run_status = ai_run_status
        if notes is not None:
            claim.auditer_notes = notes
        claim.claim_updated_at = _now()
        return claim

    async def update_category_data(
        self, claim_id: int, category_data: dict
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.category_data = category_data
        claim.claim_updated_at = _now()
        return claim

    async def update_result(
        self,
        claim_id: int,
        *,
        ai_decision: AIDecision,
        priority: ClaimPriority,
        ai_run_status: AIRunStatus = AIRunStatus.COMPLETED,
        notes: str | None = None,
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.ai_decision = ai_decision
        claim.priority = priority
        claim.ai_run_status = ai_run_status
        if notes is not None:
            claim.auditer_notes = notes
        claim.claim_updated_at = _now()
        return claim

    async def get_claim(self, claim_id: int) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def list_employee_claims(
        self,
        employee_id: str,
        *,
        exclude_claim_id: int | None = None,
        limit: int = EMPLOYEE_CLAIM_SCAN_LIMIT,
    ) -> list[dict[str, Any]]:
        stmt = select(Claim).where(Claim.employee_id == employee_id)
        if exclude_claim_id is not None:
            stmt = stmt.where(Claim.claim_id != exclude_claim_id)
        stmt = stmt.order_by(Claim.claim_id.desc()).limit(limit)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [_claim_row(claim) for claim in rows]


def _claim_row(claim: Claim) -> dict[str, Any]:
    amount = claim.claim_amount
    if amount is not None and not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return {
        "claim_id": claim.claim_id,
        "employee_id": claim.employee_id,
        "merchant_name": claim.merchant_name,
        "claim_amount": amount,
        "category_data": claim.category_data or {},
        "claim_created_at": claim.claim_created_at,
    }

