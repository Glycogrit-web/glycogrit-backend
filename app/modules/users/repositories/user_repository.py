"""
User Repository - Data access layer for users

Handles all database operations using the repository pattern.
"""

from typing import Optional
from sqlalchemy.orm import Session
import re

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with user-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the UserRepository.

        Args:
            db: Database session
        """
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: Email address to search for

        Returns:
            User instance if found, None otherwise
        """
        return self.db.query(User).filter(User.email == email.lower()).first()

    def get_by_phone(self, phone: str) -> Optional[User]:
        """
        Retrieve a user by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            User instance if found, None otherwise
        """
        return self.db.query(User).filter(User.phone == phone).first()

    def get_by_oauth_id(self, oauth_provider: str, oauth_id: str) -> Optional[User]:
        """
        Retrieve a user by OAuth provider and OAuth ID.

        Args:
            oauth_provider: OAuth provider name (e.g., 'google', 'facebook')
            oauth_id: OAuth ID from the provider

        Returns:
            User instance if found, None otherwise
        """
        return self.db.query(User).filter(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        ).first()

    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if an email already exists in the database.

        Args:
            email: Email address to check
            exclude_id: Optional user ID to exclude from the check (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = self.db.query(User).filter(User.email == email.lower())
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.count() > 0

    def phone_exists(self, phone: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if a phone number already exists in the database.

        Args:
            phone: Phone number to check
            exclude_id: Optional user ID to exclude from the check (for updates)

        Returns:
            True if phone exists, False otherwise
        """
        query = self.db.query(User).filter(User.phone == phone)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.count() > 0

    def get_active_users(self, skip: int = 0, limit: int = 100):
        """
        Retrieve all active users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active User instances
        """
        return self.db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate a user account (soft delete).

        Args:
            user_id: User ID to deactivate

        Returns:
            Updated User instance if found, None otherwise
        """
        return self.update(user_id, {"is_active": False})

    def activate_user(self, user_id: int) -> Optional[User]:
        """
        Activate a user account.

        Args:
            user_id: User ID to activate

        Returns:
            Updated User instance if found, None otherwise
        """
        return self.update(user_id, {"is_active": True})

    def verify_email(self, user_id: int) -> Optional[User]:
        """
        Mark a user's email as verified.

        Args:
            user_id: User ID to verify

        Returns:
            Updated User instance if found, None otherwise
        """
        return self.update(user_id, {"email_verified": True})

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Retrieve a user by email or phone (auto-detect).

        Args:
            identifier: Email or phone number

        Returns:
            User instance if found, None otherwise
        """
        # Try as email first (contains @)
        if '@' in identifier:
            return self.get_by_email(identifier)

        # Try as phone (digits only after cleaning)
        cleaned_phone = re.sub(r'[^\d]', '', identifier)
        if cleaned_phone.isdigit() and len(cleaned_phone) == 10:
            return self.get_by_phone(cleaned_phone)

        return None

    def can_connect_email(self, email: str, user_id: int) -> bool:
        """
        Check if email can be connected (not already in use).

        Args:
            email: Email to check
            user_id: Current user ID

        Returns:
            True if email is available
        """
        return not self.email_exists(email, exclude_id=user_id)

    def can_connect_phone(self, phone: str, user_id: int) -> bool:
        """
        Check if phone can be connected (not already in use).

        Args:
            phone: Phone to check
            user_id: Current user ID

        Returns:
            True if phone is available
        """
        return not self.phone_exists(phone, exclude_id=user_id)

    def get_users_by_role(self, role: str, skip: int = 0, limit: int = 100):
        """
        Get users by role with pagination.

        Args:
            role: User role to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User instances with the specified role
        """
        return self.db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

    def count_by_role(self, role: str) -> int:
        """
        Count users by role.

        Args:
            role: User role to count

        Returns:
            Number of users with the specified role
        """
        return self.db.query(User).filter(User.role == role).count()

    def count_active_users(self) -> int:
        """
        Count active users.

        Returns:
            Number of active users
        """
        return self.db.query(User).filter(User.is_active == True).count()
