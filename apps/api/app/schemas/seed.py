"""Structured contracts for the one-time CSV → Postgres seed load."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Currency, JobLevel


class AccountSeedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    account_name: str
    fiscal_year: int
    budget_allocated: Decimal
    remaining_budget: Decimal
    currency: Currency


class ProjectSeedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_code: str
    project_name: str
    account_id: str
    project_lead_id: str | None = None


class EmployeeSeedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    employee_name: str
    job_level: JobLevel
    manager_id: str | None = None
    project_code: str | None = None
    is_manager: bool = False


class SeedTableCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    accounts: int
    projects: int
    employees: int

    @property
    def any_populated(self) -> bool:
        return self.accounts > 0 or self.projects > 0 or self.employees > 0


class IgnoredCsvColumns(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: str
    columns: list[str] = Field(default_factory=list)


class SeedLoadReport(BaseModel):
    """Inserted / skipped counts plus extra CSV headers that were dropped."""

    model_config = ConfigDict(frozen=True)

    dry_run: bool
    forced: bool
    inserted: SeedTableCounts
    skipped: SeedTableCounts
    ignored_columns: list[IgnoredCsvColumns]
    is_manager_count: int = 0
