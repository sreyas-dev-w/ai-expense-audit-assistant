"""Validation Agent HTTP surface.

Routing-only: handlers parse/validate and delegate to ``ValidationService``
(``docs/backend/api-design.md``).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_validation_service
from app.core.exceptions import ClaimNotFoundError
from app.schemas.validation import ValidationEvaluateResponse, ValidationRequest
from app.services.validation_service import (
    ValidationPersistError,
    ValidationService,
)

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post(
    "/evaluate",
    response_model=ValidationEvaluateResponse,
    summary="Run the Validation Agent against an OCR envelope",
)
async def evaluate_claim(
    request: ValidationRequest,
    service: ValidationService = Depends(get_validation_service),
) -> ValidationEvaluateResponse:
    try:
        return await service.evaluate(request)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValidationPersistError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
