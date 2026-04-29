"""
Activity service for business logic.
"""

from typing import List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session

from app.models.user_activity_log import UserActivityLog
from app.repositories.activity_repository import ActivityRepository
from app.repositories.event_repository import EventRepository
from app.services.base import BaseService
from app.core.exceptions import NotFoundException
from app.core.permissions import PermissionChecker


class ActivityService(BaseService):
    """Service for activity-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the ActivityService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = ActivityRepository(db)
        self.event_repository = EventRepository(db)

    def create_activity(
        self,
        user_id: int,
        event_id: int,
        activity_data: Dict[str, Any]
    ) -> UserActivityLog:
        """
        Create a new activity.

        Args:
            user_id: User ID
            event_id: Event ID
            activity_data: Dictionary of activity fields

        Returns:
            Created UserActivityLog instance

        Raises:
            NotFoundException: If event not found
        """
        # Verify event exists
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event", event_id)

        # Set user_id and event_id
        activity_data["user_id"] = user_id
        activity_data["event_id"] = event_id

        # Create activity
        activity = self.repository.create(activity_data)
        return activity

    def get_activity_by_id(self, activity_id: int) -> UserActivityLog:
        """
        Get an activity by ID.

        Args:
            activity_id: Activity ID

        Returns:
            UserActivityLog instance

        Raises:
            NotFoundException: If activity not found
        """
        return self.get_or_404(self.repository, activity_id, "Activity")

    def update_activity(
        self, activity_id: int, update_data: Dict[str, Any], current_user_id: int
    ) -> UserActivityLog:
        """
        Update an activity.

        Args:
            activity_id: Activity ID
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated UserActivityLog instance

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user doesn't own the activity
        """
        # Get activity
        activity = self.get_activity_by_id(activity_id)

        # Check ownership
        PermissionChecker.require_activity_owner(activity, current_user_id)

        # Don't allow updating certain fields
        protected_fields = ["id", "user_id", "event_id", "created_at"]
        for field in protected_fields:
            update_data.pop(field, None)

        # Update activity
        updated_activity = self.repository.update(activity_id, update_data)
        return updated_activity

    def delete_activity(self, activity_id: int, current_user_id: int) -> bool:
        """
        Delete an activity.

        Args:
            activity_id: Activity ID
            current_user_id: ID of the user making the request

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user doesn't own the activity
        """
        # Get activity
        activity = self.get_activity_by_id(activity_id)

        # Check ownership
        PermissionChecker.require_activity_owner(activity, current_user_id)

        # Delete activity
        return self.repository.delete(activity_id)

    def get_activities_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[UserActivityLog]:
        """
        Get all activities for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_activities_by_user(user_id, skip, limit)

    def get_activities_by_event(self, event_id: int, skip: int = 0, limit: int = 100) -> List[UserActivityLog]:
        """
        Get all activities for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_activities_by_event(event_id, skip, limit)

    def get_activities_by_user_and_event(
        self, user_id: int, event_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserActivityLog]:
        """
        Get activities for a specific user in a specific event.

        Args:
            user_id: User ID
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_activities_by_user_and_event(user_id, event_id, skip, limit)
