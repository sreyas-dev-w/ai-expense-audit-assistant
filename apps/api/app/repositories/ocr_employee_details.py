from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.employees import Employee
from app.models.projects import Project
from app.models.accounts import Account


class OCREmployeeDetailsRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_employee(self, employee_id: str):
        """Fetch employee from database"""
        query = select(Employee).where(Employee.employee_id == employee_id)
        result = await self.session.execute(query)
        employee = result.scalar_one_or_none()

        if not employee:
            return None

        return {
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "job_level": employee.job_level.value,
            "manager_id": employee.manager_id,
            "project_code": employee.project_code,
        }

    async def get_project(self, project_code: str):
        """Fetch project from database"""
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
        """Fetch account from database"""
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
