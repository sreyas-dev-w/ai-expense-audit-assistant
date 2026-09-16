"""Serves stored receipt files back to the people allowed to see them.

Receipts are sensitive business data (``docs/backend/security.md``), so a file
is only streamed when it belongs to a claim the caller owns or manages.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_employee
from app.db.session import get_db_session
from app.models.employees import Employee
from app.services.claim_service import ClaimService
from app.services.file_service import resolve_stored_receipt

router = APIRouter(prefix="/uploads", tags=["uploads"])

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


@router.get(
    "/receipts/{stored_name}",
    summary="Download the receipt attached to a claim you own or manage",
    response_class=FileResponse,
)
async def get_receipt(
    stored_name: str,
    employee: Employee = Depends(get_current_employee),
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    path = resolve_stored_receipt(stored_name)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    claim = await ClaimService(session).resolve_receipt_claim(
        employee=employee, stored_name=stored_name
    )
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this receipt",
        )

    return FileResponse(
        path,
        media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
        filename=stored_name,
    )
