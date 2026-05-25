"""
Query objects for Event Service.

Queries represent read operations that don't modify state.
"""

from dataclasses import dataclass


@dataclass
class GetEventByIdQuery:
    """
    Query to get an event by ID.
    """
    event_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")


@dataclass
class GetEventBySlugQuery:
    """
    Query to get an event by slug.
    """
    slug: str

    def __post_init__(self):
        """Validate query data"""
        if not self.slug:
            raise ValueError("slug is required")


@dataclass
class ListEventsQuery:
    """
    Query to list events with filters.
    """
    skip: int = 0
    limit: int = 100
    status: str | None = None
    city: str | None = None
    is_virtual: bool | None = None
    is_featured: bool | None = None
    organizer_id: int | None = None
    search: str | None = None

    def __post_init__(self):
        """Validate query data"""
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.organizer_id is not None and self.organizer_id <= 0:
            raise ValueError("organizer_id must be positive if provided")


@dataclass
class GetUpcomingEventsQuery:
    """
    Query to get upcoming events.
    """
    skip: int = 0
    limit: int = 100
    city: str | None = None
    is_virtual: bool | None = None

    def __post_init__(self):
        """Validate query data"""
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetFeaturedEventsQuery:
    """
    Query to get featured events.
    """
    limit: int = 10

    def __post_init__(self):
        """Validate query data"""
        if self.limit <= 0 or self.limit > 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass
class GetEventsByOrganizerQuery:
    """
    Query to get events by organizer.
    """
    organizer_id: int
    skip: int = 0
    limit: int = 100
    status_filter: str | None = None

    def __post_init__(self):
        """Validate query data"""
        if self.organizer_id <= 0:
            raise ValueError("organizer_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetEventActivitiesQuery:
    """
    Query to get activities for an event.
    """
    event_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")


@dataclass
class GetActivityByIdQuery:
    """
    Query to get an activity by ID.
    """
    activity_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.activity_id <= 0:
            raise ValueError("activity_id must be positive")


@dataclass
class SearchEventsQuery:
    """
    Query to search events by keyword.
    """
    search_term: str
    skip: int = 0
    limit: int = 100
    city_filter: str | None = None
    status_filter: str | None = None

    def __post_init__(self):
        """Validate query data"""
        if not self.search_term or len(self.search_term.strip()) < 2:
            raise ValueError("search_term must be at least 2 characters")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetEventsRequiringStatusUpdateQuery:
    """
    Query to get events that need automatic status updates.

    Used for background jobs that update event status based on dates.
    """
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetEventStatisticsQuery:
    """
    Query to get statistics for an event.

    Returns participant counts, capacity, registration stats, etc.
    """
    event_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
