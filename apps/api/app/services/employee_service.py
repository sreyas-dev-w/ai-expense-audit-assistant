from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.employee_repository import EmployeeRepository


class EmployeeService:

    @staticmethod
    async def get_all_employees(
        db: AsyncSession,
    ):
        repository = EmployeeRepository(db)

        return await repository.get_all_employees()

    @staticmethod
    async def get_employee_details(
        db: AsyncSession,
        employee_id: str,
    ):
        repository = EmployeeRepository(db)

        employee_details = await repository.get_employee_details(
            employee_id
        )

        if employee_details is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{employee_id}' not found",
            )

        return employee_details
