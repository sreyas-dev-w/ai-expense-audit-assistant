"""Sign-in application service.

DEMO ONLY: ``employees.password`` is stored unhashed, so this compares the
submitted password directly. ``docs/backend/security.md`` forbids this pattern
for anything real -- swapping in a salted hash means changing only
``_password_matches`` and the column type.
"""
from __future__ import annotations

import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.employee import EmployeeProfile


class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Email or password is incorrect")
        self.code = "invalid_credentials"


def _password_matches(submitted: str, stored: str) -> bool:
    return hmac.compare_digest(submitted, stored or "")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._employees = EmployeeRepository(session)

    async def login(self, request: LoginRequest) -> LoginResponse:
        employee = await self._employees.get_by_email(request.email)
        if employee is None or not _password_matches(
            request.password, employee.password
        ):
            raise InvalidCredentialsError()

        token, ttl = create_access_token(employee.employee_id)
        return LoginResponse(
            access_token=token,
            expires_in=ttl,
            profile=EmployeeProfile.model_validate(employee),
        )
