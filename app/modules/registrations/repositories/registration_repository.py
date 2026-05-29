"""
Registration repository for database operations.
"""

from sqlalchemy.orm import Session

from app.core.enums import RegistrationStatus
from app.core.repository.base import BaseRepository
from app.modules.registrations.domain.registration import Registration


class RegistrationRepository(BaseRepository[Registration]):
    """Repository for Registration model with registration-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the RegistrationRepository.

        Args:
            db: Database session
        """
        super().__init__(Registration, db)

    def get_by_registration_number(self, registration_number: str) -> Registration | None:
        """
        Retrieve a registration by registration number.

        Args:
            registration_number: Registration number to search for

        Returns:
            Registration instance if found, None otherwise
        """
        return (
            self.db.query(Registration)
            .filter(Registration.registration_number == registration_number)
            .first()
        )

    def get_by_user_and_event(self, user_id: int, event_id: int) -> list[Registration]:
        """
        Get ALL registrations for a user in an event.

        UPDATED BEHAVIOR: Returns list of registrations (one per tier).
        Previously returned single registration. Now supports multiple
        registrations per user per event (one per tier).

        Args:
            user_id: User ID
            event_id: Event_ID

        Returns:
            List of Registration instances (may be empty)
        """
        return (
            self.db.query(Registration)
            .filter(Registration.user_id == user_id, Registration.event_id == event_id)
            .order_by(Registration.registered_at.desc())
            .all()
        )

    def get_by_user_event_tier(
        self, user_id: int, event_id: int, tier_id: int
    ) -> Registration | None:
        """
        Get specific registration for user/event/tier combination.

        NEW METHOD: Checks if user already registered for specific tier.
        Used to prevent duplicate registrations for the same tier while
        allowing registrations for different tiers.

        Args:
            user_id: User ID
            event_id: Event ID
            tier_id: Tier ID

        Returns:
            Registration instance if found, None otherwise
        """
        return (
            self.db.query(Registration)
            .filter(
                Registration.user_id == user_id,
                Registration.event_id == event_id,
                Registration.current_tier_id == tier_id
            )
            .first()
        )

    def get_registrations_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Registration]:
        """
        Get all registrations for a user with eager loading of related entities.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances with preloaded relationships
        """
        from sqlalchemy.orm import joinedload
        from app.modules.events.domain.event import Event

        return (
            self.db.query(Registration)
            .options(
                joinedload(Registration.current_tier),
                joinedload(Registration.event).joinedload(Event.registration_tiers),
                joinedload(Registration.activity),
                joinedload(Registration.activity_progress),
                joinedload(Registration.user)
            )
            .filter(Registration.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_registrations_by_event(
        self, event_id: int, skip: int = 0, limit: int = 100
    ) -> list[Registration]:
        """
        Get all registrations for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return (
            self.db.query(Registration)
            .filter(Registration.event_id == event_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_registrations_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[Registration]:
        """
        Get registrations by status.

        Args:
            status: Registration status (pending, confirmed, cancelled, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return (
            self.db.query(Registration)
            .filter(Registration.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_confirmed_registrations_by_event(self, event_id: int) -> list[Registration]:
        """
        Get all confirmed registrations for an event.

        Args:
            event_id: Event ID

        Returns:
            List of confirmed Registration instances
        """
        return (
            self.db.query(Registration)
            .filter(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.CONFIRMED.value,
            )
            .all()
        )

    def registration_number_exists(self, registration_number: str) -> bool:
        """
        Check if a registration number already exists.

        Args:
            registration_number: Registration number to check

        Returns:
            True if exists, False otherwise
        """
        return (
            self.db.query(Registration)
            .filter(Registration.registration_number == registration_number)
            .count()
            > 0
        )
