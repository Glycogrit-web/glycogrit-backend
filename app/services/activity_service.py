"""
Activity service for business logic.
"""

from typing import List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.models.user_activity_log import UserActivityLog
from app.models.activity_progress import ActivityProgress
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

        # Update ActivityProgress if exists
        self._update_activity_progress(user_id, event_id)

        return activity

    def _update_activity_progress(self, user_id: int, event_id: int) -> None:
        """
        Update ActivityProgress by aggregating user_activity_logs.

        Args:
            user_id: User ID
            event_id: Event ID
        """
        # Get the activity_progress record for this user/event
        progress = self.db.query(ActivityProgress).filter(
            ActivityProgress.user_id == user_id,
            ActivityProgress.event_id == event_id
        ).first()

        if not progress:
            return  # No progress record, skip

        # Calculate aggregates from user_activity_logs
        stats = self.db.query(
            func.sum(UserActivityLog.distance).label('total_distance'),
            func.count(UserActivityLog.id).label('total_activities'),
            func.sum(UserActivityLog.duration_minutes).label('total_duration')
        ).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.event_id == event_id
        ).first()

        total_distance = Decimal(str(stats.total_distance or 0))
        total_activities = stats.total_activities or 0
        total_duration = stats.total_duration or 0

        # Update progress (progress_percentage and is_completed are now computed properties)
        progress.distance_completed = total_distance

        # DEPRECATED: Stats now stored in distance_by_source
        # progress.total_activities = total_activities
        # progress.total_duration_minutes = total_duration

        # Set completed_at if just completed (is_completed is now a computed property)
        if progress.is_completed and not progress.completed_at:
            progress.completed_at = datetime.utcnow()

        progress.last_sync_at = datetime.utcnow()
        progress.sync_source = 'manual'
        progress.updated_at = datetime.utcnow()

        self.db.commit()

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
