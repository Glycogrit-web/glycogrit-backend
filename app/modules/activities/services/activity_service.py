"""
Activity Service - Business logic for activity management

Implements CQRS pattern with commands and queries.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyExistsException,
    PermissionDeniedException,
    ValidationException,
)
from app.models.user_activity_log import UserActivityLog
from app.modules.activities.domain.value_objects import ActivityDate
from app.modules.activities.repositories.activity_repository import ActivityRepository
from app.modules.activities.services.commands import (
    DeleteActivityCommand,
    SubmitActivityCommand,
    UpdateActivityCommand,
)
from app.modules.activities.services.queries import (
    GetActivitiesByDateRangeQuery,
    GetActivityQuery,
    GetActivityStatsQuery,
    GetEventActivitiesQuery,
    GetUserActivitiesQuery,
)
from app.services.base import BaseService


class ActivityService(BaseService):
    """Service for activity-related business logic using CQRS pattern."""

    def __init__(self, db: Session):
        """
        Initialize the ActivityService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = ActivityRepository(db)

    # COMMAND HANDLERS (Write Operations)

    def handle_submit_activity(self, command: SubmitActivityCommand) -> UserActivityLog:
        """
        Handle SubmitActivityCommand.

        Business Rules:
        1. Activity date cannot be in future
        2. No duplicate activities for same date
        3. Distance and duration must be non-negative

        Args:
            command: SubmitActivityCommand

        Returns:
            Created UserActivityLog instance

        Raises:
            ValidationException: If date is invalid or duplicate exists
        """
        # Validate activity date
        try:
            ActivityDate(command.activity_date)
        except ValueError as e:
            raise ValidationException(str(e))

        # Check for duplicate
        if self.repository.activity_exists(
            command.user_id,
            command.event_id,
            command.activity_date
        ):
            raise AlreadyExistsException(
                "Activity",
                "date",
                command.activity_date.isoformat()
            )

        # Create activity data
        activity_data = {
            "user_id": command.user_id,
            "event_id": command.event_id,
            "activity_date": command.activity_date,
            "distance": command.distance,
            "duration": command.duration,
            "notes": command.notes,
            "registration_id": command.registration_id,
        }

        return self.repository.create(activity_data)

    def handle_update_activity(self, command: UpdateActivityCommand) -> UserActivityLog:
        """
        Handle UpdateActivityCommand.

        Business Rules:
        1. Only owner can update activity
        2. Activity date validation if being updated

        Args:
            command: UpdateActivityCommand

        Returns:
            Updated UserActivityLog instance

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user doesn't own activity
        """
        # Get activity
        activity = self.get_or_404(self.repository, command.activity_id, "Activity")

        # Check ownership
        if activity.user_id != command.current_user_id:
            raise PermissionDeniedException("You can only update your own activities")

        # Validate activity date if being updated
        if command.activity_date:
            try:
                ActivityDate(command.activity_date)
            except ValueError as e:
                raise ValidationException(str(e))

        # Build update data
        update_data = {}
        if command.distance is not None:
            update_data["distance"] = command.distance
        if command.duration is not None:
            update_data["duration"] = command.duration
        if command.activity_date is not None:
            update_data["activity_date"] = command.activity_date
        if command.notes is not None:
            update_data["notes"] = command.notes

        return self.repository.update(command.activity_id, update_data)

    def handle_delete_activity(self, command: DeleteActivityCommand) -> bool:
        """
        Handle DeleteActivityCommand.

        Business Rule: Only owner can delete activity

        Args:
            command: DeleteActivityCommand

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If activity not found
            PermissionDeniedException: If user doesn't own activity
        """
        # Get activity
        activity = self.get_or_404(self.repository, command.activity_id, "Activity")

        # Check ownership
        if activity.user_id != command.current_user_id:
            raise PermissionDeniedException("You can only delete your own activities")

        # Delete activity
        self.repository.delete(command.activity_id)
        return True

    # QUERY HANDLERS (Read Operations)

    def handle_get_activity(self, query: GetActivityQuery) -> UserActivityLog:
        """
        Handle GetActivityQuery.

        Args:
            query: GetActivityQuery

        Returns:
            UserActivityLog instance

        Raises:
            NotFoundException: If activity not found
        """
        return self.get_or_404(self.repository, query.activity_id, "Activity")

    def handle_get_user_activities(
        self,
        query: GetUserActivitiesQuery
    ) -> list[UserActivityLog]:
        """
        Handle GetUserActivitiesQuery.

        Args:
            query: GetUserActivitiesQuery

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_user_activities(
            query.user_id,
            query.skip,
            query.limit
        )

    def handle_get_event_activities(
        self,
        query: GetEventActivitiesQuery
    ) -> list[UserActivityLog]:
        """
        Handle GetEventActivitiesQuery.

        Args:
            query: GetEventActivitiesQuery

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_event_activities(
            query.user_id,
            query.event_id,
            query.skip,
            query.limit
        )

    def handle_get_activities_by_date_range(
        self,
        query: GetActivitiesByDateRangeQuery
    ) -> list[UserActivityLog]:
        """
        Handle GetActivitiesByDateRangeQuery.

        Args:
            query: GetActivitiesByDateRangeQuery

        Returns:
            List of UserActivityLog instances
        """
        return self.repository.get_activities_by_date_range(
            query.user_id,
            query.event_id,
            query.start_date,
            query.end_date
        )

    def handle_get_activity_stats(
        self,
        query: GetActivityStatsQuery
    ) -> dict[str, Any]:
        """
        Handle GetActivityStatsQuery.

        Args:
            query: GetActivityStatsQuery

        Returns:
            Dictionary with activity statistics
        """
        total_distance = self.repository.get_total_distance(
            query.user_id,
            query.event_id
        )
        total_duration = self.repository.get_total_duration(
            query.user_id,
            query.event_id
        )
        activity_count = self.repository.count_user_activities(
            query.user_id,
            query.event_id
        )

        return {
            "total_distance_km": total_distance,
            "total_duration_minutes": total_duration,
            "activity_count": activity_count,
            "average_distance_km": total_distance / activity_count if activity_count > 0 else 0,
            "average_duration_minutes": total_duration / activity_count if activity_count > 0 else 0,
        }
