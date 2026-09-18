"""Persistence for the ``agent_response`` row of a claim.

Every claim gets exactly one ``agent_response`` row, created eagerly at claim
submission time (see ``ClaimSubmissionService``). Agent stage outputs are
written into that row progressively as they arrive:

- ``policy_response`` / ``validation_response`` once each agent responds,
- ``notes`` (the human-readable AI note shown to the auditor) once the final
  note is generated,

so the auditor/manager can always reconstruct what the agents concluded
(``docs/schemas/database-schema.md``). Methods are deliberately narrow and
persistence-only — the service/tool layer owns session lifecycle and
transaction boundaries (``docs/backend/reliability.md``).
"""
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_response import AgentResponse


class AgentResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get_by_claim_id(
        self,
        claim_id: int,
    ) -> AgentResponse | None:

        result = await self._session.execute(
            select(AgentResponse).where(
                AgentResponse.claim_id == claim_id
            )
        )

        return result.scalar_one_or_none()
    
    async def create_for_claim(self, *, claim_id: int) -> AgentResponse:
        """Insert the claim's ``agent_response`` row with nullable fields empty."""
        row = AgentResponse(claim_id=claim_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_claim(self, claim_id: int) -> AgentResponse | None:
        """Return the claim's latest ``agent_response`` row, or ``None``."""
        stmt = (
            select(AgentResponse)
            .where(AgentResponse.claim_id == claim_id)
            .order_by(AgentResponse.id.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_or_create_for_claim(self, claim_id: int) -> AgentResponse:
        """Return the claim's ``agent_response`` row, creating it if absent.

        Handles legacy claims that predate eager row creation so updates still
        land somewhere durable instead of failing.
        """
        row = await self.get_for_claim(claim_id)
        if row is None:
            row = await self.create_for_claim(claim_id=claim_id)
        return row

    async def update_validation_response(
        self,
        *,
        claim_id: int,
        validation_response: dict[str, Any],
        confidence_score: Decimal | None = None,
        notes: str | None = None,
    ) -> AgentResponse:
        """Record the Validation Agent's output on the claim's row."""
        row = await self.get_or_create_for_claim(claim_id)
        row.validation_response = validation_response
        if confidence_score is not None:
            row.confidence_score = confidence_score
        if notes is not None:
            row.notes = notes
        return row

    async def update_responses(
        self,
        *,
        claim_id: int,
        policy_response: dict[str, Any] | None = None,
        validation_response: dict[str, Any] | None = None,
        confidence_score: Decimal | None = None,
        notes: str | None = None,
    ) -> AgentResponse:
        """Record the Policy/Validation agent envelopes on the claim's row.

        Only non-``None`` payloads are written: a missing stage result must not
        overwrite a previously stored response, and assigning ``None`` to a
        JSONB column would persist a JSON ``null`` rather than leave it empty.
        """
        row = await self.get_or_create_for_claim(claim_id)
        if policy_response is not None:
            row.policy_response = policy_response
        if validation_response is not None:
            row.validation_response = validation_response
        if confidence_score is not None:
            row.confidence_score = confidence_score
        if notes is not None:
            row.notes = notes
        return row

    async def update_notes(self, *, claim_id: int, notes: str) -> AgentResponse:
        """Store the final AI note on the claim's row."""
        row = await self.get_or_create_for_claim(claim_id)
        row.notes = notes
        return row