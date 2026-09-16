import hashlib
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.security import current_user
from app.schemas.api import (
    DocumentType,
    DocumentUploadResponse,
    documented_errors,
)
from app.services.api_store import document_numbers, documents, identifier

router = APIRouter(prefix="/uploads", tags=["Documents"])
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_BYTES = 10 * 1024 * 1024
UPLOAD_DIR = Path("storage/uploads")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
    responses=documented_errors(401, 413, 415, 422),
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    user: dict = Depends(current_user),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF, JPG, JPEG, and PNG files are supported")
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit")
    document_id = identifier("DOC", document_numbers)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOAD_DIR / f"{document_id}_{safe_name}"
    stored_path.write_bytes(contents)
    record = {"document_id": document_id, "document_type": document_type.value, "original_filename": file.filename, "storage_path": str(stored_path).replace("\\", "/"), "sha256_hash": hashlib.sha256(contents).hexdigest(), "owner_id": user["sub"], "upload_status": "UPLOADED"}
    documents[document_id] = record
    return {key: record[key] for key in ("document_id", "document_type", "original_filename", "storage_path", "sha256_hash", "upload_status")}
