"""
Activity repository for database operations.
"""

from typing import List
from datetime import date
from sqlalchemy.orm import Session

from app.models.activity import EventActivity
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[EventActivity]):
    """Repository for EventActivity model with activity-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the ActivityRepository.

        Args:
            db: Database session
        """
        super().__init__(EventActivity, db)

    def get_activities_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[EventActivity]:
        """
        Get all activities for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            EventActivity.user_id == user_id
        ).order_by(EventActivity.activity_date.desc()).offset(skip).limit(limit).all()

    def get_activities_by_event(self, event_id: int, skip: int = 0, limit: int = 100) -> List[EventActivity]:
        """
        Get all activities for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            EventActivity.event_id == event_id
        ).order_by(EventActivity.activity_date.desc()).offset(skip).limit(limit).all()

    def get_activities_by_user_and_event(
        self, user_id: int, event_id: int, skip: int = 0, limit: int = 100
    ) -> List[EventActivity]:
        """
        Get activities for a specific user in a specific event.

        Args:
            user_id: User ID
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            EventActivity.user_id == user_id,
            EventActivity.event_id == event_id
        ).order_by(EventActivity.activity_date.desc()).offset(skip).limit(limit).all()

    def get_activities_by_date_range(
        self, user_id: int, event_id: int, start_date: date, end_date: date
    ) -> List[EventActivity]:
        """
        Get activities within a date range.

        Args:
            user_id: User ID
            event_id: Event ID
            start_date: Start date
            end_date: End date

        Returns:
            List of EventActivity instances
        """
        return self.db.query(EventActivity).filter(
            EventActivity.user_id == user_id,
            EventActivity.event_id == event_id,
            EventActivity.activity_date >= start_date,
            EventActivity.activity_date <= end_date
        ).order_by(EventActivity.activity_date).all()
