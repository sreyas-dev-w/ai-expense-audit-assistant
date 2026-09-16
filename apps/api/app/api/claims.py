"""Expense claim HTTP surface.

Routing-only: handlers parse/validate and delegate to ``ClaimService``
(``docs/backend/api-design.md``).

Creation is multipart because the receipt travels with the claim. The claim
itself is sent as a JSON string in the ``payload`` field so the discriminated
``ClaimCreate`` union in ``app/schemas/claim.py`` still validates it -- form
fields alone cannot express a per-category ``category_data`` shape.
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClaimNotFoundError
from app.core.security import get_current_employee, require_manager
from app.db.session import get_db_session
from app.models.employees import Employee
from app.schemas.claim import ClaimDecisionRequest, ClaimListItem, ClaimRead
from app.services.claim_service import (
    ClaimAccessError,
    ClaimAlreadyDecidedError,
    ClaimPayloadError,
    ClaimService,
)

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post(
    "",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
    summary="File an expense claim, optionally with its receipt",
)
async def create_claim(
    payload: str = Form(..., description="Claim JSON matching ClaimCreate"),
    receipt: UploadFile | None = File(None),
    employee: Employee = Depends(get_current_employee),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    receipt_bytes = await receipt.read() if receipt is not None else None
    try:
        return await ClaimService(session).create(
            employee=employee,
            payload=payload,
            receipt_filename=receipt.filename if receipt is not None else None,
            receipt_bytes=receipt_bytes or None,
        )
    except ClaimPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except ClaimAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get(
    "",
    response_model=list[ClaimListItem],
    summary="Claims filed by the signed-in employee, or by their direct reports",
)
async def list_claims(
    scope: Literal["mine", "team"] = "mine",
    employee: Employee = Depends(get_current_employee),
    session: AsyncSession = Depends(get_db_session),
) -> list[ClaimListItem]:
    try:
        return await ClaimService(session).list_for(employee=employee, scope=scope)
    except ClaimAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get(
    "/{claim_id}",
    response_model=ClaimRead,
    summary="A single claim, visible to its owner and their manager",
)
async def get_claim(
    claim_id: int,
    employee: Employee = Depends(get_current_employee),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await ClaimService(session).get(employee=employee, claim_id=claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ClaimAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.post(
    "/{claim_id}/decision",
    response_model=ClaimRead,
    summary="Approve or reject a direct report's claim",
)
async def decide_claim(
    claim_id: int,
    request: ClaimDecisionRequest,
    manager: Employee = Depends(require_manager),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await ClaimService(session).decide(
            manager=manager, claim_id=claim_id, request=request
        )
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ClaimAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except ClaimAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
