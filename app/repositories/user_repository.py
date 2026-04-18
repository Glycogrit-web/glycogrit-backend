"""
User repository for database operations.
"""

from typing import Optional
from sqlalchemy.orm import Session

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
        return self.db.query(User).filter(User.email == email).first()

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
        query = self.db.query(User).filter(User.email == email)
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
