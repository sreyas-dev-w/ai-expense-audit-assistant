from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.health import HealthLiveResponse, HealthReadyResponse
from app.services.health_service import DatabaseUnavailableError, HealthService

router = APIRouter()


def get_health_service() -> HealthService:
    return HealthService()


@router.get("/health", response_model=HealthLiveResponse)
def health_check() -> HealthLiveResponse:
    return HealthLiveResponse(status="ok")


@router.get("/health/ready", response_model=HealthReadyResponse)
async def readiness_check(
    service: HealthService = Depends(get_health_service),
) -> HealthReadyResponse:
    try:
        return await service.check_readiness()
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unavailable"},
        ) from exc
