"""Serving of stored claim receipts.

``claims.receipt_url`` holds a path relative to the app root (e.g.
``storage_dump/receipts/…``). This router exposes those files read-only so the
frontend can render receipt previews. Path resolution is delegated to
``file_service.resolve_receipt_path``, which confines serving to the receipt
storage directory.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.file_service import resolve_receipt_path

router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])


@router.get("/{receipt_path:path}")
def get_receipt(receipt_path: str) -> FileResponse:
    try:
        target = resolve_receipt_path(receipt_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Receipt not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(target)