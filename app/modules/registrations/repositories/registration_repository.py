"""
Registration repository for database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.modules.registrations.domain.registration import Registration
from app.core.repository.base import BaseRepository
from app.core.enums import RegistrationStatus


class RegistrationRepository(BaseRepository[Registration]):
    """Repository for Registration model with registration-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the RegistrationRepository.

        Args:
            db: Database session
        """
        super().__init__(Registration, db)

    def get_by_registration_number(self, registration_number: str) -> Optional[Registration]:
        """
        Retrieve a registration by registration number.

        Args:
            registration_number: Registration number to search for

        Returns:
            Registration instance if found, None otherwise
        """
        return self.db.query(Registration).filter(
            Registration.registration_number == registration_number
        ).first()

    def get_by_user_and_event(self, user_id: int, event_id: int) -> Optional[Registration]:
        """
        Check if a user is registered for an event.

        Args:
            user_id: User ID
            event_id: Event ID

        Returns:
            Registration instance if found, None otherwise
        """
        return self.db.query(Registration).filter(
            Registration.user_id == user_id,
            Registration.event_id == event_id
        ).first()

    def get_registrations_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Registration]:
        """
        Get all registrations for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return self.db.query(Registration).filter(
            Registration.user_id == user_id
        ).offset(skip).limit(limit).all()

    def get_registrations_by_event(self, event_id: int, skip: int = 0, limit: int = 100) -> List[Registration]:
        """
        Get all registrations for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return self.db.query(Registration).filter(
            Registration.event_id == event_id
        ).offset(skip).limit(limit).all()

    def get_registrations_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Registration]:
        """
        Get registrations by status.

        Args:
            status: Registration status (pending, confirmed, cancelled, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return self.db.query(Registration).filter(
            Registration.status == status
        ).offset(skip).limit(limit).all()

    def get_confirmed_registrations_by_event(self, event_id: int) -> List[Registration]:
        """
        Get all confirmed registrations for an event.

        Args:
            event_id: Event ID

        Returns:
            List of confirmed Registration instances
        """
        return self.db.query(Registration).filter(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.CONFIRMED.value
        ).all()

    def registration_number_exists(self, registration_number: str) -> bool:
        """
        Check if a registration number already exists.

        Args:
            registration_number: Registration number to check

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(Registration).filter(
            Registration.registration_number == registration_number
        ).count() > 0
