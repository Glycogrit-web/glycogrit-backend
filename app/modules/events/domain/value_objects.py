"""
Value objects for Events module.

Value objects are immutable and represent domain concepts.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EventSlug:
    """
    Value object for event slug (URL-friendly identifier).

    Slugs are unique identifiers for events in URLs.
    """

    value: str

    def __post_init__(self):
        """Validate event slug"""
        if not self.value:
            raise ValueError("Event slug cannot be empty")

        if len(self.value) < 3:
            raise ValueError("Event slug must be at least 3 characters")

        if len(self.value) > 255:
            raise ValueError("Event slug must not exceed 255 characters")

        # Validate slug format (lowercase, alphanumeric, hyphens only)
        if not all(c.islower() or c.isdigit() or c == "-" for c in self.value):
            raise ValueError("Event slug must contain only lowercase letters, numbers, and hyphens")

        if self.value.startswith("-") or self.value.endswith("-"):
            raise ValueError("Event slug cannot start or end with hyphen")

        if "--" in self.value:
            raise ValueError("Event slug cannot contain consecutive hyphens")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_name(cls, name: str) -> "EventSlug":
        """
        Generate slug from event name.

        Args:
            name: Event name

        Returns:
            EventSlug instance
        """
        # Convert to lowercase, replace spaces with hyphens
        slug = name.lower().strip()
        slug = slug.replace(" ", "-")

        # Remove non-alphanumeric characters except hyphens
        slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)

        # Remove consecutive hyphens
        while "--" in slug:
            slug = slug.replace("--", "-")

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        return cls(slug)


@dataclass(frozen=True)
class EventLocation:
    """
    Value object for event location.

    Encapsulates location information with validation.
    """

    location_name: str
    city: str
    state: str
    country: str
    full_address: str | None = None

    def __post_init__(self):
        """Validate location data"""
        if not self.location_name or len(self.location_name.strip()) < 2:
            raise ValueError("Location name must be at least 2 characters")

        if not self.city or len(self.city.strip()) < 2:
            raise ValueError("City must be at least 2 characters")

        if not self.state or len(self.state.strip()) < 2:
            raise ValueError("State must be at least 2 characters")

        if not self.country or len(self.country.strip()) < 2:
            raise ValueError("Country must be at least 2 characters")

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "location_name": self.location_name,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "location": self.full_address
            or f"{self.location_name}, {self.city}, {self.state}, {self.country}",
        }

    def __str__(self) -> str:
        return f"{self.location_name}, {self.city}, {self.state}, {self.country}"

    @property
    def short_location(self) -> str:
        """Get short location string (city, state)"""
        return f"{self.city}, {self.state}"


@dataclass(frozen=True)
class RegistrationPeriod:
    """
    Value object for event registration period.

    Encapsulates registration date validation and logic.
    """

    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        """Validate registration period"""
        if not self.start_date:
            raise ValueError("Registration start date is required")

        if not self.end_date:
            raise ValueError("Registration end date is required")

        if self.end_date <= self.start_date:
            raise ValueError("Registration end date must be after start date")

    @property
    def duration_days(self) -> int:
        """Get registration period duration in days"""
        delta = self.end_date - self.start_date
        return delta.days

    @property
    def is_open(self) -> bool:
        """Check if registration is currently open"""
        now = datetime.now()
        return self.start_date <= now <= self.end_date

    @property
    def has_started(self) -> bool:
        """Check if registration has started"""
        return datetime.now() >= self.start_date

    @property
    def has_ended(self) -> bool:
        """Check if registration has ended"""
        return datetime.now() > self.end_date

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {"registration_start_date": self.start_date, "registration_end_date": self.end_date}


@dataclass(frozen=True)
class EventCapacity:
    """
    Value object for event capacity tracking.

    Encapsulates capacity logic for events.
    """

    max_participants: int | None
    current_participants: int

    def __post_init__(self):
        """Validate event capacity"""
        if self.current_participants < 0:
            raise ValueError("Current participants cannot be negative")

        if self.max_participants is not None and self.max_participants < 0:
            raise ValueError("Max participants cannot be negative")

    @property
    def has_limit(self) -> bool:
        """Check if event has a capacity limit"""
        return self.max_participants is not None

    @property
    def is_unlimited(self) -> bool:
        """Check if event has unlimited capacity"""
        return self.max_participants is None

    @property
    def remaining(self) -> int | None:
        """Get remaining capacity"""
        if self.is_unlimited:
            return None
        return max(0, self.max_participants - self.current_participants)

    @property
    def is_full(self) -> bool:
        """Check if event is at capacity"""
        if self.is_unlimited:
            return False
        return self.current_participants >= self.max_participants

    @property
    def utilization_percentage(self) -> float | None:
        """Calculate capacity utilization as percentage"""
        if self.is_unlimited:
            return None
        if self.max_participants == 0:
            return 100.0
        return (self.current_participants / self.max_participants) * 100

    def __str__(self) -> str:
        if self.is_unlimited:
            return f"{self.current_participants} participants (unlimited)"
        return f"{self.current_participants}/{self.max_participants} participants"


@dataclass(frozen=True)
class EventDateRange:
    """
    Value object for event date range.

    Encapsulates event date validation.
    """

    start_date: datetime
    end_date: datetime | None = None

    def __post_init__(self):
        """Validate date range"""
        if not self.start_date:
            raise ValueError("Event start date is required")

        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Event end date must be after or equal to start date")

    @property
    def duration_days(self) -> int | None:
        """Get event duration in days"""
        if not self.end_date:
            return None
        delta = self.end_date - self.start_date
        return delta.days

    @property
    def is_single_day(self) -> bool:
        """Check if event is single day"""
        if not self.end_date:
            return True
        return self.start_date.date() == self.end_date.date()

    @property
    def is_multi_day(self) -> bool:
        """Check if event spans multiple days"""
        return not self.is_single_day

    @property
    def has_started(self) -> bool:
        """Check if event has started"""
        return datetime.now() >= self.start_date

    @property
    def has_ended(self) -> bool:
        """Check if event has ended"""
        end = self.end_date or self.start_date
        return datetime.now() > end

    @property
    def is_active(self) -> bool:
        """Check if event is currently active"""
        return self.has_started and not self.has_ended

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {"event_date": self.start_date, "event_end_date": self.end_date}

    def __str__(self) -> str:
        if self.is_single_day:
            return self.start_date.strftime("%B %d, %Y")
        return f"{self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}"
