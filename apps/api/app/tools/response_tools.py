"""Persistence tools for agent stage outputs.

- ``StoreExtractionTool`` persists the OCR-extracted category data onto the
  claim's ``category_data`` (``claims`` table).
- ``StoreAgentResponseTool`` writes the policy/validation agent envelopes into
  the claim's ``agent_response`` row (created eagerly at claim submission),
  updating it in place rather than inserting a new row.
- ``StoreAssessmentTool`` persists the Audit Agent's LLM assessment — only the
  note and the confidence — leaving the ``policy_response`` /
  ``validation_response`` columns untouched.
- ``GetAgentResponseTool`` is a read-only lookup used when the graph state does
  not already hold the stored policy/validation envelopes.
"""
from decimal import Decimal
from typing import Any

from app.db.session import async_session_factory
from app.repositories.agent_response_repository import AgentResponseRepository
from app.repositories.claim_repository import ClaimRepository
from app.schemas.agent_response import AgentResponseDetails
from app.schemas.assessment import AuditAssessment
from app.schemas.audit import AgentResponseRecord, ClaimWriteResult
from app.tools.base import AuditTool, AuditToolError, transaction_session


def _json_payload(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class StoreExtractionTool(AuditTool):
    """Persist the OCR-extracted category data onto the claim."""

    name = "store_extraction"
    description = "Persist the extracted category data onto the claim."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(self, *, claim_id: int, category_data: dict) -> ClaimWriteResult:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = ClaimRepository(session)
                claim = await repository.update_category_data(
                    claim_id, category_data
                )
                if claim is None:
                    raise AuditToolError(
                        f"Claim {claim_id} not found", code="claim_not_found"
                    )
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to store extraction for claim {claim_id}: {exc}",
                code="store_extraction_failed",
            ) from exc
        return ClaimWriteResult(
            claim_id=claim_id, updated_fields=["category_data"]
        )


class StoreAgentResponseTool(AuditTool):
    """Write the policy/validation agent envelopes into ``agent_response``."""

    name = "store_agent_response"
    description = "Persist the policy (and future validation) agent output for a claim."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(
        self,
        *,
        claim_id: int,
        policy_result: Any = None,
        validation_result: Any = None,
        notes: str | None = None,
    ) -> AgentResponseRecord:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = AgentResponseRepository(session)
                record = await repository.update_responses(
                    claim_id=claim_id,
                    policy_response=_json_payload(policy_result),
                    validation_response=_json_payload(validation_result),
                    confidence_score=_confidence(policy_result),
                    notes=notes,
                )
                await session.flush()
                record_id = record.id
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to store agent response for claim {claim_id}: {exc}",
                code="store_agent_response_failed",
            ) from exc
        return AgentResponseRecord(id=record_id, claim_id=claim_id)


class GetAgentResponseTool(AuditTool):
    """Read the claim's stored ``agent_response`` row (policy/validation envelopes)."""

    name = "get_agent_response"
    description = "Load the claim's stored agent response row."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(self, *, claim_id: int) -> AgentResponseDetails | None:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = AgentResponseRepository(session)
                row = await repository.get_by_claim_id(claim_id)
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to load agent response for claim {claim_id}: {exc}",
                code="agent_response_load_failed",
                retryable=True,
            ) from exc
        return AgentResponseDetails.model_validate(row) if row is not None else None


class StoreAssessmentTool(AuditTool):
    """Persist the Audit Agent's LLM assessment note + confidence.

    Only ``agent_response.notes`` and ``confidence_score`` are written; the
    ``validation_response`` / ``policy_response`` columns remain untouched.
    """

    name = "store_assessment"
    description = "Persist the AI assessment note and confidence for a claim."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(
        self,
        *,
        claim_id: int,
        assessment: AuditAssessment,
    ) -> AgentResponseRecord:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = AgentResponseRepository(session)
                record = await repository.update_assessment(
                    claim_id=claim_id,
                    notes=assessment.summary,
                    confidence_score=_decimal(assessment.confidence),
                )
                await session.flush()
                record_id = record.id
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to store audit assessment for claim {claim_id}: {exc}",
                code="store_assessment_failed",
            ) from exc
        return AgentResponseRecord(id=record_id, claim_id=claim_id)


def _confidence(policy_result: Any) -> Decimal | None:
    output = getattr(policy_result, "output", None)
    confidence = getattr(output, "confidence", None)
    return _decimal(confidence)


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None