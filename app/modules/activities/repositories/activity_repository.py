"""
Activity Repository - Data access layer for user activities

Handles all database operations for UserActivityLog.
"""

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.user_activity_log import UserActivityLog
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[UserActivityLog]):
    """Repository for UserActivityLog with activity-specific operations."""

    def __init__(self, db: Session):
        """
        Initialize the ActivityRepository.

        Args:
            db: Database session
        """
        super().__init__(UserActivityLog, db)

    def get_user_activities(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserActivityLog]:
        """
        Get all activities for a user with pagination.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserActivityLog instances
        """
        return self.db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id
        ).order_by(desc(UserActivityLog.activity_date)).offset(skip).limit(limit).all()

    def get_event_activities(
        self,
        user_id: int,
        event_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserActivityLog]:
        """
        Get all activities for a user in a specific event.

        Args:
            user_id: User ID
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserActivityLog instances
        """
        return self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id
            )
        ).order_by(desc(UserActivityLog.activity_date)).offset(skip).limit(limit).all()

    def get_activities_by_date_range(
        self,
        user_id: int,
        event_id: int,
        start_date: date,
        end_date: date
    ) -> List[UserActivityLog]:
        """
        Get activities within a date range.

        Args:
            user_id: User ID
            event_id: Event ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of UserActivityLog instances
        """
        return self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id,
                UserActivityLog.activity_date >= start_date,
                UserActivityLog.activity_date <= end_date
            )
        ).order_by(desc(UserActivityLog.activity_date)).all()

    def get_activity_by_date(
        self,
        user_id: int,
        event_id: int,
        activity_date: date
    ) -> Optional[UserActivityLog]:
        """
        Get activity for a specific date.

        Args:
            user_id: User ID
            event_id: Event ID
            activity_date: Activity date

        Returns:
            UserActivityLog instance if found, None otherwise
        """
        return self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id,
                UserActivityLog.activity_date == activity_date
            )
        ).first()

    def activity_exists(
        self,
        user_id: int,
        event_id: int,
        activity_date: date
    ) -> bool:
        """
        Check if activity exists for a specific date.

        Args:
            user_id: User ID
            event_id: Event ID
            activity_date: Activity date

        Returns:
            True if activity exists, False otherwise
        """
        return self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id,
                UserActivityLog.activity_date == activity_date
            )
        ).count() > 0

    def count_user_activities(self, user_id: int, event_id: Optional[int] = None) -> int:
        """
        Count activities for a user.

        Args:
            user_id: User ID
            event_id: Optional event ID to filter by

        Returns:
            Number of activities
        """
        query = self.db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id
        )

        if event_id:
            query = query.filter(UserActivityLog.event_id == event_id)

        return query.count()

    def get_total_distance(self, user_id: int, event_id: int) -> float:
        """
        Calculate total distance for user in event.

        Args:
            user_id: User ID
            event_id: Event ID

        Returns:
            Total distance in kilometers
        """
        from sqlalchemy import func

        result = self.db.query(
            func.sum(UserActivityLog.distance)
        ).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id
            )
        ).scalar()

        return float(result) if result else 0.0

    def get_total_duration(self, user_id: int, event_id: int) -> int:
        """
        Calculate total duration for user in event.

        Args:
            user_id: User ID
            event_id: Event ID

        Returns:
            Total duration in minutes
        """
        from sqlalchemy import func

        result = self.db.query(
            func.sum(UserActivityLog.duration)
        ).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.event_id == event_id
            )
        ).scalar()

        return int(result) if result else 0

    def delete_by_date(self, user_id: int, event_id: int, activity_date: date) -> bool:
        """
        Delete activity by date.

        Args:
            user_id: User ID
            event_id: Event ID
            activity_date: Activity date

        Returns:
            True if deleted, False if not found
        """
        activity = self.get_activity_by_date(user_id, event_id, activity_date)
        if activity:
            self.delete(activity.id)
            return True
        return False
