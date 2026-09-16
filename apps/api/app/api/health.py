from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.api import HealthResponse

router = APIRouter()


@router.get("/health", tags=["Health"], response_model=HealthResponse)
def health_check() -> dict[str, str]:
    """Health endpoint. The in-memory development store is always available."""
    return {
        "status": "healthy",
        "api": "up",
        "mysql": "not_configured",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
