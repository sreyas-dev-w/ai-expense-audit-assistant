"""Persistence for structured agent stage outputs."""
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_response import AgentResponse


class AgentResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
