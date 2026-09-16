"""Read/write access for expense claims used by validation and the Audit Agent."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_response import AgentResponse
from app.models.claims import Claim
from app.models.employees import Employee
from app.models.enums import ClaimStatus
from app.rules.constants import EMPLOYEE_CLAIM_SCAN_LIMIT


class ClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_claim(self, claim_id: int) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def create(self, claim: Claim) -> Claim:
        now = datetime.now(timezone.utc)
        claim.claim_created_at = claim.claim_created_at or now
        claim.claim_updated_at = now
        self._session.add(claim)
        await self._session.flush()
        await self._session.refresh(claim)
        return claim

    async def list_by_employees(
        self, employee_ids: Sequence[str]
    ) -> list[tuple[Claim, str | None, AgentResponse | None]]:
        """Claims for the given employees, newest first, each with its latest run.

        Returned as ``(claim, employee_name, latest_agent_response)`` so the list
        endpoint can render status without a second round trip per row.
        """
        if not employee_ids:
            return []

        stmt = (
            select(Claim, Employee.employee_name)
            .join(Employee, Employee.employee_id == Claim.employee_id)
            .where(Claim.employee_id.in_(list(employee_ids)))
            .order_by(Claim.claim_id.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        if not rows:
            return []

        claim_ids = [claim.claim_id for claim, _ in rows]
        runs = (
            await self._session.execute(
                select(AgentResponse)
                .where(AgentResponse.claim_id.in_(claim_ids))
                .order_by(AgentResponse.claim_id, AgentResponse.id)
            )
        ).scalars()
        # Ordered ascending, so the last write per claim wins.
        latest: dict[int, AgentResponse] = {run.claim_id: run for run in runs}

        return [(claim, name, latest.get(claim.claim_id)) for claim, name in rows]

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

    async def update_status(
        self, claim_id: int, status: ClaimStatus
    ) -> Claim | None:
        claim = await self.get_claim(claim_id)
        if claim is None:
            return None
        claim.status = status
        claim.claim_updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return claim

    async def record_decision(
        self,
        claim_id: int,
        *,
        status: ClaimStatus,
        auditer_id: str,
        auditer_notes: str,
    ) -> Claim | None:
        claim = await self.get_claim(claim_id)
        if claim is None:
            return None
        claim.status = status
        claim.auditer_id = auditer_id
        claim.auditer_notes = auditer_notes
        claim.claim_updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return claim


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
