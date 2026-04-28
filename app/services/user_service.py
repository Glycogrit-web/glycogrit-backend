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

    def register_user(self, email: Optional[str] = None, phone: Optional[str] = None,
                     password: str = None, first_name: str = None, last_name: str = None,
                     city: Optional[str] = None, state: Optional[str] = None) -> Dict[str, str]:
        """
        Register a new user with email and/or phone.

        Args:
            email: Optional user's email address
            phone: Optional user's phone number
            password: User's password (will be hashed)
            first_name: User's first name
            last_name: User's last name
            city: Optional city
            state: Optional state

        Returns:
            Dictionary with access_token and token_type

        Raises:
            ValidationException: If neither email nor phone provided
            AlreadyExistsException: If email or phone already exists
        """
        # Validate at least one identifier
        if not email and not phone:
            raise ValidationException("Either email or phone must be provided")

        # Check if email already exists
        if email and self.repository.email_exists(email):
            raise AlreadyExistsException("User", "email", email)

        # Check if phone already exists
        if phone and self.repository.phone_exists(phone):
            raise AlreadyExistsException("User", "phone", phone)

        # Create new user
        user_data = {
            "email": email,
            "phone": phone,
            "password_hash": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "city": city,
            "state": state,
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

    def authenticate_user(self, identifier: str, password: str, identifier_type: Optional[str] = None) -> Dict[str, str]:
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
            raise AuthenticationException("This account uses OAuth sign-in. Please login with Google or set a password first.")

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

    def connect_email(self, user_id: int, email: str, current_user_id: int) -> User:
        """
        Connect an email address to an existing user account.

        Args:
            user_id: User ID to update
            email: Email address to connect
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            AlreadyExistsException: If email already exists
            ValidationException: If user already has email
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Check if user already has email
        if user.has_email():
            from app.core.exceptions import ValidationException
            raise ValidationException("User already has an email address. Disconnect the current email first.")

        # Validate email uniqueness
        if not self.repository.can_connect_email(email, user_id):
            raise AlreadyExistsException("User", "email", email)

        # Update user with email
        updated_user = self.repository.update(user_id, {"email": email})
        return updated_user

    def connect_phone(self, user_id: int, phone: str, current_user_id: int) -> User:
        """
        Connect a phone number to an existing user account.

        Args:
            user_id: User ID to update
            phone: Phone number to connect
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            AlreadyExistsException: If phone already exists
            ValidationException: If user already has phone
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Check if user already has phone
        if user.has_phone():
            from app.core.exceptions import ValidationException
            raise ValidationException("User already has a phone number. Disconnect the current phone first.")

        # Validate phone uniqueness
        if not self.repository.can_connect_phone(phone, user_id):
            raise AlreadyExistsException("User", "phone", phone)

        # Update user with phone
        updated_user = self.repository.update(user_id, {"phone": phone})
        return updated_user

    def disconnect_email(self, user_id: int, current_user_id: int) -> User:
        """
        Disconnect email from user account.

        Args:
            user_id: User ID to update
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            ValidationException: If user doesn't have phone (cannot disconnect last identifier)
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Check if user can disconnect email (must have phone)
        if not user.can_disconnect_email():
            from app.core.exceptions import ValidationException
            raise ValidationException("Cannot disconnect email. You must have a phone number connected first.")

        # Disconnect email
        updated_user = self.repository.update(user_id, {"email": None})
        return updated_user

    def disconnect_phone(self, user_id: int, current_user_id: int) -> User:
        """
        Disconnect phone from user account.

        Args:
            user_id: User ID to update
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            ValidationException: If user doesn't have email (cannot disconnect last identifier)
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Check if user can disconnect phone (must have email)
        if not user.can_disconnect_phone():
            from app.core.exceptions import ValidationException
            raise ValidationException("Cannot disconnect phone. You must have an email address connected first.")

        # Disconnect phone
        updated_user = self.repository.update(user_id, {"phone": None})
        return updated_user

    def set_password_for_oauth_user(self, user_id: int, phone: str, password: str, current_user_id: int) -> User:
        """
        Set password and phone for OAuth user to enable password-based login.

        Args:
            user_id: User ID to update
            phone: Phone number to connect
            password: Password to set
            current_user_id: ID of the user making the request

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            ValidationException: If user already has password
            AlreadyExistsException: If phone already exists
        """
        # Get user
        user = self.get_user_by_id(user_id)

        # Check ownership
        self.check_ownership(user.id, current_user_id, "user account")

        # Check if user already has password
        if user.has_password:
            from app.core.exceptions import ValidationException
            raise ValidationException("User already has a password set.")

        # Validate phone uniqueness
        if not self.repository.can_connect_phone(phone, user_id):
            raise AlreadyExistsException("User", "phone", phone)

        # Hash password and update user
        password_hash = hash_password(password)
        updated_user = self.repository.update(user_id, {
            "phone": phone,
            "password_hash": password_hash
        })

        return updated_user

    def authenticate_or_create_oauth_user(
        self,
        email: str,
        oauth_provider: str,
        oauth_id: str,
        first_name: str,
        last_name: str,
        profile_picture_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Authenticate or create a user via OAuth (Google, Facebook, etc.).

        If a user with this OAuth ID exists, authenticate them.
        If a user with this email exists but no OAuth ID, link the OAuth account.
        Otherwise, create a new user.

        Args:
            email: User's email from OAuth provider
            oauth_provider: OAuth provider name (e.g., 'google')
            oauth_id: User's ID from the OAuth provider
            first_name: User's first name
            last_name: User's last name
            profile_picture_url: Optional profile picture URL

        Returns:
            Dictionary with access_token and token_type

        Raises:
            PermissionDeniedException: If account is inactive
        """
        # Try to find user by OAuth ID first
        user = self.repository.get_by_oauth_id(oauth_provider, oauth_id)

        if user:
            # User exists with this OAuth account
            if not user.is_active:
                raise PermissionDeniedException("Account is inactive")
        else:
            # Check if user exists with this email (account linking)
            user = self.repository.get_by_email(email)

            if user:
                # Link OAuth account to existing user
                update_data = {
                    "oauth_provider": oauth_provider,
                    "oauth_id": oauth_id,
                    "email_verified": True,  # Trust OAuth provider's email verification
                }
                if profile_picture_url and not user.profile_picture_url:
                    update_data["profile_picture_url"] = profile_picture_url

                user = self.repository.update(user.id, update_data)
            else:
                # Create new OAuth user
                user_data = {
                    "email": email,
                    "password_hash": None,  # No password for OAuth users
                    "first_name": first_name,
                    "last_name": last_name,
                    "oauth_provider": oauth_provider,
                    "oauth_id": oauth_id,
                    "profile_picture_url": profile_picture_url,
                    "is_active": True,
                    "email_verified": True  # Trust OAuth provider's email verification
                }

                user = self.repository.create(user_data)

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
