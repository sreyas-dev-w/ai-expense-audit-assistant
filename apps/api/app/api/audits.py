"""Audit Agent HTTP surface.

Routing-only: handlers parse/validate and delegate to ``AuditService``
(``docs/backend/api-design.md``).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.dependencies import get_audit_service
from app.schemas.audit import AuditRunResponse
from app.services.audit_service import AuditNotFoundError, AuditService
from app.services.validation_service import ClaimNotFoundError
from app.tools.audit_tools import AuditPersistError, EmployeeNotFoundError

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post(
    "",
    response_model=AuditRunResponse,
    summary="Run the Audit Agent workflow for an existing claim",
)
async def run_audit(
    claim_id: int = Form(...),
    persist: bool = Form(True),
    receipt: UploadFile | None = File(None),
    service: AuditService = Depends(get_audit_service),
) -> AuditRunResponse:
    receipt_bytes: bytes | None = None
    mime_type: str | None = None
    if receipt is not None:
        receipt_bytes = await receipt.read()
        mime_type = receipt.content_type
        if not receipt_bytes:
            receipt_bytes = None
    try:
        return await service.run(
            claim_id=claim_id,
            receipt_bytes=receipt_bytes,
            mime_type=mime_type,
            persist=persist,
        )
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except AuditPersistError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get(
    "/{claim_id}",
    response_model=AuditRunResponse,
    summary="Latest audit result for a claim, including approver-facing fields",
)
async def get_audit(
    claim_id: int,
    service: AuditService = Depends(get_audit_service),
) -> AuditRunResponse:
    try:
        return await service.get_latest(claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AuditNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
