"""Data access for ``agent_response`` rows.

Each audit run persists the structured policy/validation agent envelopes here
so the human auditor/manager can reconstruct what the agents concluded
(``docs/schemas/database-schema.md``).
"""
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_response import AgentResponse


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_agent_response(
        self,
        *,
        claim_id: int,
        validation_response: dict[str, Any] | None = None,
        policy_response: dict[str, Any] | None = None,
        notes: str | None = None,
        confidence_score: Decimal | None = None,
    ) -> AgentResponse:
        record = AgentResponse(
            claim_id=claim_id,
            validation_response=validation_response,
            policy_response=policy_response,
            notes=notes,
            confidence_score=confidence_score,
        )
        self._session.add(record)
        return record