"""
User service for business logic.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    AuthenticationException,
    PermissionDeniedException
)
from app.core.auth import hash_password, verify_password, create_access_token


class UserService(BaseService):
    """Service for user-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the UserService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = UserRepository(db)

    def register_user(self, email: str, password: str, first_name: str, last_name: str,
                     city: Optional[str] = None, state: Optional[str] = None,
                     phone: Optional[str] = None) -> Dict[str, str]:
        """
        Register a new user.

        Args:
            email: User's email address
            password: User's password (will be hashed)
            first_name: User's first name
            last_name: User's last name
            city: Optional city
            state: Optional state
            phone: Optional phone number

        Returns:
            Dictionary with access_token and token_type

        Raises:
            AlreadyExistsException: If email or phone already exists
        """
        # Check if email already exists
        if self.repository.email_exists(email):
            raise AlreadyExistsException("User", "email", email)

        # Check if phone already exists
        if phone and self.repository.phone_exists(phone):
            raise AlreadyExistsException("User", "phone", phone)

        # Create new user
        user_data = {
            "email": email,
            "password_hash": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "city": city,
            "state": state,
            "phone": phone,
            "is_active": True,
            "email_verified": False
        }

        new_user = self.repository.create(user_data)

        # Create access token
        access_token = create_access_token(data={"sub": new_user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    def authenticate_user(self, email: str, password: str) -> Dict[str, str]:
        """
        Authenticate a user with email and password.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dictionary with access_token and token_type

        Raises:
            AuthenticationException: If credentials are invalid
            PermissionDeniedException: If account is inactive
        """
        # Find user by email
        user = self.repository.get_by_email(email)

        if not user:
            raise AuthenticationException("Incorrect email or password")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise AuthenticationException("Incorrect email or password")

        # Check if user is active
        if not user.is_active:
            raise PermissionDeniedException("Account is inactive")

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    def get_user_by_id(self, user_id: int) -> User:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User instance

        Raises:
            NotFoundException: If user not found
        """
        return self.get_or_404(self.repository, user_id, "User")

    def update_user(self, user_id: int, update_data: Dict[str, Any], current_user_id: int) -> User:
        """
        Update a user's profile.

        Args:
            user_id: User ID to update
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            AlreadyExistsException: If email or phone already exists
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user profile")

        # Validate email uniqueness if updating email
        if "email" in update_data and update_data["email"] != user.email:
            if self.repository.email_exists(update_data["email"], exclude_id=user_id):
                raise AlreadyExistsException("User", "email", update_data["email"])

        # Validate phone uniqueness if updating phone
        if "phone" in update_data and update_data["phone"] != user.phone:
            if self.repository.phone_exists(update_data["phone"], exclude_id=user_id):
                raise AlreadyExistsException("User", "phone", update_data["phone"])

        # Don't allow updating sensitive fields directly
        sensitive_fields = ["password_hash", "is_active", "email_verified", "id"]
        for field in sensitive_fields:
            update_data.pop(field, None)

        # Update user
        updated_user = self.repository.update(user_id, update_data)
        return updated_user

    def change_password(self, user_id: int, current_password: str, new_password: str, current_user_id: int) -> User:
        """
        Change a user's password.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            AuthenticationException: If current password is incorrect
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationException("Current password is incorrect")

        # Update password
        new_password_hash = hash_password(new_password)
        updated_user = self.repository.update(user_id, {"password_hash": new_password_hash})

        return updated_user

    def delete_user(self, user_id: int, current_user_id: int) -> bool:
        """
        Delete a user account (soft delete - deactivates the account).

        Args:
            user_id: User ID to delete
            current_user_id: ID of the user making the request

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Soft delete (deactivate)
        self.repository.deactivate_user(user_id)

        return True

    def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User instances
        """
        return self.repository.get_all(skip, limit)

    def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all active users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active User instances
        """
        return self.repository.get_active_users(skip, limit)
