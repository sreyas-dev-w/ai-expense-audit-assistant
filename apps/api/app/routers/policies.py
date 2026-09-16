import hashlib
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.security import require_roles
from app.schemas.api import PolicyUploadResponse, documented_errors
from app.services.api_store import identifier, policies, policy_numbers

router = APIRouter(prefix="/policies", tags=["Policies"])
POLICY_DIR = Path("storage/policies")
MAX_POLICY_BYTES = 20 * 1024 * 1024


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PolicyUploadResponse,
    responses=documented_errors(401, 403, 409, 413, 415, 422),
)
async def upload_policy(
    file: UploadFile = File(...),
    policy_name: str = Form(...),
    policy_version: str = Form(...),
    effective_from: date = Form(...),
    country: str = Form(...),
    _: dict = Depends(require_roles("ADMIN")),
):
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Policy file must be a PDF")
    if any(item["policy_version"] == policy_version for item in policies.values()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Policy version already exists")
    contents = await file.read()
    if len(contents) > MAX_POLICY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Policy file exceeds 20 MB limit",
        )
    policy_id = identifier("POL", policy_numbers)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "policy.pdf")
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    path = POLICY_DIR / f"{policy_id}_{safe_name}"
    path.write_bytes(contents)
    policies[policy_id] = {
        "policy_id": policy_id,
        "policy_name": policy_name,
        "policy_version": policy_version,
        "effective_from": str(effective_from),
        "country": country.strip(),
        "active": True,
        "storage_path": str(path).replace("\\", "/"),
        "sha256_hash": hashlib.sha256(contents).hexdigest(),
        "indexing_status": "READY",
    }
    return {
        "policy_id": policy_id,
        "policy_version": policy_version,
        "indexing_status": "READY",
        "message": "Policy uploaded and indexed successfully.",
    }
