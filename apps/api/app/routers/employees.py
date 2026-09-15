from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Employee
from app.schemas import EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])

db_session = Annotated[AsyncSession, Depends(get_db)]


async def _resolve_employee(
    session: AsyncSession, employee_id: str
) -> tuple[Employee, bool]:
    employee = (
        await session.execute(
            select(Employee).where(Employee.employee_id == employee_id)
        )
    ).scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    is_manager = (
        await session.execute(
            select(Employee.employee_id).where(
                Employee.manager_id == employee_id
            )
        )
    ).first() is not None

    return employee, is_manager


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(session: db_session) -> list[EmployeeResponse]:
    rows = (await session.execute(select(Employee))).scalars().all()
    manager_ids = {
        emp.manager_id
        for emp in rows
        if emp.manager_id is not None
    }
    return [
        EmployeeResponse(
            employee_id=emp.employee_id,
            employee_name=emp.employee_name,
            job_level=emp.job_level,
            manager_id=emp.manager_id,
            project_code=emp.project_code,
            is_manager=emp.employee_id in manager_ids,
        )
        for emp in sorted(rows, key=lambda e: e.employee_id)
    ]


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, session: db_session) -> EmployeeResponse:
    employee, is_manager = await _resolve_employee(session, employee_id)
    return EmployeeResponse(
        employee_id=employee.employee_id,
        employee_name=employee.employee_name,
        job_level=employee.job_level,
        manager_id=employee.manager_id,
        project_code=employee.project_code,
        is_manager=is_manager,
    )


@router.get("/{employee_id}/is-manager")
async def is_manager(employee_id: str, session: db_session) -> dict[str, bool]:
    _, manager = await _resolve_employee(session, employee_id)
    return {"is_manager": manager}