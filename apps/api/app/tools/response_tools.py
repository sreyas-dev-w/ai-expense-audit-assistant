"""Persistence tools for agent stage outputs.

- ``StoreExtractionTool`` persists the OCR-extracted category data onto the
  claim's ``category_data`` (``claims`` table).
- ``StoreAgentResponseTool`` persists the policy/validation agent envelopes
  into an ``agent_response`` row (``agent_response`` table).
"""
from decimal import Decimal
from typing import Any

from app.db.session import async_session_factory
from app.repositories.audit_repository import AuditRepository
from app.repositories.claim_repository import ClaimRepository
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
    """Persist the policy/validation agent envelopes into ``agent_response``."""

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
                repository = AuditRepository(session)
                record = await repository.create_agent_response(
                    claim_id=claim_id,
                    policy_response=_json_payload(policy_result),
                    validation_response=_json_payload(validation_result),
                    notes=notes,
                    confidence_score=_confidence(policy_result),
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


def _confidence(policy_result: Any) -> Decimal | None:
    output = getattr(policy_result, "output", None)
    confidence = getattr(output, "confidence", None)
    if confidence is None:
        return None
    try:
        return Decimal(str(confidence))
    except (ValueError, ArithmeticError):
        return None