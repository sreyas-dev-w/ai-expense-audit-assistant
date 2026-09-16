"""Authentication contracts for the employee-facing sign-in flow."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.employee import EmployeeProfile


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    profile: EmployeeProfile
