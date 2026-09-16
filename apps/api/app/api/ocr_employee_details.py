from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ocr_employee_details import OCREmployeeDetailsService


class OCREmployeeDetailsAPI:
    """
    API layer for OCR employee details.
    Provides methods for the OCR agent to fetch employee information from Neon DB.
    """

    def __init__(self, session: AsyncSession):
        self.service = OCREmployeeDetailsService(session)

    async def get_employee(self, employee_id: str):
        """
        Get employee details from database.
        Returns a dictionary with:
        - employee_id
        - employee_name
        - job_level
        - manager_id
        - project_code
        - account_id (from associated project)
        """
        return await self.service.get_employee_details(employee_id)

    async def get_project(self, project_code: str):
        """
        Get project details from database.
        Returns a dictionary with project information.
        """
        return await self.service.repository.get_project(project_code)

    async def get_account(self, account_id: str):
        """
        Get account details from database.
        Returns a dictionary with account information.
        """
        return await self.service.repository.get_account(account_id)
