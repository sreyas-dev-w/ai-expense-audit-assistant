"""Claim read / status tools for the Audit Agent.

Each tool owns a short, deliberate transaction (``transaction_session``) and
returns a typed structured result (``docs/agents/agent-tools.md``).
"""
from app.db.session import async_session_factory
from app.models.enums import AIDecision, AIRunStatus, ClaimPriority, ClaimStatus
from app.repositories.claim_repository import ClaimRepository
from app.schemas.audit import ClaimAuditContext, ClaimWriteResult
from app.tools.base import AuditTool, AuditToolError, transaction_session


class GetClaimTool(AuditTool):
    """Load a claim + its employee context for the audit run."""

    name = "get_claim"
    description = "Load a claim and its employee context for an audit run."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(self, *, claim_id: int) -> ClaimAuditContext | None:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = ClaimRepository(session)
                claim = await repository.get(claim_id)
                if claim is None:
                    return None
                employee = (
                    await repository.get_employee(claim.employee_id)
                    if claim.employee_id
                    else None
                )
                return ClaimAuditContext(
                    claim_id=claim.claim_id,
                    category=claim.category,
                    category_data=dict(claim.category_data or {}),
                    receipt_url=claim.receipt_url,
                    merchant_name=claim.merchant_name,
                    claim_amount=claim.claim_amount,
                    tax_amount=claim.tax_amount,
                    currency=claim.currency,
                    business_purpose=claim.business_purpose,
                    project_code=claim.project_code,
                    employee_id=claim.employee_id,
                    employee_job_level=employee.job_level if employee else None,
                    priority=claim.priority,
                )
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to load claim {claim_id}: {exc}",
                code="claim_load_failed",
                retryable=True,
            ) from exc


class UpdateAuditRunStatusTool(AuditTool):
    """Update the claim's workflow status (in_audit + ai run status)."""

    name = "update_audit_run_status"
    description = "Update the claim's workflow status and AI run status."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(
        self,
        *,
        claim_id: int,
        claim_status: ClaimStatus,
        ai_run_status: AIRunStatus,
        notes: str | None = None,
    ) -> ClaimWriteResult:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = ClaimRepository(session)
                claim = await repository.update_run_status(
                    claim_id,
                    claim_status=claim_status,
                    ai_run_status=ai_run_status,
                    notes=notes,
                )
                if claim is None:
                    raise AuditToolError(
                        f"Claim {claim_id} not found", code="claim_not_found"
                    )
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to update run status for claim {claim_id}: {exc}",
                code="update_status_failed",
            ) from exc
        return ClaimWriteResult(
            claim_id=claim_id, updated_fields=["status", "ai_run_status"]
        )


class UpdateClaimResultTool(AuditTool):
    """Persist the final AI decision, priority and notes onto the claim."""

    name = "update_claim_result"
    description = "Persist the AI recommendation, priority and notes onto the claim."

    def __init__(self, *, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def run(
        self,
        *,
        claim_id: int,
        ai_decision: AIDecision,
        priority: ClaimPriority,
        ai_run_status: AIRunStatus = AIRunStatus.COMPLETED,
        notes: str | None = None,
    ) -> ClaimWriteResult:
        try:
            async with transaction_session(self._session_factory) as session:
                repository = ClaimRepository(session)
                claim = await repository.update_result(
                    claim_id,
                    ai_decision=ai_decision,
                    priority=priority,
                    ai_run_status=ai_run_status,
                    notes=notes,
                )
                if claim is None:
                    raise AuditToolError(
                        f"Claim {claim_id} not found", code="claim_not_found"
                    )
        except AuditToolError:
            raise
        except Exception as exc:
            raise AuditToolError(
                f"Failed to persist audit result for claim {claim_id}: {exc}",
                code="update_result_failed",
            ) from exc
        return ClaimWriteResult(
            claim_id=claim_id,
            updated_fields=[
                "ai_decision",
                "priority",
                "ai_run_status",
                "auditer_notes",
            ],
        )