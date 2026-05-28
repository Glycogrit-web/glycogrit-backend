"""
Domain entities for Events module.

Entities encapsulate business rules and domain logic.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.core.enums import EventStatus

if TYPE_CHECKING:
    from app.modules.events.domain.event import Event, EventActivity


class EventEntity:
    """
    Domain entity for Event with business rules.

    Encapsulates event-related business logic including:
    - Status management
    - Registration period validation
    - Capacity management
    - Event lifecycle
    """

    def __init__(self, event: "Event"):
        """
        Initialize EventEntity.

        Args:
            event: Event ORM model instance
        """
        self._event = event

    # ===== Status Properties =====

    @property
    def is_draft(self) -> bool:
        """Check if event is in draft status"""
        return self._event.status == EventStatus.DRAFT.value

    @property
    def is_published(self) -> bool:
        """Check if event is published"""
        return self._event.status == EventStatus.PUBLISHED.value

    @property
    def is_archived(self) -> bool:
        """Check if event is archived"""
        return getattr(self._event, 'is_archived', False)

    @property
    def registration_state(self) -> str:
        """
        Get registration state: 'open' or 'closed'.

        Auto-determined based on registration_start_date and registration_end_date.
        """
        if self.is_registration_open:
            return 'open'
        return 'closed'

    # ===== Time-based Properties =====

    @property
    def has_started(self) -> bool:
        """Check if event has started"""
        if not self._event.event_date:
            return False
        return datetime.now() >= self._event.event_date

    @property
    def has_ended(self) -> bool:
        """Check if event has ended"""
        end_date = self._event.event_end_date or self._event.event_date
        if not end_date:
            return False
        return datetime.now() > end_date

    @property
    def is_active(self) -> bool:
        """Check if event is currently active (started but not ended)"""
        return self.has_started and not self.has_ended

    @property
    def days_until_start(self) -> int | None:
        """Get number of days until event starts"""
        if not self._event.event_date:
            return None
        if self.has_started:
            return 0
        delta = self._event.event_date - datetime.now()
        return delta.days

    @property
    def days_since_end(self) -> int | None:
        """Get number of days since event ended"""
        end_date = self._event.event_end_date or self._event.event_date
        if not end_date:
            return None
        if not self.has_ended:
            return 0
        delta = datetime.now() - end_date
        return delta.days

    # ===== Registration Properties =====

    @property
    def is_registration_open(self) -> bool:
        """Check if registration is currently open"""
        now = datetime.now()
        return self._event.registration_start_date <= now <= self._event.registration_end_date

    @property
    def registration_opens_soon(self, days: int = 7) -> bool:
        """Check if registration opens within specified days"""
        if self.is_registration_open:
            return False
        if not self._event.registration_start_date:
            return False
        delta = self._event.registration_start_date - datetime.now()
        return 0 <= delta.days <= days

    @property
    def registration_closes_soon(self, hours: int = 48) -> bool:
        """Check if registration closes within specified hours"""
        if not self.is_registration_open:
            return False
        delta = self._event.registration_end_date - datetime.now()
        return 0 <= delta.total_seconds() <= (hours * 3600)

    @property
    def days_until_registration_opens(self) -> int | None:
        """Get number of days until registration opens"""
        if self.is_registration_open:
            return 0
        if not self._event.registration_start_date:
            return None
        delta = self._event.registration_start_date - datetime.now()
        return max(0, delta.days)

    @property
    def days_until_registration_closes(self) -> int | None:
        """Get number of days until registration closes"""
        if not self.is_registration_open:
            return None
        delta = self._event.registration_end_date - datetime.now()
        return max(0, delta.days)

    # ===== Capacity Properties =====

    @property
    def has_capacity_limit(self) -> bool:
        """Check if event has a capacity limit"""
        return self._event.max_participants is not None

    @property
    def is_full(self) -> bool:
        """Check if event is at capacity"""
        if not self.has_capacity_limit:
            return False
        return self._event.current_participants >= self._event.max_participants

    @property
    def capacity_remaining(self) -> int | None:
        """Get remaining capacity"""
        if not self.has_capacity_limit:
            return None
        return max(0, self._event.max_participants - self._event.current_participants)

    @property
    def capacity_utilization_percentage(self) -> float | None:
        """Calculate capacity utilization as percentage"""
        if not self.has_capacity_limit:
            return None
        if self._event.max_participants == 0:
            return 100.0
        return (self._event.current_participants / self._event.max_participants) * 100

    @property
    def is_nearly_full(self, threshold: float = 0.9) -> bool:
        """Check if event is nearly full (default 90% capacity)"""
        if not self.has_capacity_limit:
            return False
        utilization = self.capacity_utilization_percentage
        return utilization >= (threshold * 100)

    # ===== Feature Properties =====

    @property
    def uses_tier_system(self) -> bool:
        """Check if event uses tier-based registration"""
        return self._event.uses_tier_system

    @property
    def is_virtual(self) -> bool:
        """Check if event is virtual"""
        return self._event.is_virtual

    @property
    def is_featured(self) -> bool:
        """Check if event is featured"""
        return self._event.is_featured

    # ===== Validation Methods =====

    def can_accept_registrations(self) -> tuple[bool, str | None]:
        """
        Check if event can accept new registrations.

        Returns:
            Tuple of (can_accept, reason_if_not)
        """
        # Check if event is published
        if not self.is_published:
            return False, "Event must be published to accept registrations"

        # Check if event is archived
        if self.is_archived:
            return False, "Event is archived and no longer accepting registrations"

        # Check if registration period is open
        if not self.is_registration_open:
            if datetime.now() < self._event.registration_start_date:
                return False, "Registration has not opened yet"
            return False, "Registration period has closed"

        # Check capacity
        if self.is_full:
            return False, "Event is at maximum capacity"

        return True, None

    def can_be_published(self) -> tuple[bool, str | None]:
        """
        Check if event can be published.

        Returns:
            Tuple of (can_publish, reason_if_not)
        """
        if not self.is_draft:
            return False, "Event is not in draft status"

        # Validate required fields
        if not self._event.name:
            return False, "Event name is required"
        if not self._event.event_date:
            return False, "Event date is required"
        if not self._event.registration_start_date or not self._event.registration_end_date:
            return False, "Registration dates are required"
        if not self._event.location_name:
            return False, "Location is required"

        return True, None


    def can_be_deleted(self) -> tuple[bool, str | None]:
        """
        Check if event can be deleted.

        Returns:
            Tuple of (can_delete, reason_if_not)
        """
        # Check if event has registrations
        if self._event.current_participants > 0:
            return False, "Cannot delete event with existing registrations"

        return True, None

    def can_be_edited(self) -> tuple[bool, str | None]:
        """
        Check if event can be edited.

        Returns:
            Tuple of (can_edit, reason_if_not)
        """
        # Events can be edited unless they have ended
        if self.has_ended:
            return False, "Cannot edit event that has ended"

        return True, None



class ActivityEntity:
    """
    Domain entity for EventActivity with business rules.

    Encapsulates activity-related business logic including:
    - Capacity management
    - Activity availability
    """

    def __init__(self, activity: "EventActivity"):
        """
        Initialize ActivityEntity.

        Args:
            activity: EventActivity ORM model instance
        """
        self._activity = activity

    # NOTE: Capacity and pricing properties removed
    # These are now handled at the tier level (event_registration_tiers)
    # Use tier-based capacity and pricing logic instead

    # ===== Validation Methods =====

    def can_accept_registration(self) -> tuple[bool, str | None]:
        """
        Check if activity can accept new registrations.

        NOTE: Capacity validation removed from activity level.
        Capacity is now managed at the tier level.

        Returns:
            Tuple of (can_accept, reason_if_not)
        """
        return True, None
