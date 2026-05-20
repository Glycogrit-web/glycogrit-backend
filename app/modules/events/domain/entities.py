"""
Domain entities for Events module.

Entities encapsulate business rules and domain logic.
"""

from typing import TYPE_CHECKING, Optional
from datetime import datetime, timedelta
from decimal import Decimal

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

    def __init__(self, event: 'Event'):
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
    def is_upcoming(self) -> bool:
        """Check if event is upcoming"""
        return self._event.status == EventStatus.UPCOMING.value

    @property
    def is_ongoing(self) -> bool:
        """Check if event is ongoing"""
        return self._event.status == EventStatus.ONGOING.value

    @property
    def is_completed(self) -> bool:
        """Check if event is completed"""
        return self._event.status == EventStatus.COMPLETED.value

    @property
    def is_cancelled(self) -> bool:
        """Check if event is cancelled"""
        return self._event.status == EventStatus.CANCELLED.value

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
    def days_until_start(self) -> Optional[int]:
        """Get number of days until event starts"""
        if not self._event.event_date:
            return None
        if self.has_started:
            return 0
        delta = self._event.event_date - datetime.now()
        return delta.days

    @property
    def days_since_end(self) -> Optional[int]:
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
        return (
            self._event.registration_start_date <= now <= self._event.registration_end_date
        )

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
    def days_until_registration_opens(self) -> Optional[int]:
        """Get number of days until registration opens"""
        if self.is_registration_open:
            return 0
        if not self._event.registration_start_date:
            return None
        delta = self._event.registration_start_date - datetime.now()
        return max(0, delta.days)

    @property
    def days_until_registration_closes(self) -> Optional[int]:
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
    def capacity_remaining(self) -> Optional[int]:
        """Get remaining capacity"""
        if not self.has_capacity_limit:
            return None
        return max(0, self._event.max_participants - self._event.current_participants)

    @property
    def capacity_utilization_percentage(self) -> Optional[float]:
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

    def can_accept_registrations(self) -> tuple[bool, Optional[str]]:
        """
        Check if event can accept new registrations.

        Returns:
            Tuple of (can_accept, reason_if_not)
        """
        # Check if registration period is open
        if not self.is_registration_open:
            if datetime.now() < self._event.registration_start_date:
                return False, "Registration has not opened yet"
            return False, "Registration period has closed"

        # Check if event is cancelled
        if self.is_cancelled:
            return False, "Event is cancelled"

        # Check if event has already started (optional business rule)
        if self.has_started:
            return False, "Event has already started"

        # Check capacity
        if self.is_full:
            return False, "Event is at maximum capacity"

        # Check if event is published/upcoming
        if self._event.status not in ['published', 'upcoming']:
            return False, f"Event is not open for registration (status: {self._event.status})"

        return True, None

    def can_be_published(self) -> tuple[bool, Optional[str]]:
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

    def can_be_cancelled(self) -> tuple[bool, Optional[str]]:
        """
        Check if event can be cancelled.

        Returns:
            Tuple of (can_cancel, reason_if_not)
        """
        if self.is_cancelled:
            return False, "Event is already cancelled"

        if self.has_ended:
            return False, "Cannot cancel event that has already ended"

        # Allow cancellation before or during event
        return True, None

    def can_be_deleted(self) -> tuple[bool, Optional[str]]:
        """
        Check if event can be deleted.

        Returns:
            Tuple of (can_delete, reason_if_not)
        """
        # Check if event has registrations
        if self._event.current_participants > 0:
            return False, "Cannot delete event with existing registrations"

        return True, None

    def can_be_edited(self) -> tuple[bool, Optional[str]]:
        """
        Check if event can be edited.

        Returns:
            Tuple of (can_edit, reason_if_not)
        """
        if self.is_cancelled:
            return False, "Cannot edit cancelled event"

        if self.has_ended:
            return False, "Cannot edit event that has ended"

        return True, None

    def should_update_status(self) -> Optional[str]:
        """
        Determine if event status should be auto-updated based on dates.

        Returns:
            New status if update needed, None otherwise
        """
        current_status = self._event.status

        # Draft events don't auto-update
        if current_status == EventStatus.DRAFT.value:
            return None

        # Check if should be ongoing
        if self.is_active and current_status != EventStatus.ONGOING.value:
            return EventStatus.ONGOING.value

        # Check if should be completed
        if self.has_ended and current_status not in [EventStatus.COMPLETED.value, EventStatus.CANCELLED.value]:
            return EventStatus.COMPLETED.value

        # Check if should be upcoming
        if (
            not self.has_started and
            current_status == EventStatus.PUBLISHED.value and
            self.days_until_start and
            self.days_until_start <= 30
        ):
            return EventStatus.UPCOMING.value

        return None


class ActivityEntity:
    """
    Domain entity for EventActivity with business rules.

    Encapsulates activity-related business logic including:
    - Capacity management
    - Activity availability
    """

    def __init__(self, activity: 'EventActivity'):
        """
        Initialize ActivityEntity.

        Args:
            activity: EventActivity ORM model instance
        """
        self._activity = activity

    # ===== Capacity Properties =====

    @property
    def has_capacity_limit(self) -> bool:
        """Check if activity has a capacity limit"""
        return self._activity.max_participants is not None

    @property
    def is_full(self) -> bool:
        """Check if activity is at capacity"""
        if not self.has_capacity_limit:
            return False
        return self._activity.current_participants >= self._activity.max_participants

    @property
    def capacity_remaining(self) -> Optional[int]:
        """Get remaining capacity"""
        if not self.has_capacity_limit:
            return None
        return max(0, self._activity.max_participants - self._activity.current_participants)

    @property
    def is_available(self) -> bool:
        """Check if activity is available for registration"""
        return not self.is_full

    # ===== Pricing Properties =====

    @property
    def is_free(self) -> bool:
        """Check if activity is free"""
        return self._activity.registration_fee is None or self._activity.registration_fee == 0

    @property
    def registration_fee(self) -> Decimal:
        """Get registration fee"""
        return Decimal(str(self._activity.registration_fee or 0))

    # ===== Validation Methods =====

    def can_accept_registration(self) -> tuple[bool, Optional[str]]:
        """
        Check if activity can accept new registrations.

        Returns:
            Tuple of (can_accept, reason_if_not)
        """
        if self.is_full:
            return False, "Activity is at maximum capacity"

        return True, None
