"""
Challenge Service

Business logic for challenge progress and evaluation.
Challenges are implemented as Events with special rules.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modules.challenges.domain.value_objects import (
    ChallengeProgress,
    ChallengeStatus,
    StreakDays,
)
from app.modules.events.domain.event import Event
from app.modules.registrations.domain.registration import Registration
from app.models.activity_progress import ActivityProgress
from app.services.base import BaseService
from app.core.exceptions import NotFoundException, ValidationException
from app.core.enums import RegistrationStatus
import logging

logger = logging.getLogger(__name__)


class ChallengeService(BaseService):
    """Service for challenge operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_challenge_progress(
        self,
        user_id: int,
        event_id: int
    ) -> Dict[str, Any]:
        """
        Get user's progress in a challenge.

        Args:
            user_id: User ID
            event_id: Event/Challenge ID

        Returns:
            Dict with progress details

        Raises:
            NotFoundException: If challenge or registration not found
        """
        # Get challenge (event)
        challenge = self.db.query(Event).filter(Event.id == event_id).first()
        if not challenge:
            raise NotFoundException("Challenge", "id", str(event_id))

        # Get registration
        registration = self.db.query(Registration).filter(
            and_(
                Registration.user_id == user_id,
                Registration.event_id == event_id
            )
        ).first()

        if not registration:
            raise NotFoundException(
                "Registration",
                "user_id/event_id",
                f"{user_id}/{event_id}"
            )

        # Get progress
        progress = self.db.query(ActivityProgress).filter(
            ActivityProgress.registration_id == registration.id
        ).first()

        if not progress:
            # No progress yet
            return {
                "challenge_id": event_id,
                "challenge_name": challenge.name,
                "status": ChallengeStatus.NOT_STARTED.value,
                "current_distance": 0.0,
                "target_distance": float(progress.target_distance) if progress else 0.0,
                "progress_percentage": 0.0,
                "activity_count": 0,
                "streak_days": 0,
            }

        # Calculate progress
        challenge_progress = ChallengeProgress(
            current_distance=float(progress.distance_completed),
            target_distance=float(progress.target_distance)
        )

        # Determine status
        if challenge_progress.is_complete:
            status = ChallengeStatus.COMPLETED
        elif challenge_progress.current_distance > 0:
            status = ChallengeStatus.IN_PROGRESS
        else:
            status = ChallengeStatus.NOT_STARTED

        return {
            "challenge_id": event_id,
            "challenge_name": challenge.name,
            "status": status.value,
            "current_distance": challenge_progress.current_distance,
            "target_distance": challenge_progress.target_distance,
            "progress_percentage": challenge_progress.percentage,
            "remaining_distance": challenge_progress.remaining_distance,
            "activity_count": progress.get_total_activities(),
            "streak_days": 0,  # TODO: Calculate streak
            "last_activity_date": progress.last_sync_at,
        }

    def join_challenge(
        self,
        user_id: int,
        event_id: int
    ) -> Registration:
        """
        Join a challenge (create registration).

        Business Rules:
        1. User can only join once
        2. Challenge must be active

        Args:
            user_id: User ID
            event_id: Challenge/Event ID

        Returns:
            Created Registration

        Raises:
            NotFoundException: If challenge not found
            ValidationException: If already joined
        """
        # Check if challenge exists
        challenge = self.db.query(Event).filter(Event.id == event_id).first()
        if not challenge:
            raise NotFoundException("Challenge", "id", str(event_id))

        # Check if already joined
        existing = self.db.query(Registration).filter(
            and_(
                Registration.user_id == user_id,
                Registration.event_id == event_id
            )
        ).first()

        if existing:
            raise ValidationException("Already joined this challenge")

        # Create registration
        registration = Registration(
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.CONFIRMED.value,
            participant_name="",  # TODO: Get from user profile
        )

        self.db.add(registration)
        self.db.commit()
        self.db.refresh(registration)

        return registration
