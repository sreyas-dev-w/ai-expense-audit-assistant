from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.employees import Employee


class ProjectRepository:
    """
    Repository for project data fetched from Neon DB.
    """

    def __init__(self, session: AsyncSession = None):
        self.session = session

    async def get_project_by_code(self, project_code: str):
        """
        Fetch project details using project code.

        Also fetches the project lead's employee name
        using Project.project_lead_id -> Employee.employee_id.
        """

        if not self.session:
            return None

        query = (
            select(Project, Employee.employee_name)
            .outerjoin(
                Employee,
                Project.project_lead_id == Employee.employee_id,
            )
            .where(Project.project_code == project_code)
        )

        result = await self.session.execute(query)
        row = result.one_or_none()

        if not row:
            return None

        project, lead_name = row

        return {
            "project_code": project.project_code,
            "project_name": project.project_name,
            "account_id": project.account_id,
            "project_lead_id": project.project_lead_id,
            "lead_name": lead_name,
        }

