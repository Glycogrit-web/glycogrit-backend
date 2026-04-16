"""
Registration service for business logic.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import secrets
import string

from app.models.registration import Registration
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.event_repository import EventRepository
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    PermissionDeniedException,
    ValidationException
)
from app.core.permissions import PermissionChecker


class RegistrationService(BaseService):
    """Service for registration-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the RegistrationService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = RegistrationRepository(db)
        self.event_repository = EventRepository(db)

    def _generate_registration_number(self, event_id: int) -> str:
        """
        Generate a unique registration number.

        Args:
            event_id: Event ID

        Returns:
            Unique registration number
        """
        while True:
            # Generate format: EVT{event_id}-{random_6_chars}
            random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            reg_number = f"EVT{event_id}-{random_suffix}"

            if not self.repository.registration_number_exists(reg_number):
                return reg_number

    def register_for_event(
        self,
        event_id: int,
        user_id: int,
        category_id: Optional[int] = None,
        participant_name: str = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        t_shirt_size: Optional[str] = None
    ) -> Registration:
        """
        Register a user for an event.

        Args:
            event_id: Event ID
            user_id: User ID
            category_id: Optional category ID
            participant_name: Participant name
            age: Optional age
            gender: Optional gender
            t_shirt_size: Optional t-shirt size

        Returns:
            Created Registration instance

        Raises:
            NotFoundException: If event not found
            AlreadyExistsException: If user already registered
            ValidationException: If event is full or not open for registration
        """
        # Get event
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event", event_id)

        # Check if event is open for registration
        if event.status not in ['upcoming', 'ongoing', 'published']:
            raise ValidationException("Event is not open for registration", "event_status")

        # Check if user is already registered
        existing = self.repository.get_by_user_and_event(user_id, event_id)
        if existing:
            raise AlreadyExistsException("Registration", "user_event", f"user {user_id} in event {event_id}")

        # Check max participants
        if event.max_participants and event.current_participants >= event.max_participants:
            raise ValidationException("Event is full", "max_participants")

        # Generate registration number
        registration_number = self._generate_registration_number(event_id)

        # Determine payment status
        payment_status = 'not_required'
        if event.registration_fee and event.registration_fee > 0:
            payment_status = 'pending'

        # Create registration
        registration_data = {
            "user_id": user_id,
            "event_id": event_id,
            "event_category_id": category_id,
            "registration_number": registration_number,
            "participant_name": participant_name,
            "age": age,
            "gender": gender,
            "t_shirt_size": t_shirt_size,
            "status": "confirmed"
        }

        registration = self.repository.create(registration_data)

        # Increment participant count
        self.event_repository.update(event_id, {"current_participants": event.current_participants + 1})

        return registration

    def get_registration_by_id(self, registration_id: int) -> Registration:
        """
        Get a registration by ID.

        Args:
            registration_id: Registration ID

        Returns:
            Registration instance

        Raises:
            NotFoundException: If registration not found
        """
        return self.get_or_404(self.repository, registration_id, "Registration")

    def update_registration(
        self, registration_id: int, update_data: Dict[str, Any], current_user_id: int
    ) -> Registration:
        """
        Update a registration.

        Args:
            registration_id: Registration ID
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated Registration instance

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        PermissionChecker.require_registration_owner(registration, current_user_id)

        # Don't allow updating certain fields
        protected_fields = ["id", "user_id", "event_id", "registration_number", "registered_at"]
        for field in protected_fields:
            update_data.pop(field, None)

        # Update registration
        updated_registration = self.repository.update(registration_id, update_data)
        return updated_registration

    def cancel_registration(self, registration_id: int, current_user_id: int) -> bool:
        """
        Cancel a registration.

        Args:
            registration_id: Registration ID
            current_user_id: ID of the user making the request

        Returns:
            True if cancelled successfully

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
            ValidationException: If already cancelled
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        PermissionChecker.require_registration_owner(registration, current_user_id)

        # Check if already cancelled
        if registration.status == 'cancelled':
            raise ValidationException("Registration is already cancelled", "status")

        # Update status to cancelled
        self.repository.update(registration_id, {"status": "cancelled"})

        # Decrement participant count
        event = self.event_repository.get_by_id(registration.event_id)
        if event and event.current_participants > 0:
            self.event_repository.update(
                registration.event_id,
                {"current_participants": event.current_participants - 1}
            )

        return True

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
        return self.repository.get_registrations_by_user(user_id, skip, limit)

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
        return self.repository.get_registrations_by_event(event_id, skip, limit)
