from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ocr_employee_details import OCREmployeeDetailsRepository


class OCREmployeeDetailsService:

    def __init__(self, session: AsyncSession):
        self.repository = OCREmployeeDetailsRepository(session)

    async def get_employee_details(self, employee_id: str):
        """
        Fetch employee details with project and account information.
        Returns the same format as the hardcoded version for backward compatibility.
        """
        employee = await self.repository.get_employee(employee_id)

        if employee is None:
            return None

        # Fetch project details if employee has a project
        project = None
        if employee.get("project_code"):
            project = await self.repository.get_project(employee["project_code"])

        # Fetch account details if project has an account
        account = None
        account_id = None
        if project:
            account_id = project.get("account_id")
            if account_id:
                account = await self.repository.get_account(account_id)

        return {
            "employee_id": employee["employee_id"],
            "employee_name": employee["employee_name"],
            "job_level": employee["job_level"],
            "manager_id": employee["manager_id"],
            "project_code": employee["project_code"],
            "account_id": account_id,
        }
