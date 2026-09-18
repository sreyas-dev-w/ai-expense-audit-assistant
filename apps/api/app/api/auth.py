from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import AuthRequest, AuthResponse
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate employee",
)
async def login(
    auth_data: AuthRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService.authenticate(
        db=db,
        auth_data=auth_data,
    )