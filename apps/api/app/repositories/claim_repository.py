"""Data access for claims used by the Audit Agent tools.

Persistence-only: the tool layer owns session lifecycle and transaction
boundaries so no session is ever held across an LLM/agent call
(``docs/backend/reliability.md``). Methods are deliberately narrow — they use
``session.get`` and direct field updates only.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims import Claim
from app.models.employees import Employee
from app.models.enums import AIDecision, AIRunStatus, ClaimPriority, ClaimStatus


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