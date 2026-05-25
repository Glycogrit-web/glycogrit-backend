"""
Progress Repository - Data access layer for activity progress

Handles all database operations for ActivityProgress.
"""

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.repository.base import BaseRepository
from app.models.activity_progress import ActivityProgress


class ProgressRepository(BaseRepository[ActivityProgress]):
    """Repository for ActivityProgress with progress-specific operations."""

    def __init__(self, db: Session):
        """
        Initialize the ProgressRepository.

        Args:
            db: Database session
        """
        super().__init__(ActivityProgress, db)

    def get_by_registration(self, registration_id: int) -> ActivityProgress | None:
        """
        Get progress by registration ID.

        Args:
            registration_id: Registration ID

        Returns:
            ActivityProgress instance if found, None otherwise
        """
        return (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.registration_id == registration_id)
            .first()
        )

    def get_by_user_and_event(self, user_id: int, event_id: int) -> ActivityProgress | None:
        """
        Get progress for user in event.

        Args:
            user_id: User ID
            event_id: Event ID

        Returns:
            ActivityProgress instance if found, None otherwise
        """
        return (
            self.db.query(ActivityProgress)
            .filter(
                and_(ActivityProgress.user_id == user_id, ActivityProgress.event_id == event_id)
            )
            .first()
        )

    def get_user_progress(self, user_id: int, event_id: int) -> ActivityProgress | None:
        """
        Get progress for user in event (alias for get_by_user_and_event).

        Args:
            user_id: User ID
            event_id: Event ID

        Returns:
            ActivityProgress instance if found, None otherwise
        """
        return self.get_by_user_and_event(user_id, event_id)

    def get_user_progress_list(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[ActivityProgress]:
        """
        Get all progress records for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ActivityProgress instances
        """
        return (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_event_progress_list(
        self, event_id: int, skip: int = 0, limit: int = 100
    ) -> list[ActivityProgress]:
        """
        Get all progress records for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ActivityProgress instances
        """
        return (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.event_id == event_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_completed_progress(
        self, event_id: int | None = None, skip: int = 0, limit: int = 100
    ) -> list[ActivityProgress]:
        """
        Get all completed progress records.

        Args:
            event_id: Optional event ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of completed ActivityProgress instances
        """
        query = self.db.query(ActivityProgress).filter(ActivityProgress.completed_at.isnot(None))

        if event_id:
            query = query.filter(ActivityProgress.event_id == event_id)

        return query.offset(skip).limit(limit).all()

    def count_completed(self, event_id: int | None = None) -> int:
        """
        Count completed progress records.

        Args:
            event_id: Optional event ID to filter by

        Returns:
            Number of completed progress records
        """
        query = self.db.query(ActivityProgress).filter(ActivityProgress.completed_at.isnot(None))

        if event_id:
            query = query.filter(ActivityProgress.event_id == event_id)

        return query.count()

    def get_leaderboard(self, event_id: int, limit: int = 10) -> list[ActivityProgress]:
        """
        Get leaderboard (top progress) for an event.

        Args:
            event_id: Event ID
            limit: Maximum number of records to return

        Returns:
            List of ActivityProgress instances ordered by progress
        """
        return (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.event_id == event_id)
            .order_by(ActivityProgress.distance_completed.desc())
            .limit(limit)
            .all()
        )

    def progress_exists(self, registration_id: int) -> bool:
        """
        Check if progress exists for registration.

        Args:
            registration_id: Registration ID

        Returns:
            True if progress exists, False otherwise
        """
        return (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.registration_id == registration_id)
            .count()
            > 0
        )

    def get_average_progress(self, event_id: int) -> float:
        """
        Calculate average progress percentage for event.

        Args:
            event_id: Event ID

        Returns:
            Average progress percentage
        """
        from sqlalchemy import Float, cast, func

        result = (
            self.db.query(
                func.avg(
                    cast(ActivityProgress.distance_completed, Float)
                    / cast(ActivityProgress.target_distance, Float)
                    * 100
                )
            )
            .filter(ActivityProgress.event_id == event_id)
            .scalar()
        )

        return float(result) if result else 0.0
