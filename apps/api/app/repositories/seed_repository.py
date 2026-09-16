"""Persistence helpers for the one-time CSV seed load."""
from collections.abc import Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import Account
from app.models.agent_response import AgentResponse
from app.models.claims import Claim
from app.models.employees import Employee
from app.models.projects import Project
from app.schemas.seed import (
    AccountSeedRow,
    EmployeeSeedRow,
    ProjectSeedRow,
    SeedTableCounts,
)


class SeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_rows(self) -> SeedTableCounts:
        accounts = (
            await self._session.execute(select(func.count()).select_from(Account))
        ).scalar_one()
        projects = (
            await self._session.execute(select(func.count()).select_from(Project))
        ).scalar_one()
        employees = (
            await self._session.execute(select(func.count()).select_from(Employee))
        ).scalar_one()
        return SeedTableCounts(
            accounts=int(accounts),
            projects=int(projects),
            employees=int(employees),
        )

    async def delete_seed_graph(self) -> None:
        """Delete seed tables in FK-safe order (claims cascade from employees)."""
        await self._session.execute(delete(AgentResponse))
        await self._session.execute(delete(Claim))
        await self._session.execute(update(Project).values(project_lead_id=None))
        await self._session.execute(
            update(Employee).values(manager_id=None, project_code=None)
        )
        await self._session.execute(delete(Employee))
        await self._session.execute(delete(Project))
        await self._session.execute(delete(Account))

    async def insert_accounts(self, rows: Sequence[AccountSeedRow]) -> None:
        for row in rows:
            self._session.add(
                Account(
                    account_id=row.account_id,
                    account_name=row.account_name,
                    fiscal_year=row.fiscal_year,
                    budget_allocated=row.budget_allocated,
                    remaining_budget=row.remaining_budget,
                    currency=row.currency,
                )
            )
        await self._session.flush()

    async def insert_projects_without_leads(
        self, rows: Sequence[ProjectSeedRow]
    ) -> None:
        for row in rows:
            self._session.add(
                Project(
                    project_code=row.project_code,
                    project_name=row.project_name,
                    account_id=row.account_id,
                    project_lead_id=None,
                )
            )
        await self._session.flush()

    async def insert_employees_without_managers(
        self, rows: Sequence[EmployeeSeedRow]
    ) -> None:
        for row in rows:
            self._session.add(
                Employee(
                    employee_id=row.employee_id,
                    employee_name=row.employee_name,
                    job_level=row.job_level,
                    is_manager=row.is_manager,
                    manager_id=None,
                    project_code=row.project_code,
                )
            )
        await self._session.flush()

    async def update_employee_managers(
        self, rows: Sequence[EmployeeSeedRow]
    ) -> None:
        for row in rows:
            if not row.manager_id:
                continue
            await self._session.execute(
                update(Employee)
                .where(Employee.employee_id == row.employee_id)
                .values(manager_id=row.manager_id)
            )
        await self._session.flush()

    async def update_project_leads(self, rows: Sequence[ProjectSeedRow]) -> None:
        for row in rows:
            if not row.project_lead_id:
                continue
            await self._session.execute(
                update(Project)
                .where(Project.project_code == row.project_code)
                .values(project_lead_id=row.project_lead_id)
            )
        await self._session.flush()
