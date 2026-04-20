"""
Event service for business logic.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.event import Event, EventCategory
from app.repositories.event_repository import EventRepository, EventCategoryRepository
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
        """
        # Get event
        event = self.get_event_by_id(event_id)

        # Check permission (admin or organizer)
        self.check_admin_or_organizer(event, current_user)

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


class CategoryService(BaseService):
    """Service for event category-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the CategoryService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = EventCategoryRepository(db)
        self.event_repository = EventRepository(db)

    def create_category(self, event_id: int, category_data: Dict[str, Any], current_user_id: int) -> EventCategory:
        """
        Create a new event category.

        Args:
            event_id: Event ID
            category_data: Dictionary of category fields
            current_user_id: ID of the user making the request

        Returns:
            Created EventCategory instance

        Raises:
            NotFoundException: If event not found
            PermissionDeniedException: If user is not the event organizer
            AlreadyExistsException: If category name already exists for the event
        """
        # Get event and check permission
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event", event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_category_management(event, current_user_id)

        # Check if category name already exists for this event
        if "name" in category_data:
            if self.repository.category_exists(event_id, category_data["name"]):
                raise AlreadyExistsException("Category", "name", category_data["name"])

        # Set event_id and initial values
        category_data["event_id"] = event_id
        category_data.setdefault("current_participants", 0)

        # Create category
        category = self.repository.create(category_data)
        return category

    def get_category_by_id(self, category_id: int) -> EventCategory:
        """
        Get a category by ID.

        Args:
            category_id: Category ID

        Returns:
            EventCategory instance

        Raises:
            NotFoundException: If category not found
        """
        return self.get_or_404(self.repository, category_id, "Category")

    def get_categories_by_event(self, event_id: int) -> List[EventCategory]:
        """
        Get all categories for an event.

        Args:
            event_id: Event ID

        Returns:
            List of EventCategory instances
        """
        return self.repository.get_categories_by_event(event_id)

    def update_category(self, category_id: int, update_data: Dict[str, Any], current_user_id: int) -> EventCategory:
        """
        Update a category.

        Args:
            category_id: Category ID to update
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated EventCategory instance

        Raises:
            NotFoundException: If category not found
            PermissionDeniedException: If user is not the event organizer
            AlreadyExistsException: If category name already exists
        """
        # Get category
        category = self.get_category_by_id(category_id)

        # Get event and check permission
        event = self.event_repository.get_by_id(category.event_id)
        if not event:
            raise NotFoundException("Event", category.event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_category_management(event, current_user_id)

        # Validate name uniqueness if updating name
        if "name" in update_data and update_data["name"] != category.name:
            if self.repository.category_exists(category.event_id, update_data["name"], exclude_id=category_id):
                raise AlreadyExistsException("Category", "name", update_data["name"])

        # Don't allow updating event_id directly
        update_data.pop("event_id", None)

        # Update category
        updated_category = self.repository.update(category_id, update_data)
        return updated_category

    def delete_category(self, category_id: int, current_user_id: int) -> bool:
        """
        Delete a category.

        Args:
            category_id: Category ID to delete
            current_user_id: ID of the user making the request

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If category not found
            PermissionDeniedException: If user is not the event organizer
        """
        # Get category
        category = self.get_category_by_id(category_id)

        # Get event and check permission
        event = self.event_repository.get_by_id(category.event_id)
        if not event:
            raise NotFoundException("Event", category.event_id)

        from app.core.permissions import PermissionChecker
        PermissionChecker.require_category_management(event, current_user_id)

        # Delete category
        return self.repository.delete(category_id)
