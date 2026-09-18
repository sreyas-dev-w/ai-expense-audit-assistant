from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.project import ProjectDetailsResponse
from app.services.project_service import ProjectService


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.get(
    "/{project_code}",
    response_model=ProjectDetailsResponse,
)
async def get_project_details(
    project_code: str,
    db: AsyncSession = Depends(get_db),
):
    return await ProjectService.get_project_details(
        db,
        project_code,
    )

