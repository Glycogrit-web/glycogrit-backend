"""
Challenge Scheduler Service
Handles automatic challenge start/end based on dates
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.activity_progress import ActivityProgress
from app.modules.events.domain.event import Event, EventActivity
from app.modules.registrations.domain.registration import Registration

logger = logging.getLogger(__name__)


class ChallengeSchedulerService:
    """
    Service for automatically managing challenge lifecycle

    Responsibilities:
    - Auto-start challenges on start_date
    - Auto-complete challenges on end_date
    - Initialize user progress tracking when users join
    - Trigger evaluation when challenges complete
    """

    def __init__(self, db: Session):
        self.db = db

    def process_challenge_starts(self) -> list[int]:
        """
        Process challenges that should start today

        Returns:
            List of challenge IDs that were started
        """
        now = datetime.now(timezone.utc)
        today = now.date()

        # Find challenges that should start today but haven't been auto-started
        challenges_to_start = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.start_date == today,
                    Event.auto_started_at.is_(None),
                    Event.status == "upcoming",
                )
            )
            .all()
        )

        started_challenge_ids = []

        for challenge in challenges_to_start:
            try:
                self._start_challenge(challenge, now)
                started_challenge_ids.append(challenge.id)
                logger.info(f"Auto-started challenge: {challenge.id} - {challenge.name}")
            except Exception as e:
                logger.error(f"Error starting challenge {challenge.id}: {e}")

        self.db.commit()
        return started_challenge_ids

    def process_challenge_completions(self) -> list[int]:
        """
        Process challenges that should complete today

        Returns:
            List of challenge IDs that were completed
        """
        now = datetime.now(timezone.utc)
        today = now.date()

        # Find challenges that should complete today but haven't been auto-completed
        challenges_to_complete = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.end_date == today,
                    Event.auto_completed_at.is_(None),
                    Event.status == "ongoing",
                )
            )
            .all()
        )

        completed_challenge_ids = []

        for challenge in challenges_to_complete:
            try:
                self._complete_challenge(challenge, now)
                completed_challenge_ids.append(challenge.id)
                logger.info(f"Auto-completed challenge: {challenge.id} - {challenge.name}")
            except Exception as e:
                logger.error(f"Error completing challenge {challenge.id}: {e}")

        self.db.commit()
        return completed_challenge_ids

    def initialize_user_progress(self, user_id: int, challenge_id: int) -> ActivityProgress:
        """
        Initialize progress tracking when user joins a challenge
        Creates or finds Registration and ActivityProgress records

        Args:
            user_id: User ID
            challenge_id: Challenge/Event ID

        Returns:
            Created or existing ActivityProgress record
        """
        challenge = self.db.query(Event).filter(Event.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        # Check if registration exists
        registration = (
            self.db.query(Registration)
            .filter(and_(Registration.user_id == user_id, Registration.event_id == challenge_id))
            .first()
        )

        # If no registration, this is an error - user must register first
        if not registration:
            raise ValueError(f"User {user_id} not registered for challenge {challenge_id}")

        # Check if progress record already exists
        existing_progress = (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.registration_id == registration.id)
            .first()
        )

        if existing_progress:
            logger.info(f"Progress already exists for user {user_id} in challenge {challenge_id}")
            return existing_progress

        # Get the event activity (assuming one activity per event for now)
        event_activity = (
            self.db.query(EventActivity).filter(EventActivity.event_id == challenge_id).first()
        )

        if not event_activity:
            # Create a default activity if none exists
            logger.warning(
                f"No event_activity found for challenge {challenge_id}, creating default"
            )
            event_activity = EventActivity(
                event_id=challenge_id, name="Default Activity", distance=50.0  # Default 50km
            )
            self.db.add(event_activity)
            self.db.flush()

        # Extract goal from completion criteria or use event_activity distance
        target_distance = event_activity.distance or 50.0
        if challenge.completion_criteria:
            target_distance = challenge.completion_criteria.get("min_distance_km", target_distance)

        # Create new activity progress record
        progress = ActivityProgress(
            user_id=user_id,
            registration_id=registration.id,
            event_id=challenge_id,
            activity_id=event_activity.id,
            distance_completed=0.0,
            target_distance=target_distance,
            distance_by_source={},
        )

        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)

        logger.info(f"Initialized activity_progress for user {user_id} in challenge {challenge_id}")
        return progress

    def check_should_auto_start_now(self, challenge_id: int) -> bool:
        """
        Check if a challenge should be started immediately (past start date)

        Args:
            challenge_id: Challenge ID

        Returns:
            True if challenge should be started now
        """
        challenge = self.db.query(Event).filter(Event.id == challenge_id).first()
        if not challenge:
            return False

        now = datetime.now(timezone.utc)
        return (
            challenge.start_date
            and challenge.start_date <= now.date()
            and challenge.auto_started_at is None
            and challenge.status == "upcoming"
        )

    def _start_challenge(self, challenge: Event, start_time: datetime):
        """
        Internal method to start a challenge

        Args:
            challenge: Event object
            start_time: When the challenge is being started
        """
        challenge.status = "ongoing"
        challenge.auto_started_at = start_time

        # Initialize progress for all registered users
        registrations = (
            self.db.query(Registration).filter(Registration.event_id == challenge.id).all()
        )

        for registration in registrations:
            try:
                self.initialize_user_progress(registration.user_id, challenge.id)
            except Exception as e:
                logger.error(f"Error initializing progress for user {registration.user_id}: {e}")

    def _complete_challenge(self, challenge: Event, completion_time: datetime):
        """
        Internal method to complete a challenge

        Args:
            challenge: Event object
            completion_time: When the challenge is being completed
        """
        challenge.status = "completed"
        challenge.auto_completed_at = completion_time

        # Trigger evaluation for all participants
        # This will be handled by ChallengeEvaluationService
        logger.info(f"Challenge {challenge.id} marked for evaluation")

    def get_active_challenges(self) -> list[Event]:
        """
        Get all currently active (ongoing) challenges

        Returns:
            List of active challenges
        """
        return self.db.query(Event).filter(Event.status == "ongoing").all()

    def get_upcoming_challenges(self) -> list[Event]:
        """
        Get all upcoming challenges

        Returns:
            List of upcoming challenges
        """
        return (
            self.db.query(Event).filter(Event.status == "upcoming").order_by(Event.start_date).all()
        )
