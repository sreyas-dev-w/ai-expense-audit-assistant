"""Database readiness checks. SQL lives in the health repository."""
from app.db.session import async_session_factory
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthReadyResponse


class DatabaseUnavailableError(RuntimeError):
    """Postgres did not respond to a readiness ping."""


class HealthService:
    def __init__(self, session_factory=async_session_factory) -> None:
        self._session_factory = session_factory

    async def check_readiness(self) -> HealthReadyResponse:
        try:
            async with self._session_factory() as session:
                await HealthRepository(session).ping()
        except Exception as exc:
            raise DatabaseUnavailableError("database unavailable") from exc
        return HealthReadyResponse(status="ok", database="ok")
