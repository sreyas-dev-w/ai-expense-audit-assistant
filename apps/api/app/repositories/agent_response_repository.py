"""Persistence for structured agent stage outputs."""
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_response import AgentResponse


class AgentResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_run(self, *, claim_id: int) -> AgentResponse:
        row = AgentResponse(claim_id=claim_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def insert_validation_response(
        self,
        *,
        claim_id: int,
        validation_response: dict[str, Any],
        notes: str | None,
        confidence_score: Decimal | None,
    ) -> AgentResponse:
        row = AgentResponse(
            claim_id=claim_id,
            validation_response=validation_response,
            policy_response=None,
            notes=notes,
            confidence_score=confidence_score,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_id(self, row_id: int) -> AgentResponse | None:
        return await self._session.get(AgentResponse, row_id)

    async def get_latest_for_claim(self, claim_id: int) -> AgentResponse | None:
        stmt = (
            select(AgentResponse)
            .where(AgentResponse.claim_id == claim_id)
            .order_by(AgentResponse.id.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update_validation_response(
        self,
        *,
        row_id: int,
        validation_response: dict[str, Any],
        validation_violation: str | None = None,
        notes: str | None = None,
        confidence_score: Decimal | None = None,
    ) -> AgentResponse | None:
        row = await self.get_by_id(row_id)
        if row is None:
            return None
        row.validation_response = validation_response
        if validation_violation is not None:
            row.validation_violation = validation_violation
        if notes is not None:
            row.notes = notes
        if confidence_score is not None:
            row.confidence_score = confidence_score
        await self._session.flush()
        return row

    async def update_policy_response(
        self,
        *,
        row_id: int,
        policy_response: dict[str, Any],
        policy_violation: str | None = None,
        notes: str | None = None,
        confidence_score: Decimal | None = None,
    ) -> AgentResponse | None:
        row = await self.get_by_id(row_id)
        if row is None:
            return None
        row.policy_response = policy_response
        if policy_violation is not None:
            row.policy_violation = policy_violation
        if notes is not None:
            row.notes = notes
        if confidence_score is not None:
            row.confidence_score = confidence_score
        await self._session.flush()
        return row

    async def update_audit_result(
        self,
        *,
        row_id: int,
        audit_response: dict[str, Any],
        validation_violation: str | None,
        policy_violation: str | None,
        notes: str | None,
        confidence_score: Decimal | None,
    ) -> AgentResponse | None:
        row = await self.get_by_id(row_id)
        if row is None:
            return None
        row.audit_response = audit_response
        row.validation_violation = validation_violation
        row.policy_violation = policy_violation
        row.notes = notes
        row.confidence_score = confidence_score
        await self._session.flush()
        return row
