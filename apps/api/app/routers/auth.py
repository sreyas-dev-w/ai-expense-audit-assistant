from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.schemas.api import LoginRequest, LoginResponse, documented_errors
from app.services.api_store import USERS

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses=documented_errors(401, 403, 422),
)
def login(payload: LoginRequest):
    user = USERS.get(payload.username.lower())
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user["active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    public_user = {key: user[key] for key in ("user_id", "employee_id", "name", "role")}
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": public_user}
