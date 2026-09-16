"""Authentication HTTP surface.

Routing-only: handlers parse/validate and delegate to ``AuthService``
(``docs/backend/api-design.md``).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_employee
from app.db.session import get_db_session
from app.models.employees import Employee
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.employee import EmployeeProfile
from app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Exchange employee credentials for a session token",
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    try:
        return await AuthService(session).login(request)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@router.get(
    "/me",
    response_model=EmployeeProfile,
    summary="Profile of the signed-in employee",
)
async def read_current_employee(
    employee: Employee = Depends(get_current_employee),
) -> EmployeeProfile:
    return EmployeeProfile.model_validate(employee)
