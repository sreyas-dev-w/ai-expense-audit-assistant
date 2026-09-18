from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobLevel, Currency


# ============================================================
# API 1: General employee details
# GET /employees
# ============================================================

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_name: str
    job_level: JobLevel
    is_manager: bool
    manager_id: str | None
    project_code: str | None
    username: str | None


# ============================================================
# API 2: Detailed employee information
# GET /employees/{employee_id}/details
# ============================================================

class EmployeeDetailsEmployee(BaseModel):
    employee_id: str
    employee_name: str
    job_level: str
    manager_id: str | None
    project_code: str | None


class EmployeeDetailsProject(BaseModel):
    project_code: str
    project_name: str
    account_id: str
    project_lead_id: str | None


class EmployeeDetailsAccount(BaseModel):
    account_id: str
    account_name: str
    fiscal_year: int
    budget_allocated: Decimal
    remaining_budget: Decimal
    currency: str


class EmployeeDetailsResponse(BaseModel):
    employee: EmployeeDetailsEmployee
    project: EmployeeDetailsProject | None
    account: EmployeeDetailsAccount | None

