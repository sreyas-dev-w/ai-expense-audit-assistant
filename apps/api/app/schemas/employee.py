"""Employee API contracts.

The ORM model is never exposed directly (``docs/backend/api-design.md``);
``EmployeeProfile`` is the public shape and deliberately omits ``password``.
"""
from pydantic import BaseModel, ConfigDict

from app.models.enums import JobLevel


class EmployeeProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_name: str
    email: str
    job_level: JobLevel
    is_manager: bool
    manager_id: str | None = None
    project_code: str | None = None
