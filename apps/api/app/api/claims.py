"""Claim submission endpoint.

Routing-only: parses the multipart form (claim JSON + receipt file), delegates
the persistence work to ``ClaimSubmissionService`` and schedules the Audit
Agent to run in the background once the claim is committed. The response is
returned immediately after the insert — the agent fetches/updates claim data on
its own (``docs/backend/api-design.md``, ``docs/backend/reliability.md``).
"""
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import TypeAdapter, ValidationError

from app.core.dependencies import get_claim_submission_service
from app.schemas.claim import ClaimCreate, ClaimSubmissionResponse
from app.services.claim_service import (
    ClaimSubmissionError,
    ClaimSubmissionService,
    EmployeeNotFoundError,
)

router = APIRouter(prefix="/claims", tags=["claims"])

_claim_create_adapter = TypeAdapter(ClaimCreate)


@router.post(
    "",
    response_model=ClaimSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an expense claim and trigger the AI audit in the background",
)
async def submit_claim(
    claim_json: str = Form(...),
    receipt: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks,
    service: ClaimSubmissionService = Depends(get_claim_submission_service),
) -> ClaimSubmissionResponse:
    try:
        claim = _claim_create_adapter.validate_json(claim_json)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(include_url=False),
        ) from exc

    content = await receipt.read()
    try:
        submission = await service.submit_claim(
            claim=claim,
            receipt_filename=receipt.filename or "receipt",
            receipt_content=content,
            receipt_mime_type=receipt.content_type,
        )
    except EmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ClaimSubmissionError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc

    background_tasks.add_task(service.run_audit_background, submission.claim_id)
    return submission