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
            "manager_id": employee.manager_id,
            "project_code": employee.project_code,
        }

    
    async def get_by_username(
        self,
        username: str,
    ) -> Employee | None:
        result = await self.session.execute(
            select(Employee).where(
                Employee.username == username
            )
        )

        return result.scalar_one_or_none()

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

    # ============================================================
    # NEW METHOD 1: Fetch all employees
    # ============================================================

    async def get_all_employees(self):
        """
        Fetch all employees from the database.

        Returns only general employee information.
        Password is intentionally not returned.
        """
        if not self.session:
            return []

        query = select(Employee)
        result = await self.session.execute(query)
        employees = result.scalars().all()

        return [
            {
                "employee_id": employee.employee_id,
                "employee_name": employee.employee_name,
                "job_level": employee.job_level.value,
                "is_manager": employee.is_manager,
                "manager_id": employee.manager_id,
                "project_code": employee.project_code,
                "username": employee.username,
            }
            for employee in employees
        ]

    # ============================================================
    # NEW METHOD 2: Fetch employee + project + account details
    # ============================================================

    async def get_employee_details(self, employee_id: str):
        """
        Fetch detailed employee information.

        Flow:
            Employee
                ↓
            Project
                ↓
            Account

        Returns combined employee, project and account details.
        """

        if not self.session:
            return None

        # --------------------------------------------------------
        # Step 1: Get employee
        # --------------------------------------------------------

        employee = await self.get_employee(employee_id)

        if not employee:
            return None

        # --------------------------------------------------------
        # Step 2: Get project using employee's project_code
        # --------------------------------------------------------

        project = None
        account = None

        project_code = employee.get("project_code")

        if project_code:
            project = await self.get_project(project_code)

            # ----------------------------------------------------
            # Step 3: Get account using project's account_id
            # ----------------------------------------------------

            if project:
                account_id = project.get("account_id")

                if account_id:
                    account = await self.get_account(account_id)

        # --------------------------------------------------------
        # Step 4: Return combined response
        # --------------------------------------------------------

        return {
            "employee": employee,
            "project": project,
            "account": account,
        }

