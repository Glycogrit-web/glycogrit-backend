"""
Command objects for Event Service.

Commands represent write operations that modify state.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class CreateEventCommand:
    """
    Command to create a new event.
    """
    organizer_id: int
    name: str
    slug: str
    description: str
    event_date: datetime
    registration_start_date: datetime
    registration_end_date: datetime
    location_name: str
    city: str
    state: str
    country: str
    event_end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: Optional[int] = None
    is_virtual: bool = False
    is_featured: bool = False
    uses_tier_system: bool = True
    difficulty_level: Optional[str] = None
    currency: str = "INR"

    def __post_init__(self):
        """Validate command data"""
        if self.organizer_id <= 0:
            raise ValueError("organizer_id must be positive")
        if not self.name or len(self.name.strip()) < 3:
            raise ValueError("name must be at least 3 characters")
        if not self.slug or len(self.slug.strip()) < 3:
            raise ValueError("slug must be at least 3 characters")
        if not self.description or len(self.description.strip()) < 10:
            raise ValueError("description must be at least 10 characters")
        if self.registration_end_date <= self.registration_start_date:
            raise ValueError("registration_end_date must be after registration_start_date")
        if self.event_end_date and self.event_end_date < self.event_date:
            raise ValueError("event_end_date must be after or equal to event_date")
        if self.max_participants is not None and self.max_participants <= 0:
            raise ValueError("max_participants must be positive if provided")


@dataclass
class UpdateEventCommand:
    """
    Command to update an event.
    """
    event_id: int
    user_id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None
    max_participants: Optional[int] = None
    is_virtual: Optional[bool] = None
    is_featured: Optional[bool] = None
    difficulty_level: Optional[str] = None
    status: Optional[str] = None

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.name is not None and len(self.name.strip()) < 3:
            raise ValueError("name must be at least 3 characters if provided")
        if self.slug is not None and len(self.slug.strip()) < 3:
            raise ValueError("slug must be at least 3 characters if provided")
        if self.description is not None and len(self.description.strip()) < 10:
            raise ValueError("description must be at least 10 characters if provided")
        if self.max_participants is not None and self.max_participants < 0:
            raise ValueError("max_participants cannot be negative")


@dataclass
class PublishEventCommand:
    """
    Command to publish an event (change from draft to published).
    """
    event_id: int
    user_id: int

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class CancelEventCommand:
    """
    Command to cancel an event.
    """
    event_id: int
    user_id: int
    reason: Optional[str] = None

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class DeleteEventCommand:
    """
    Command to delete an event.
    """
    event_id: int
    user_id: int

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class CreateActivityCommand:
    """
    Command to create an event activity.
    """
    event_id: int
    name: str
    activity_type: Optional[str] = None
    distance: Optional[float] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None
    registration_fee: Optional[float] = None

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if not self.name or len(self.name.strip()) < 2:
            raise ValueError("name must be at least 2 characters")
        if self.distance is not None and self.distance <= 0:
            raise ValueError("distance must be positive if provided")
        if self.max_participants is not None and self.max_participants <= 0:
            raise ValueError("max_participants must be positive if provided")
        if self.registration_fee is not None and self.registration_fee < 0:
            raise ValueError("registration_fee cannot be negative")


@dataclass
class UpdateActivityCommand:
    """
    Command to update an event activity.
    """
    activity_id: int
    name: Optional[str] = None
    activity_type: Optional[str] = None
    distance: Optional[float] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None
    registration_fee: Optional[float] = None

    def __post_init__(self):
        """Validate command data"""
        if self.activity_id <= 0:
            raise ValueError("activity_id must be positive")
        if self.name is not None and len(self.name.strip()) < 2:
            raise ValueError("name must be at least 2 characters if provided")
        if self.distance is not None and self.distance < 0:
            raise ValueError("distance cannot be negative")
        if self.max_participants is not None and self.max_participants < 0:
            raise ValueError("max_participants cannot be negative")
        if self.registration_fee is not None and self.registration_fee < 0:
            raise ValueError("registration_fee cannot be negative")


@dataclass
class DeleteActivityCommand:
    """
    Command to delete an event activity.
    """
    activity_id: int

    def __post_init__(self):
        """Validate command data"""
        if self.activity_id <= 0:
            raise ValueError("activity_id must be positive")
