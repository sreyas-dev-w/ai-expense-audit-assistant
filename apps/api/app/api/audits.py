"""Audit workflow endpoints.

Routing-only: handlers parse/validate and delegate to the AuditService
(``docs/backend/api-design.md``); all agent/business logic lives below the API
layer. The AuditResult returned here is the meaningful, decision-support result
produced by the Audit Agent graph.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_audit_service
from app.schemas.audit import AuditResult
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post(
    "/{claim_id}/run",
    response_model=AuditResult,
    summary="Run the AI audit workflow for a claim",
)
async def run_audit(
    claim_id: int,
    service: AuditService = Depends(get_audit_service),
) -> AuditResult:
    try:
        return await service.run_audit(claim_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audit run failed: {exc}",
        ) from exc