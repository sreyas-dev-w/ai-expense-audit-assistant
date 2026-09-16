"""Read access for expense claims used by validation (duplicates + persist)."""
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims import Claim
from app.rules.constants import EMPLOYEE_CLAIM_SCAN_LIMIT


class ClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
