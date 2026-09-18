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

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.repositories.agent_response_repository import AgentResponseRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.claim import ClaimAuditUpdate, ClaimCreate, ClaimSubmissionResponse
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
            await agent_responses.create_for_claim(
                claim_id=row.claim_id
            )

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
                "Background audit failed for claim %s: %s",
                claim_id,
                exc,
            )

    @staticmethod
    def _validate_receipt_mime(mime_type: str | None) -> str:
        normalized = (mime_type or "").split(";")[0].strip().lower()

        if normalized not in ALLOWED_RECEIPT_MIME_TYPES:
            raise UnsupportedReceiptError(mime_type)

        return normalized


# ============================================================
# GET CLAIM DETAILS BY EMPLOYEE ID
# ============================================================

class ClaimService:
    """Application service for retrieving employee claim details."""

    @staticmethod
    async def get_claims_by_employee_id(
        db: AsyncSession,
        employee_id: str,
    ):
        # First verify that the employee exists.
        employee_repository = EmployeeRepository(db)

        employee = await employee_repository.get_employee(
            employee_id
        )

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{employee_id}' not found",
            )

        # Fetch all claims belonging to that employee.
        claim_repository = ClaimRepository(db)

        return await claim_repository.get_claims_by_employee_id(
            employee_id
        )

    
    @staticmethod
    async def update_claim_audit(
        db: AsyncSession,
        claim_id: int,
        audit_data: ClaimAuditUpdate,
    ):
        """
        Update manager/auditor-controlled fields for a claim.

        Updates only:
        - status
        - priority
        - auditer_id
        - auditer_notes

        claim_updated_at is maintained automatically by the repository.
        """

        claim_repository = ClaimRepository(db)

        # 1. Check that the claim exists.
        claim = await claim_repository.get(claim_id)

        if claim is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found",
            )

        # 2. Check that the auditor/employee exists.
        auditor = await claim_repository.get_employee(
            audit_data.auditer_id
        )

        if auditor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Employee with ID "
                    f"'{audit_data.auditer_id}' not found"
                ),
            )

        # 3. Update only the audit-related fields.
        updated_claim = await claim_repository.update_audit_fields(
            claim_id,
            status=audit_data.status,
            priority=audit_data.priority,
            auditer_id=audit_data.auditer_id,
            auditer_notes=audit_data.auditer_notes,
        )

        if updated_claim is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found",
            )

        # 4. Commit the transaction.
        await db.commit()

        # 5. Refresh the updated object.
        await db.refresh(updated_claim)

        return updated_claim
