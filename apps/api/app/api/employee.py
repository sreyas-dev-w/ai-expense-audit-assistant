from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.employee import (
    EmployeeResponse,
    EmployeeDetailsResponse,
)
from app.services.employee_service import EmployeeService


router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


# ============================================================
# API 1: Fetch all employees - General details only
# ============================================================

@router.get(
    "",
    response_model=list[EmployeeResponse],
)
async def get_all_employees(
    db: AsyncSession = Depends(get_db),
):
    return await EmployeeService.get_all_employees(db)


# ============================================================
# API 2: Fetch employee details by employee ID
# Includes Employee + Project + Account information
# ============================================================

@router.get(
    "/{employee_id}/details",
    response_model=EmployeeDetailsResponse,
)
async def get_employee_details(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await EmployeeService.get_employee_details(
        db,
        employee_id,
    )

