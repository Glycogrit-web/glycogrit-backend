"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.schemas.user import UserUpdate, UserDetailResponse, PasswordChange
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user

    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **city**: Optional city
    - **state**: Optional state
    """
    service = UserService(db)
    result = service.register_user(
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        city=user_data.city,
        state=user_data.state
    )
    return result


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password

    - **email**: Registered email address
    - **password**: User's password
    """
    service = UserService(db)
    result = service.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )
    return result


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information

    Requires: Bearer token in Authorization header
    """
    return current_user


@router.put("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile

    - **user_id**: ID of the user to update
    - Only the user themselves can update their profile

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)
    update_dict = user_data.model_dump(exclude_unset=True)
    updated_user = service.update_user(user_id, update_dict, current_user.id)
    return updated_user


@router.post("/users/{user_id}/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    user_id: int,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password

    - **user_id**: ID of the user
    - **current_password**: Current password for verification
    - **new_password**: New password (minimum 8 characters)
    - Only the user themselves can change their password

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)
    service.change_password(
        user_id=user_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        current_user_id=current_user.id
    )
    return {"message": "Password changed successfully"}


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account (soft delete - deactivates the account)

    - **user_id**: ID of the user to delete
    - Only the user themselves can delete their account

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)
    service.delete_user(user_id, current_user.id)
    return {"message": "User account deleted successfully"}
