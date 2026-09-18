from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.project_repository import ProjectRepository


class ProjectService:

    @staticmethod
    async def get_project_details(
        db: AsyncSession,
        project_code: str,
    ):
        repository = ProjectRepository(db)

        project = await repository.get_project_by_code(
            project_code
        )

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with code '{project_code}' not found",
            )

        return project

