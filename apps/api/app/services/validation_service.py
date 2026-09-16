"""Application service for the Validation Agent.

Runs the LangGraph subgraph, optionally persists SUCCESS output into
``agent_response.validation_response``, and exposes the Policy RAG request
mapper. Agents never open database sessions; persist uses a short write
transaction after the graph returns.
"""
from decimal import Decimal

from app.agents.validation_agent import run_validation_agent
from app.core.exceptions import ClaimNotFoundError
from app.db.session import async_session_factory
from app.repositories.agent_response_repository import AgentResponseRepository
from app.repositories.claim_repository import ClaimRepository
from app.rules.constants import NOTES_MAX_LENGTH
from app.schemas.extraction import OCRResponse
from app.schemas.policy import PolicyEvaluationRequest
from app.schemas.validation import (
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationEvaluateResponse,
    ValidationRequest,
)
from app.services.gemini_client import GeminiClient
from app.services.policy_request_mapper import to_policy_evaluation_request
from app.services.validation_context_service import ValidationContextService


class ValidationPersistError(Exception):
    def __init__(self, message: str, *, code: str = "validation_persist_error"):
        super().__init__(message)
        self.code = code


class ValidationService:
    def __init__(
        self,
        *,
        llm_client: GeminiClient,
        context_service: ValidationContextService | None = None,
        session_factory=async_session_factory,
    ) -> None:
        self._llm_client = llm_client
        self._context_service = context_service or ValidationContextService(
            session_factory=session_factory
        )
        self._session_factory = session_factory

    async def evaluate(
        self, request: ValidationRequest
    ) -> ValidationEvaluateResponse:
        result = await run_validation_agent(
            request,
            context_service=self._context_service,
            llm_client=self._llm_client,
        )
        stored_id: int | None = None
        if request.persist and request.claim_id is not None:
            stored_id = await self.store_validation_result(
                claim_id=request.claim_id, result=result
            )
        return ValidationEvaluateResponse(
            status=result.status,
            output=result.output,
            error=result.error,
            stored_agent_response_id=stored_id,
        )

    async def store_validation_result(
        self,
        *,
        claim_id: int,
        result: ValidationAgentResult,
    ) -> int | None:
        """Insert ``validation_response`` for ``claim_id``. SUCCESS output only."""
        if (
            result.status != ValidationAgentStatus.SUCCESS
            or result.output is None
        ):
            return None

        payload = result.output.model_dump(mode="json")
        notes = result.output.summary
        if notes and len(notes) > NOTES_MAX_LENGTH:
            notes = notes[: NOTES_MAX_LENGTH - 1] + "…"
        confidence = Decimal(str(round(result.output.confidence, 2)))

        async with self._session_factory() as session:
            claims = ClaimRepository(session)
            if await claims.get_claim(claim_id) is None:
                raise ClaimNotFoundError(claim_id)
            repository = AgentResponseRepository(session)
            try:
                row = await repository.insert_validation_response(
                    claim_id=claim_id,
                    validation_response=payload,
                    notes=notes,
                    confidence_score=confidence,
                )
                await session.commit()
            except ClaimNotFoundError:
                raise
            except Exception as exc:
                await session.rollback()
                raise ValidationPersistError(
                    f"Failed to store validation result: {exc}"
                ) from exc
            return row.id

    def build_policy_request(
        self,
        ocr: OCRResponse,
        *,
        claim_id: int | None = None,
    ) -> PolicyEvaluationRequest:
        return to_policy_evaluation_request(ocr, claim_id=claim_id)
