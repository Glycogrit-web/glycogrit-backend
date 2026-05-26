"""
Query objects for Registration Service.

Queries represent read operations that don't modify state.
"""

from dataclasses import dataclass


@dataclass
class GetRegistrationByIdQuery:
    """
    Query to get a registration by ID.
    """

    registration_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")


@dataclass
class GetRegistrationByNumberQuery:
    """
    Query to get a registration by registration number.
    """

    registration_number: str

    def __post_init__(self):
        """Validate query data"""
        if not self.registration_number:
            raise ValueError("registration_number is required")


@dataclass
class GetUserRegistrationsQuery:
    """
    Query to get all registrations for a user.
    """

    user_id: int
    skip: int = 0
    limit: int = 100
    status_filter: str | None = None

    def __post_init__(self):
        """Validate query data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetEventRegistrationsQuery:
    """
    Query to get all registrations for an event.
    """

    event_id: int
    skip: int = 0
    limit: int = 100
    status_filter: str | None = None
    tier_id_filter: int | None = None

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.tier_id_filter is not None and self.tier_id_filter <= 0:
            raise ValueError("tier_id_filter must be positive if provided")


@dataclass
class GetEventRegistrationsWithProgressQuery:
    """
    Query to get event registrations with activity progress.

    Used for leaderboards and progress tracking.
    """

    event_id: int
    skip: int = 0
    limit: int = 100
    activity_id: int | None = None
    sort_by: str = "distance_desc"  # Options: distance_desc, distance_asc, name_asc

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.activity_id is not None and self.activity_id <= 0:
            raise ValueError("activity_id must be positive if provided")

        valid_sort_options = ["distance_desc", "distance_asc", "name_asc", "progress_desc"]
        if self.sort_by not in valid_sort_options:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")


@dataclass
class GetUserRegistrationForEventQuery:
    """
    Query to check if a user is registered for a specific event.
    """

    user_id: int
    event_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")


@dataclass
class GetTierHistoryQuery:
    """
    Query to get tier upgrade history for a registration.
    """

    registration_id: int
    user_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class GetStaleRegistrationsQuery:
    """
    Query to get stale pending registrations.

    Used for cleanup jobs that cancel old unpaid registrations.
    """

    max_age_hours: int = 48
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if self.max_age_hours <= 0:
            raise ValueError("max_age_hours must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetRegistrationsByStatusQuery:
    """
    Query to get registrations by status.
    """

    status: str
    event_id: int | None = None
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if not self.status:
            raise ValueError("status is required")
        if self.event_id is not None and self.event_id <= 0:
            raise ValueError("event_id must be positive if provided")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetTierRegistrationCountQuery:
    """
    Query to get registration count for a specific tier.
    """

    tier_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.tier_id <= 0:
            raise ValueError("tier_id must be positive")


@dataclass
class GetEventTierStatisticsQuery:
    """
    Query to get statistics for all tiers in an event.

    Returns counts, capacity, and revenue per tier.
    """

    event_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")


@dataclass
class SearchRegistrationsQuery:
    """
    Query to search registrations by various criteria.
    """

    search_term: str
    event_id: int | None = None
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if not self.search_term or len(self.search_term.strip()) < 2:
            raise ValueError("search_term must be at least 2 characters")
        if self.event_id is not None and self.event_id <= 0:
            raise ValueError("event_id must be positive if provided")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
