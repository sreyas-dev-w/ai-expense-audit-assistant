from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.agent_response_repository import (
    AgentResponseRepository,
)


class AgentResponseService:

    @staticmethod
    async def get_by_claim_id(
        db: AsyncSession,
        claim_id: int,
    ):

        repository = AgentResponseRepository(db)

        agent_response = await repository.get_by_claim_id(
            claim_id
        )

        if agent_response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Agent response for claim "
                    f"{claim_id} not found"
                ),
            )

        return agent_response