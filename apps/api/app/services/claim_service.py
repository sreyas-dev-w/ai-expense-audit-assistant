"""Claim submission workflow.

``ClaimSubmissionService`` is the application layer behind ``POST /claims``
(``docs/backend/api-design.md``): it validates the submitted receipt, stores
it, verifies the employee exists, and persists the claim in one short,
deliberate transaction. In that same transaction it also creates the claim's
``agent_response`` row (empty stage outputs, filled in later as the agents
respond), so a persisted claim always has one. The HTTP layer responds with 201
only after that transaction commits.

The Audit Agent is then invoked in the background. ``run_audit_background``
hands off to the production ``AuditService`` outside the request lifecycle; the
agent itself fetches the claim and updates workflow data through its tools
(``docs/agents/orchestration.md``, ``docs/backend/reliability.md``).
"""
import logging
from typing import Any, Awaitable, Callable

from app.db.session import async_session_factory
from app.repositories.agent_response_repository import AgentResponseRepository
from app.repositories.claim_repository import ClaimRepository
from app.schemas.claim import ClaimCreate, ClaimSubmissionResponse
from app.services.file_service import (
    ALLOWED_RECEIPT_MIME_TYPES,
    RECEIPT_EXTENSION_BY_MIME,
    store_receipt,
)
from app.services.file_service import receipt_url_from_path

logger = logging.getLogger(__name__)


class ClaimSubmissionError(Exception):
    """Base error for the claim submission flow, mapped to an HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "claim_submission_error",
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class EmployeeNotFoundError(ClaimSubmissionError):
    def __init__(self, employee_id: str):
        super().__init__(
            f"Employee {employee_id} was not found",
            code="employee_not_found",
            status_code=404,
        )
        self.employee_id = employee_id


class UnsupportedReceiptError(ClaimSubmissionError):
    def __init__(self, mime_type: str | None):
        super().__init__(
            f"Unsupported receipt format: {mime_type or 'unknown'}. "
            "Supported formats are PNG, JPEG, and PDF.",
            code="unsupported_receipt_format",
            status_code=400,
        )


class EmptyReceiptError(ClaimSubmissionError):
    def __init__(self):
        super().__init__(
            "The submitted receipt is empty",
            code="empty_receipt",
            status_code=400,
        )


class ClaimSubmissionService:
    """Application entry point for claim submission + audit handoff."""

    def __init__(
        self,
        *,
        session_factory=async_session_factory,
        audit_runner: Callable[[int], Awaitable[Any]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._audit_runner = audit_runner

    async def submit_claim(
        self,
        *,
        claim: ClaimCreate,
        receipt_filename: str,
        receipt_content: bytes,
        receipt_mime_type: str | None,
    ) -> ClaimSubmissionResponse:
        """Validate + store the receipt, persist the claim, return the 201 payload."""
        mime_type = self._validate_receipt_mime(receipt_mime_type)
        if not receipt_content:
            raise EmptyReceiptError()

        receipt_url = receipt_url_from_path(
            store_receipt(
                receipt_filename,
                receipt_content,
                extension=RECEIPT_EXTENSION_BY_MIME[mime_type],
            )
        )

        async with self._session_factory() as session:
            repository = ClaimRepository(session)
            if await repository.get_employee(claim.employee_id) is None:
                raise EmployeeNotFoundError(claim.employee_id)
            row = await repository.create(
                employee_id=claim.employee_id,
                category=claim.category,
                category_data=claim.category_data.model_dump(mode="json"),
                claim_amount=claim.claim_amount,
                currency=claim.currency,
                business_purpose=claim.business_purpose,
                merchant_name=claim.merchant_name,
                project_code=claim.project_code,
                receipt_url=receipt_url,
            )
            agent_responses = AgentResponseRepository(session)
            await agent_responses.create_for_claim(claim_id=row.claim_id)
            try:
                await session.commit()
            except Exception as exc:
                await session.rollback()
                raise ClaimSubmissionError(
                    f"Failed to persist the claim: {exc}",
                    code="claim_persist_failed",
                ) from exc

        return ClaimSubmissionResponse(
            claim_id=row.claim_id,
            status=row.status,
            ai_run_status=row.ai_run_status,
            receipt_url=receipt_url,
        )

    async def run_audit_background(self, claim_id: int) -> None:
        """Trigger the Audit Agent for the just-created claim.

        Runs outside the request cycle (FastAPI ``BackgroundTasks``). The agent
        owns fetching and updating the claim/workflow data itself; failures are
        logged here and never raised into the request lifecycle.
        """
        runner = self._audit_runner
        if runner is None:
            from app.services.audit_service import AuditService

            runner = AuditService().run_audit
        try:
            await runner(claim_id)
        except Exception as exc:
            logger.exception(
                "Background audit failed for claim %s: %s", claim_id, exc
            )

    @staticmethod
    def _validate_receipt_mime(mime_type: str | None) -> str:
        normalized = (mime_type or "").split(";")[0].strip().lower()
        if normalized not in ALLOWED_RECEIPT_MIME_TYPES:
            raise UnsupportedReceiptError(mime_type)
        return normalized