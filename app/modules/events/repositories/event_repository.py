"""
Event repository for database operations.
"""

from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.core.repository.base import BaseRepository
from app.modules.events.domain.event import Event, EventActivity


class EventRepository(BaseRepository[Event]):
    """Repository for Event model with event-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the EventRepository.

        Args:
            db: Database session
        """
        super().__init__(Event, db)

    def get_by_id(self, id: int) -> Event | None:
        """
        Retrieve an event by its ID with tiers eagerly loaded.

        Args:
            id: Event ID

        Returns:
            Event instance if found, None otherwise
        """
        return (
            self.db.query(Event)
            .options(joinedload(Event.registration_tiers))
            .filter(Event.id == id)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Retrieve all events with eager loading of relationships.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of Event instances with preloaded relationships
        """
        return (
            self.db.query(Event)
            .options(
                joinedload(Event.registration_tiers),
                joinedload(Event.activities)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_slug(self, slug: str) -> Event | None:
        """
        Retrieve an event by its slug.

        Args:
            slug: Event slug to search for

        Returns:
            Event instance if found, None otherwise
        """
        return self.db.query(Event).filter(Event.slug == slug).first()

    def slug_exists(self, slug: str, exclude_id: int | None = None) -> bool:
        """
        Check if a slug already exists.

        Args:
            slug: Slug to check
            exclude_id: Optional event ID to exclude from the check (for updates)

        Returns:
            True if slug exists, False otherwise
        """
        query = self.db.query(Event).filter(Event.slug == slug)
        if exclude_id:
            query = query.filter(Event.id != exclude_id)
        return query.count() > 0

    def get_events_by_organizer(
        self, organizer_id: int, skip: int = 0, limit: int = 100
    ) -> list[Event]:
        """
        Get all events organized by a specific user.

        Args:
            organizer_id: Organizer user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return (
            self.db.query(Event)
            .filter(Event.organizer_id == organizer_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_featured_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Get all featured events with eager loading.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of featured Event instances with preloaded relationships
        """
        return (
            self.db.query(Event)
            .options(
                joinedload(Event.registration_tiers),
                joinedload(Event.activities)
            )
            .filter(Event.is_featured)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_events_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Get events by status.

        Args:
            status: Event status (draft, published, cancelled, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return self.db.query(Event).filter(Event.status == status).offset(skip).limit(limit).all()

    def get_events_by_location(
        self,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get events by location.

        Args:
            city: Optional city filter
            state: Optional state filter
            country: Optional country filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        query = self.db.query(Event)

        if city:
            query = query.filter(Event.city == city)
        if state:
            query = query.filter(Event.state == state)
        if country:
            query = query.filter(Event.country == country)

        return query.offset(skip).limit(limit).all()

    def get_upcoming_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Get upcoming events (start_date in the future).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of upcoming Event instances
        """
        today = datetime.now().date()
        return (
            self.db.query(Event)
            .filter(Event.event_date >= today)
            .order_by(Event.event_date)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_events(self, search_term: str, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Search events by name, description, or location with eager loading.

        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances matching the search term with preloaded relationships
        """
        search_pattern = f"%{search_term}%"
        return (
            self.db.query(Event)
            .options(
                joinedload(Event.registration_tiers),
                joinedload(Event.activities)
            )
            .filter(
                or_(
                    Event.name.ilike(search_pattern),
                    Event.description.ilike(search_pattern),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_events_with_filters(
        self,
        city: str | None = None,
        is_featured: bool | None = None,
        difficulty: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get events with multiple filters.

        Args:
            city: Optional city filter
            is_featured: Optional featured filter
            difficulty: Optional difficulty level filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances matching the filters
        """
        query = self.db.query(Event).options(joinedload(Event.registration_tiers))

        if city:
            query = query.filter(Event.city == city)
        if is_featured is not None:
            query = query.filter(Event.is_featured == is_featured)
        if difficulty:
            query = query.filter(Event.difficulty_level == difficulty)

        return query.offset(skip).limit(limit).all()

    def get_events_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Event]:
        """
        Get all events that a user has registered for.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances the user has registered for
        """
        from app.modules.registrations.domain.registration import Registration

        # Query events through registrations
        events = (
            self.db.query(Event)
            .join(Registration, Event.id == Registration.event_id)
            .filter(Registration.user_id == user_id)
            .options(joinedload(Event.registration_tiers))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return events


class EventActivityRepository(BaseRepository[EventActivity]):
    """Repository for EventActivity model with activity-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the EventActivityRepository.

        Args:
            db: Database session
        """
        super().__init__(EventActivity, db)

    def get_all_activities(self) -> list[EventActivity]:
        """
        Get all global activity templates.

        NOTE: Activities are now global templates, not event-specific.
        All events can use any of the available activities.

        Returns:
            List of all EventActivity instances
        """
        return self.db.query(EventActivity).order_by(EventActivity.activity_type, EventActivity.distance).all()

    def get_activity_by_name(self, name: str) -> EventActivity | None:
        """
        Get an activity by name.

        Args:
            name: Activity name

        Returns:
            EventActivity instance if found, None otherwise
        """
        return self.db.query(EventActivity).filter(EventActivity.name == name).first()

    def activity_exists(self, name: str, exclude_id: int | None = None) -> bool:
        """
        Check if an activity name already exists.

        Args:
            name: Activity name
            exclude_id: Optional activity ID to exclude from the check (for updates)

        Returns:
            True if activity exists, False otherwise
        """
        query = self.db.query(EventActivity).filter(EventActivity.name == name)
        if exclude_id:
            query = query.filter(EventActivity.id != exclude_id)
        return query.count() > 0

    def get_activities_by_type(self, activity_type: str) -> list[EventActivity]:
        """
        Get all activities of a specific type.

        Args:
            activity_type: Activity type (running, cycling, etc.)

        Returns:
            List of EventActivity instances
        """
        return (
            self.db.query(EventActivity)
            .filter(EventActivity.activity_type == activity_type)
            .order_by(EventActivity.distance)
            .all()
        )
