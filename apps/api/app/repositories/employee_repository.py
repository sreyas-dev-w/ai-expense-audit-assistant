from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.employees import Employee
from app.models.projects import Project
from app.models.accounts import Account


class EmployeeRepository:
    """
    Repository for employee data fetched from Neon DB.
    Replaces the hardcoded test data with live database queries.
    """

    def __init__(self, session: AsyncSession = None):
        self.session = session

    async def get_employee(self, employee_id: str):
        """
        Fetch employee from database.
        Returns a dictionary with employee details.
        """
        if not self.session:
            return None

        query = select(Employee).where(Employee.employee_id == employee_id)
        result = await self.session.execute(query)
        employee = result.scalar_one_or_none()

        if not employee:
            return None

        return {
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "job_level": employee.job_level.value,
            "is_manager": employee.is_manager,
            "manager_id": employee.manager_id,
            "project_code": employee.project_code,
        }

    async def get_manager(self, manager_id: str):
        """Fetch the manager row; same shape as ``get_employee``."""
        return await self.get_employee(manager_id)

    async def get_employee_model(self, employee_id: str) -> Employee | None:
        """Fetch the ORM row itself, for callers that need the whole entity."""
        if not self.session:
            return None
        return await self.session.get(Employee, employee_id)

    async def get_by_email(self, email: str) -> Employee | None:
        """Look up the login identity. Emails are stored and matched lowercase."""
        if not self.session:
            return None
        query = select(Employee).where(Employee.email == email.strip().lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_report_ids(self, manager_id: str) -> list[str]:
        """Employee ids that report directly to ``manager_id``."""
        if not self.session:
            return []
        query = select(Employee.employee_id).where(
            Employee.manager_id == manager_id
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_project(self, project_code: str):
        """
        Fetch project from database.
        Returns a dictionary with project details.
        """
        if not self.session:
            return None

        query = select(Project).where(Project.project_code == project_code)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            return None

        return {
            "project_code": project.project_code,
            "project_name": project.project_name,
            "account_id": project.account_id,
            "project_lead_id": project.project_lead_id,
        }

    async def get_account(self, account_id: str):
        """
        Fetch account from database.
        Returns a dictionary with account details.
        """
        if not self.session:
            return None

        query = select(Account).where(Account.account_id == account_id)
        result = await self.session.execute(query)
        account = result.scalar_one_or_none()

        if not account:
            return None

        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "fiscal_year": account.fiscal_year,
            "budget_allocated": float(account.budget_allocated),
            "remaining_budget": float(account.remaining_budget),
            "currency": account.currency.value,
        }
