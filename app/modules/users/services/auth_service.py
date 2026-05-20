"""
Authentication Service - Handles authentication and OAuth

Manages user authentication, JWT token generation, and OAuth flows.
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.users.repositories.user_repository import UserRepository
from app.modules.users.services.commands import RegisterOAuthUserCommand
from app.core.auth import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    PermissionDeniedException,
)


class AuthService:
    """Service for authentication-related operations."""

    def __init__(self, db: Session):
        """
        Initialize the AuthService.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = UserRepository(db)

    def authenticate_user(
        self,
        identifier: str,
        password: str,
        identifier_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Authenticate a user with email/phone and password.

        Args:
            identifier: User's email address or phone number
            password: User's password
            identifier_type: Optional 'email' or 'phone' (auto-detected if not provided)

        Returns:
            Dictionary with access_token and token_type

        Raises:
            AuthenticationException: If credentials are invalid or user has no password
            PermissionDeniedException: If account is inactive
        """
        # Find user by identifier (auto-detects email vs phone)
        user = self.repository.get_by_identifier(identifier)

        if not user:
            raise AuthenticationException("Incorrect email/phone or password")

        # Check if user has a password (OAuth users might not)
        if not user.password_hash:
            raise AuthenticationException(
                "This account uses OAuth sign-in. Please login with Google or set a password first."
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            raise AuthenticationException("Incorrect email/phone or password")

        # Check if user is active
        if not user.is_active:
            raise PermissionDeniedException("Account is inactive")

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id
        }

    def handle_register_oauth_user(self, command: RegisterOAuthUserCommand) -> Dict[str, str]:
        """
        Authenticate or create a user via OAuth (Google, Facebook, etc.).

        If a user with this OAuth ID exists, authenticate them.
        If a user with this email exists but no OAuth ID, link the OAuth account.
        Otherwise, create a new user.

        Args:
            command: RegisterOAuthUserCommand with OAuth data

        Returns:
            Dictionary with access_token and token_type

        Raises:
            PermissionDeniedException: If account is inactive
        """
        # Determine role based on email
        user_role = "admin" if command.email.lower() in settings.admin_emails_list else "user"

        # Try to find user by OAuth ID first
        user = self.repository.get_by_oauth_id(command.oauth_provider, command.oauth_id)

        if user:
            # User exists with this OAuth account
            if not user.is_active:
                raise PermissionDeniedException("Account is inactive")

            # Update role if user is in admin list but doesn't have admin role
            if command.email.lower() in settings.admin_emails_list and user.role != "admin":
                user = self.repository.update(user.id, {"role": "admin"})
        else:
            # Check if user exists with this email (account linking)
            user = self.repository.get_by_email(command.email)

            if user:
                # Link OAuth account to existing user
                update_data = {
                    "oauth_provider": command.oauth_provider,
                    "oauth_id": command.oauth_id,
                    "email_verified": True,  # Trust OAuth provider's email verification
                }
                if command.profile_picture_url and not user.profile_picture_url:
                    update_data["profile_picture_url"] = command.profile_picture_url

                # Update role if user is in admin list
                if command.email.lower() in settings.admin_emails_list:
                    update_data["role"] = "admin"

                user = self.repository.update(user.id, update_data)
            else:
                # Create new OAuth user
                user_data = {
                    "email": command.email.lower(),
                    "password_hash": None,  # No password for OAuth users
                    "first_name": command.first_name,
                    "last_name": command.last_name,
                    "oauth_provider": command.oauth_provider,
                    "oauth_id": command.oauth_id,
                    "profile_picture_url": command.profile_picture_url,
                    "is_active": True,
                    "email_verified": True,  # Trust OAuth provider's email verification
                    "role": user_role
                }

                user = self.repository.create(user_data)

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id
        }

    def refresh_token(self, user_id: int) -> Dict[str, str]:
        """
        Generate a new access token for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with new access_token and token_type

        Raises:
            PermissionDeniedException: If user is inactive
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            raise AuthenticationException("User not found")

        if not user.is_active:
            raise PermissionDeniedException("Account is inactive")

        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id
        }
