from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/verify")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verify if the provided token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }
