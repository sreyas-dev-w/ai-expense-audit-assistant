"""Application service for the Audit Agent orchestrator.

Routers parse/validate and call this service. The LangGraph parent graph
invokes the three sub-agents; this layer owns DI, receipt bytes, and mapping
the envelope onto the HTTP response.
"""
from decimal import Decimal

from app.agents.audit_agent import run_audit_agent
from app.agents.ocr_agent import OCRAgent
from app.db.session import async_session_factory
from app.models.enums import ClaimStatus
from app.schemas.audit import (
    AuditAgentResult,
    AuditAgentStatus,
    AuditRequest,
    AuditResult,
    AuditRunResponse,
)
from app.services.gemini_client import GeminiClient
from app.services.rag_service import PolicyRagService
from app.services.validation_context_service import ValidationContextService
from app.tools.audit_tools import AuditPersistError, AuditTools, EmployeeNotFoundError
from app.core.exceptions import ClaimNotFoundError


class AuditNotFoundError(Exception):
    def __init__(self, claim_id: int):
        super().__init__(f"No audit result found for claim {claim_id}")
        self.claim_id = claim_id
        self.code = "audit_not_found"


class AuditService:
    def __init__(
        self,
        *,
        llm_client: GeminiClient,
        context_service: ValidationContextService | None = None,
        rag_service: PolicyRagService | None = None,
        session_factory=async_session_factory,
        ocr_agent: OCRAgent | None = None,
        run_ocr=None,
        run_validation=None,
        run_policy=None,
    ) -> None:
        self._llm_client = llm_client
        self._context_service = context_service or ValidationContextService(
            session_factory=session_factory
        )
        self._rag_service = rag_service
        self._session_factory = session_factory
        self._ocr_agent = ocr_agent or OCRAgent()
        self._run_ocr = run_ocr or self._ocr_agent.process
        self._run_validation = run_validation
        self._run_policy = run_policy

    async def run(
        self,
        *,
        claim_id: int,
        receipt_bytes: bytes | None = None,
        mime_type: str | None = None,
        persist: bool = True,
    ) -> AuditRunResponse:
        tools = AuditTools(session_factory=self._session_factory)
        result = await run_audit_agent(
            AuditRequest(claim_id=claim_id, persist=persist),
            tools=tools,
            run_ocr=self._run_ocr,
            run_validation=self._run_validation,
            run_policy=self._run_policy,
            llm_client=self._llm_client,
            receipt_bytes=receipt_bytes,
            mime_type=mime_type,
            context_service=self._context_service,
            rag_service=self._rag_service,
        )
        claim_status: ClaimStatus | None = None
        row = None
        if persist:
            try:
                claim, row = await tools.get_latest_for_claim(claim_id)
                claim_status = claim.status
            except ClaimNotFoundError:
                claim_status = None
        return _to_run_response(result, claim_status=claim_status, row=row)

    async def get_latest(self, claim_id: int) -> AuditRunResponse:
        tools = AuditTools(session_factory=self._session_factory)
        claim, row = await tools.get_latest_for_claim(claim_id)
        if row is None:
            raise AuditNotFoundError(claim_id)
        output = None
        if row.audit_response:
            output = AuditResult.model_validate(row.audit_response)
        result = AuditAgentResult(
            status=(
                AuditAgentStatus.SUCCESS
                if output is not None
                else AuditAgentStatus.ERROR
            ),
            output=output,
            error=None,
        )
        return _to_run_response(result, claim_status=claim.status, row=row)


def _to_run_response(
    result: AuditAgentResult,
    *,
    claim_status: ClaimStatus | None,
    row,
) -> AuditRunResponse:
    output = result.output
    confidence: Decimal | None = None
    if row is not None and row.confidence_score is not None:
        confidence = row.confidence_score
    elif output is not None:
        confidence = Decimal(str(round(output.confidence, 2)))
    return AuditRunResponse(
        status=result.status,
        output=output,
        error=result.error,
        agent_response_id=row.id if row is not None else None,
        claim_status=claim_status,
        validation_violation=(
            row.validation_violation
            if row is not None
            else (output.validation_violation if output else None)
        ),
        policy_violation=(
            row.policy_violation
            if row is not None
            else (output.policy_violation if output else None)
        ),
        notes=(
            row.notes if row is not None else (output.notes if output else None)
        ),
        confidence_score=confidence,
        validation_response=(
            row.validation_response if row is not None else None
        ),
        policy_response=row.policy_response if row is not None else None,
        audit_response=row.audit_response if row is not None else None,
    )
