"""
Event service for business logic.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.modules.events.domain.event import Event, EventActivity
from app.modules.events.repositories.event_repository import EventRepository, EventActivityRepository
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    PermissionDeniedException
)


class EventService(BaseService):
    """Service for event-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the EventService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = EventRepository(db)

    def create_event(self, event_data: Dict[str, Any], organizer_id: int) -> Event:
        """
        Create a new event.

        Args:
            event_data: Dictionary of event fields
            organizer_id: ID of the user creating the event (organizer)

        Returns:
            Created Event instance

        Raises:
            AlreadyExistsException: If slug already exists
        """
        # Check if slug already exists
        if "slug" in event_data and self.repository.slug_exists(event_data["slug"]):
            raise AlreadyExistsException("Event", "slug", event_data["slug"])

        # Set organizer_id and initial values
        event_data["organizer_id"] = organizer_id
        event_data.setdefault("current_participants", 0)

        # Remove activity_types if provided (activities are now managed separately via EventActivity)
        event_data.pop("activity_types", None)

        # Create event
        event = self.repository.create(event_data)

        return event

    def get_event_by_id(self, event_id: int) -> Event:
        """
        Get an event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event instance

        Raises:
            NotFoundException: If event not found
        """
        return self.get_or_404(self.repository, event_id, "Event")

    def get_event_by_slug(self, slug: str) -> Event:
        """
        Get an event by slug.

        Args:
            slug: Event slug

        Returns:
            Event instance

        Raises:
            NotFoundException: If event not found
        """
        event = self.repository.get_by_slug(slug)
        if not event:
            raise NotFoundException("Event", slug)
        return event

    def update_event(self, event_id: int, update_data: Dict[str, Any], current_user) -> Event:
        """
        Update an event.

        Args:
            event_id: Event ID to update
            update_data: Dictionary of fields to update
            current_user: User model instance making the request

        Returns:
            Updated Event instance

        Raises:
            NotFoundException: If event not found
            PermissionDeniedException: If user is not the organizer or admin
            AlreadyExistsException: If slug already exists
        """
        # Get event
        event = self.get_event_by_id(event_id)

        # Check permission (admin or organizer)
        self.check_admin_or_organizer(event, current_user)

        # Validate slug uniqueness if updating slug
        if "slug" in update_data and update_data["slug"] != event.slug:
            if self.repository.slug_exists(update_data["slug"], exclude_id=event_id):
                raise AlreadyExistsException("Event", "slug", update_data["slug"])

        # Don't allow updating organizer_id directly
        update_data.pop("organizer_id", None)

        # Remove activity_types if provided (activities are now managed separately via EventActivity)
        update_data.pop("activity_types", None)

        # Update event
        updated_event = self.repository.update(event_id, update_data)

        return updated_event

    def delete_event(self, event_id: int, current_user) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event ID to delete
            current_user: User model instance making the request

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If event not found
            PermissionDeniedException: If user is not the organizer or admin
            ValueError: If event has existing registrations
        """
        from app.modules.registrations.domain.registration import Registration

        # Get event
        event = self.get_event_by_id(event_id)

        # Check permission (admin or organizer)
        self.check_admin_or_organizer(event, current_user)

        # Check if event has any registrations
        has_registrations = self.db.query(Registration).filter(
            Registration.event_id == event_id
        ).first() is not None

        if has_registrations:
            raise ValueError("Cannot delete event with existing registrations. Please cancel or refund all registrations first.")

        # Delete event
        return self.repository.delete(event_id)

    def get_all_events(self, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get all events with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return self.repository.get_all(skip, limit)

    def get_events_by_organizer(self, organizer_id: int, skip: int = 0, limit: int = 100) -> List[Event]:
        """
        Get events by organizer.

        Args:
            organizer_id: Organizer user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances
        """
        return self.repository.get_events_by_organizer(organizer_id, skip, limit)

    def get_events_with_filters(
        self,
        event_type: Optional[str] = None,
        city: Optional[str] = None,
        is_featured: Optional[bool] = None,
        difficulty: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events with filters.

        Args:
            event_type: Optional event type filter
            city: Optional city filter
            is_featured: Optional featured filter
            difficulty: Optional difficulty level filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances matching the filters
        """
        return self.repository.get_events_with_filters(
            event_type=event_type,
            city=city,
            is_featured=is_featured,
            difficulty=difficulty,
            skip=skip,
            limit=limit
        )

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
        return self.repository.search_events(search_term, skip, limit)


class ActivityService(BaseService):
    """Service for event activity-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the ActivityService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = EventActivityRepository(db)
        self.event_repository = EventRepository(db)

    def create_activity(self, event_id: int, activity_data: Dict[str, Any], current_user_id: int) -> EventActivity:
        """
        Create a new event activity.

        Args:
            event_id: Event ID
            activity_data: Dictionary of activity fields
            current_user_id: ID of the user making the request

        Returns:
            Created EventActivity instance

        Raises:
            NotFoundException: If event not found
            PermissionDeniedException: If user is not the event organizer
            AlreadyExistsException: If activity name already exists for the event
        """
        # Get event and check permission
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event", event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_activity_management(event, current_user_id)

        # Check if activity name already exists for this event
        if "name" in activity_data:
            if self.repository.activity_exists(event_id, activity_data["name"]):
                raise AlreadyExistsException("Activity", "name", activity_data["name"])

        # Set event_id and initial values
        activity_data["event_id"] = event_id
        activity_data.setdefault("current_participants", 0)

        # Create activity
        activity = self.repository.create(activity_data)
        return activity

    def get_activity_by_id(self, activity_id: int) -> EventActivity:
        """
        Get an activity by ID.

        Args:
            activity_id: Activity ID

        Returns:
            EventActivity instance

        Raises:
            NotFoundException: If activity not found
        """
        return self.get_or_404(self.repository, activity_id, "Activity")

    def get_activities_by_event(self, event_id: int) -> List[EventActivity]:
        """
        Get all activities for an event.

        Args:
            event_id: Event ID

        Returns:
            List of EventActivity instances
        """
        return self.repository.get_activities_by_event(event_id)

    def update_activity(self, activity_id: int, update_data: Dict[str, Any], current_user_id: int) -> EventActivity:
        """
        Update an activity.

        Args:
            activity_id: Activity ID to update
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated EventActivity instance

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user is not the event organizer
            AlreadyExistsException: If activity name already exists
        """
        # Get activity
        activity = self.get_activity_by_id(activity_id)

        # Get event and check permission
        event = self.event_repository.get_by_id(activity.event_id)
        if not event:
            raise NotFoundException("Event", activity.event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_activity_management(event, current_user_id)

        # Validate name uniqueness if updating name
        if "name" in update_data and update_data["name"] != activity.name:
            if self.repository.activity_exists(activity.event_id, update_data["name"], exclude_id=activity_id):
                raise AlreadyExistsException("Activity", "name", update_data["name"])

        # Don't allow updating event_id directly
        update_data.pop("event_id", None)

        # Update activity
        updated_activity = self.repository.update(activity_id, update_data)
        return updated_activity

    def delete_activity(self, activity_id: int, current_user_id: int) -> bool:
        """
        Delete an activity.

        Args:
            activity_id: Activity ID to delete
            current_user_id: ID of the user making the request

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user is not the event organizer
        """
        # Get activity
        activity = self.get_activity_by_id(activity_id)

        # Get event and check permission
        event = self.event_repository.get_by_id(activity.event_id)
        if not event:
            raise NotFoundException("Event", activity.event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_activity_management(event, current_user_id)

        # Delete activity
        return self.repository.delete(activity_id)
