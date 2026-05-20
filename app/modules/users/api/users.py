"""
User Profile Management API Endpoints - DDD Module

Provides user profile management functionality:
- Profile updates
- Password management
- Email/Phone connection/disconnection
- Account deactivation
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
from app.models.user import User
from app.modules.users.schemas.user import (
    UserDetailResponse,
    UserUpdate,
    PasswordChange,
)
from app.modules.users.schemas.auth import (
    ConnectEmail,
    ConnectPhone,
    SetPasswordForOAuth,
)
from app.modules.users.services.user_service import UserService
from app.modules.users.services.commands import (
    UpdateProfileCommand,
    ChangePasswordCommand,
    SetPasswordCommand,
    ConnectEmailCommand,
    DisconnectEmailCommand,
    ConnectPhoneCommand,
    DisconnectPhoneCommand,
    DeactivateUserCommand,
)
from app.modules.users.services.queries import GetUserByIdQuery

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


@router.get("/{user_id}", response_model=UserDetailResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_user(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Get user profile by ID.

    Returns detailed user information. Users can view their own profile,
    admins can view any profile.

    Rate Limit: 100 requests per minute per user

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)

    # Create query
    query = GetUserByIdQuery(user_id=user_id)

    # Execute query
    user = service.handle_get_user_by_id(query)

    # Check permissions (users can only view their own profile, unless admin)
    if user.id != current_user.id and not current_user.is_admin:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException("You can only view your own profile")

    return user


@router.put("/{user_id}", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_user(
    request: Request,
    response: Response,
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Update user profile information.

    Allows users to update their own profile data.

    Rate Limit: 30 requests per minute per user

    Authorization: Only the user themselves can update their profile

    Requires: Bearer token in Authorization header

    Example:
        ```json
        {
          "first_name": "John",
          "last_name": "Doe",
          "city": "Mumbai",
          "state": "Maharashtra",
          "postal_code": "400001"
        }
        ```
    """
    service = UserService(db)

    # Build update data from request
    update_dict = user_data.model_dump(exclude_unset=True)

    # Create command
    command = UpdateProfileCommand(
        user_id=user_id,
        current_user_id=current_user.id,
        **update_dict
    )

    # Execute command
    updated_user = service.handle_update_profile(command)

    return updated_user


@router.post("/{user_id}/change-password", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.AUTH)
async def change_password(
    request: Request,
    response: Response,
    user_id: int,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Change user password.

    Updates the user's password after verifying the current password.

    Rate Limit: 5 requests per minute per user

    Authorization: Only the user themselves can change their password

    Requires: Bearer token in Authorization header

    Example:
        ```json
        {
          "current_password": "OldPass123!",
          "new_password": "NewSecurePass456!"
        }
        ```
    """
    service = UserService(db)

    # Create command
    command = ChangePasswordCommand(
        user_id=user_id,
        current_user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

    # Execute command
    service.handle_change_password(command)

    return {"message": "Password changed successfully"}


@router.post("/{user_id}/set-password", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.AUTH)
async def set_password_for_oauth_user(
    request: Request,
    response: Response,
    user_id: int,
    password_data: SetPasswordForOAuth,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Set password for OAuth users to enable password-based login.

    Allows OAuth users (Google login) to set a password and phone number.

    Rate Limit: 5 requests per minute per user

    Authorization: Only the user themselves can set their password

    Requires: Bearer token in Authorization header

    Example:
        ```json
        {
          "phone": "9876543210",
          "password": "SecurePass123!"
        }
        ```
    """
    service = UserService(db)

    # Create command
    command = SetPasswordCommand(
        user_id=user_id,
        current_user_id=current_user.id,
        phone=password_data.phone,
        password=password_data.password
    )

    # Execute command
    service.handle_set_password(command)

    return {"message": "Password set successfully. You can now login with phone and password."}


@router.post("/{user_id}/connect-email", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def connect_email(
    request: Request,
    response: Response,
    user_id: int,
    email_data: ConnectEmail,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Connect email address to user account.

    Allows phone-only users to add an email address.

    Rate Limit: 30 requests per minute per user

    Authorization: Only the user themselves can connect their email

    Requires: Bearer token in Authorization header

    Example:
        ```json
        {
          "email": "user@example.com"
        }
        ```
    """
    service = UserService(db)

    # Create command
    command = ConnectEmailCommand(
        user_id=user_id,
        current_user_id=current_user.id,
        email=email_data.email
    )

    # Execute command
    updated_user = service.handle_connect_email(command)

    return updated_user


@router.delete("/{user_id}/disconnect-email", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def disconnect_email(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Disconnect email from user account.

    Removes email from account. Requires phone as alternative identifier.
    Cannot disconnect OAuth email.

    Rate Limit: 30 requests per minute per user

    Authorization: Only the user themselves can disconnect their email

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)

    # Create command
    command = DisconnectEmailCommand(
        user_id=user_id,
        current_user_id=current_user.id
    )

    # Execute command
    updated_user = service.handle_disconnect_email(command)

    return updated_user


@router.post("/{user_id}/connect-phone", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def connect_phone(
    request: Request,
    response: Response,
    user_id: int,
    phone_data: ConnectPhone,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Connect phone number to user account.

    Allows email-only users to add a phone number.

    Rate Limit: 30 requests per minute per user

    Authorization: Only the user themselves can connect their phone

    Requires: Bearer token in Authorization header

    Example:
        ```json
        {
          "phone": "9876543210"
        }
        ```
    """
    service = UserService(db)

    # Create command
    command = ConnectPhoneCommand(
        user_id=user_id,
        current_user_id=current_user.id,
        phone=phone_data.phone
    )

    # Execute command
    updated_user = service.handle_connect_phone(command)

    return updated_user


@router.delete("/{user_id}/disconnect-phone", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def disconnect_phone(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Disconnect phone from user account.

    Removes phone from account. Requires email as alternative identifier.

    Rate Limit: 30 requests per minute per user

    Authorization: Only the user themselves can disconnect their phone

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)

    # Create command
    command = DisconnectPhoneCommand(
        user_id=user_id,
        current_user_id=current_user.id
    )

    # Execute command
    updated_user = service.handle_disconnect_phone(command)

    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_user(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete user account (soft delete - deactivates the account).

    Soft deletes the user account by marking it as inactive while preserving data.

    Rate Limit: 10 requests per minute per user

    Authorization: Only the user themselves can delete their account

    Requires: Bearer token in Authorization header
    """
    service = UserService(db)

    # Create command
    command = DeactivateUserCommand(
        user_id=user_id,
        current_user_id=current_user.id
    )

    # Execute command
    service.handle_deactivate_user(command)

    return {"message": "Account deactivated successfully"}
