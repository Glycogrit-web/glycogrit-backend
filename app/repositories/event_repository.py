"""
Event repository for database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from datetime import datetime

from app.models.event import Event, EventActivity
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event model with event-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the EventRepository.

        Args:
            db: Database session
        """
        super().__init__(Event, db)

    def get_by_id(self, id: int) -> Optional[Event]:
        """
        Retrieve an event by its ID with tiers and activities eagerly loaded.

        Args:
            id: Event ID

        Returns:
            Event instance if found, None otherwise
        """
        return self.db.query(Event).options(
            joinedload(Event.registration_tiers),
            joinedload(Event.activities)
        ).filter(Event.id == id).first()

    def get_by_slug(self, slug: str) -> Optional[Event]:
        """
        Retrieve an event by its slug.

        Args:
            slug: Event slug to search for

        Returns:
            Event instance if found, None otherwise
        """
        return self.db.query(Event).filter(Event.slug == slug).first()

    def slug_exists(self, slug: str, exclude_id: Optional[int] = None) -> bool:
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

    def get_events_by_organizer(self, organizer_id: int, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get all events organized by a specific user.

        Args:
            organizer_id: Organizer user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return self.db.query(Event).filter(
            Event.organizer_id == organizer_id
        ).offset(skip).limit(limit).all()

    def get_featured_events(self, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get all featured events.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of featured Event instances
        """
        return self.db.query(Event).filter(
            Event.is_featured == True
        ).offset(skip).limit(limit).all()

    def get_events_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get events by status.

        Args:
            status: Event status (draft, published, cancelled, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return self.db.query(Event).filter(
            Event.status == status
        ).offset(skip).limit(limit).all()

    def get_events_by_location(self, city: Optional[str] = None, state: Optional[str] = None,
                               country: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Event]:
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

    def get_upcoming_events(self, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get upcoming events (start_date in the future).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of upcoming Event instances
        """
        today = datetime.now().date()
        return self.db.query(Event).filter(
            Event.event_date >= today
        ).order_by(Event.event_date).offset(skip).limit(limit).all()

    def search_events(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Search events by name, description, or location.

        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances matching the search term
        """
        search_pattern = f"%{search_term}%"
        return self.db.query(Event).filter(
            or_(
                Event.name.ilike(search_pattern),
                Event.description.ilike(search_pattern),
                Event.location_name.ilike(search_pattern),
                Event.city.ilike(search_pattern)
            )
        ).offset(skip).limit(limit).all()

    def get_events_with_filters(
        self,
        city: Optional[str] = None,
        is_featured: Optional[bool] = None,
        difficulty: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
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
        query = self.db.query(Event).options(
            joinedload(Event.activities)
        )

        if city:
            query = query.filter(Event.city == city)
        if is_featured is not None:
            query = query.filter(Event.is_featured == is_featured)
        if difficulty:
            query = query.filter(Event.difficulty_level == difficulty)

        return query.offset(skip).limit(limit).all()


class EventActivityRepository(BaseRepository[EventActivity]):
    """Repository for EventActivity model with activity-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the EventActivityRepository.

        Args:
            db: Database session
        """
        super().__init__(EventActivity, db)

    def get_activities_by_event(self, event_id: int) -> List[EventActivity]:
        """
        Get all activities for a specific event.

        Args:
            event_id: Event ID

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            EventActivity.event_id == event_id
        ).all()

    def get_activity_by_name(self, event_id: int, name: str) -> Optional[EventActivity]:
        """
        Get an activity by event ID and name.

        Args:
            event_id: Event ID
            name: Activity name

        Returns:
            EventActivity instance if found, None otherwise
        """
        return self.db.query(EventActivity).filter(
            and_(
                EventActivity.event_id == event_id,
                EventActivity.name == name
            )
        ).first()

    def activity_exists(self, event_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if an activity name already exists for an event.

        Args:
            event_id: Event ID
            name: Activity name
            exclude_id: Optional activity ID to exclude from the check (for updates)

        Returns:
            True if activity exists, False otherwise
        """
        query = self.db.query(EventActivity).filter(
            and_(
                EventActivity.event_id == event_id,
                EventActivity.name == name
            )
        )
        if exclude_id:
            query = query.filter(EventActivity.id != exclude_id)
        return query.count() > 0

    def get_activities_by_type(self, event_id: int, activity_type: str) -> List[EventActivity]:
        """
        Get all activities of a specific type for an event.

        Args:
            event_id: Event ID
            activity_type: Activity type (running, cycling, etc.)

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            and_(
                EventActivity.event_id == event_id,
                EventActivity.activity_type == activity_type
            )
        ).all()
