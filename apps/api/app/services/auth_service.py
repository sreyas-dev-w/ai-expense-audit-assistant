from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.employee_repository import EmployeeRepository
from app.schemas.auth import AuthRequest, AuthResponse


class AuthService:

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        auth_data: AuthRequest,
    ) -> AuthResponse:

        employee_repository = EmployeeRepository(db)

        employee = await employee_repository.get_by_username(
            auth_data.username
        )

        if employee is None:
            return AuthResponse(
                authenticated=False,
                employee_id=None,
            )

        if employee.password != auth_data.password:
            return AuthResponse(
                authenticated=False,
                employee_id=None,
            )

        return AuthResponse(
            authenticated=True,
            employee_id=employee.employee_id,
        )