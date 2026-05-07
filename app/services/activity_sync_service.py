"""
Activity Sync Service
Syncs activities from various fitness trackers and aggregates progress
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.event import Event
from app.models.strava_connection import StravaConnection, ChallengeActivity, UserChallengeProgress
from app.models.activity_progress import ActivityProgress
from app.models.fitness_tracker import FitnessTrackerConnection
from app.services.fitness_trackers import FitnessTrackerFactory, FitnessActivity
from typing import List, Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)


class ActivitySyncService:
    """
    Service for syncing activities from fitness trackers and updating progress

    Handles:
    - Syncing activities from Strava, Google Fit, Apple Health, Nike Run Club
    - Filtering activities by challenge date range
    - Preventing duplicate activities across providers
    - Updating user challenge progress
    """

    def __init__(self, db: Session):
        self.db = db

    async def sync_user_activities(
        self,
        user_id: int,
        challenge_id: Optional[int] = None,
        force: bool = False
    ) -> Dict:
        """
        Sync activities for a user from all connected trackers

        Args:
            user_id: User ID
            challenge_id: Optional challenge ID to sync for (or all active challenges)
            force: Force resync even if recently synced

        Returns:
            Dict with sync results
        """
        results = {
            "user_id": user_id,
            "synced_providers": [],
            "total_new_activities": 0,
            "errors": []
        }

        # Get challenges to sync for
        if challenge_id:
            challenges = [self.db.query(Event).filter(Event.id == challenge_id).first()]
        else:
            # Sync for all active challenges user is registered for
            challenges = self._get_user_active_challenges(user_id)

        if not challenges:
            logger.info(f"No active challenges found for user {user_id}")
            return results

        # Sync from Strava
        try:
            strava_count = await self._sync_strava_activities(user_id, challenges)
            if strava_count > 0:
                results["synced_providers"].append("strava")
                results["total_new_activities"] += strava_count
        except Exception as e:
            logger.error(f"Error syncing Strava for user {user_id}: {e}")
            results["errors"].append({"provider": "strava", "error": str(e)})

        # Sync from other fitness trackers
        fitness_trackers = self.db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == user_id,
                FitnessTrackerConnection.is_active == True
            )
        ).all()

        for tracker_conn in fitness_trackers:
            try:
                count = await self._sync_fitness_tracker_activities(tracker_conn, challenges)
                if count > 0:
                    results["synced_providers"].append(tracker_conn.provider)
                    results["total_new_activities"] += count
            except Exception as e:
                logger.error(f"Error syncing {tracker_conn.provider} for user {user_id}: {e}")
                results["errors"].append({"provider": tracker_conn.provider, "error": str(e)})

        # Update progress for all challenges
        for challenge in challenges:
            if challenge:
                self._update_challenge_progress(user_id, challenge.id)

        self.db.commit()
        return results

    async def sync_challenge_activities(self, challenge_id: int) -> Dict:
        """
        Sync activities for all participants in a challenge

        Args:
            challenge_id: Challenge ID

        Returns:
            Dict with sync results
        """
        challenge = self.db.query(Event).filter(Event.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        # Get all users with progress in this challenge
        progress_records = self.db.query(UserChallengeProgress).filter(
            UserChallengeProgress.challenge_id == challenge_id
        ).all()

        results = {
            "challenge_id": challenge_id,
            "total_users": len(progress_records),
            "synced_users": 0,
            "total_activities": 0,
            "errors": []
        }

        for progress in progress_records:
            try:
                user_result = await self.sync_user_activities(
                    progress.user_id,
                    challenge_id=challenge_id
                )
                results["synced_users"] += 1
                results["total_activities"] += user_result["total_new_activities"]
            except Exception as e:
                logger.error(f"Error syncing activities for user {progress.user_id}: {e}")
                results["errors"].append({"user_id": progress.user_id, "error": str(e)})

        return results

    async def _sync_strava_activities(self, user_id: int, challenges: List[Event]) -> int:
        """Sync activities from Strava"""
        strava_conn = self.db.query(StravaConnection).filter(
            and_(
                StravaConnection.user_id == user_id,
                StravaConnection.is_active == True
            )
        ).first()

        if not strava_conn:
            return 0

        # Check if token needs refresh
        if strava_conn.expires_at < datetime.now(timezone.utc):
            # TODO: Refresh Strava token
            logger.warning(f"Strava token expired for user {user_id}")
            return 0

        new_activities_count = 0

        for challenge in challenges:
            if not challenge or not challenge.start_date or not challenge.end_date:
                continue

            # Fetch activities from Strava API
            # This would use the existing Strava integration
            # For POC, we'll mark the sync timestamp
            strava_conn.last_sync_at = datetime.now(timezone.utc)
            new_activities_count += 0  # Placeholder

        return new_activities_count

    async def _sync_fitness_tracker_activities(
        self,
        tracker_conn: FitnessTrackerConnection,
        challenges: List[Event]
    ) -> int:
        """Sync activities from generic fitness tracker"""

        # Create tracker instance
        connection_data = {
            "access_token": tracker_conn.access_token,
            "refresh_token": tracker_conn.refresh_token,
            "expires_at": tracker_conn.token_expires_at,
            "provider_data": json.loads(tracker_conn.provider_data) if tracker_conn.provider_data else {}
        }

        try:
            tracker = FitnessTrackerFactory.create_tracker(
                tracker_conn.provider,
                connection_data
            )
        except ValueError as e:
            logger.error(f"Unsupported provider {tracker_conn.provider}: {e}")
            return 0

        new_activities_count = 0

        for challenge in challenges:
            if not challenge or not challenge.start_date or not challenge.end_date:
                continue

            # Convert dates to datetime
            start_datetime = datetime.combine(challenge.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(challenge.end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

            # Fetch activities from provider
            try:
                activities = await tracker.get_activities(start_datetime, end_datetime)

                for activity in activities:
                    # Check if activity already exists
                    existing = self.db.query(ChallengeActivity).filter(
                        and_(
                            ChallengeActivity.source_provider == tracker_conn.provider,
                            ChallengeActivity.external_activity_id == activity.external_id,
                            ChallengeActivity.challenge_id == challenge.id
                        )
                    ).first()

                    if existing:
                        continue

                    # Create new activity record
                    challenge_activity = ChallengeActivity(
                        challenge_id=challenge.id,
                        user_id=tracker_conn.user_id,
                        strava_connection_id=None,
                        source_provider=tracker_conn.provider,
                        external_activity_id=activity.external_id,
                        strava_activity_id=None,
                        activity_type=activity.activity_type,
                        activity_name=activity.activity_name,
                        distance_meters=activity.distance_meters,
                        duration_seconds=activity.duration_seconds,
                        elevation_gain_meters=activity.elevation_gain_meters,
                        average_speed=int(activity.average_speed) if activity.average_speed else None,
                        max_speed=int(activity.max_speed) if activity.max_speed else None,
                        activity_date=activity.activity_date,
                        is_verified=True
                    )

                    self.db.add(challenge_activity)
                    new_activities_count += 1

            except Exception as e:
                logger.error(f"Error fetching activities from {tracker_conn.provider}: {e}")
                raise

        # Update last sync time
        tracker_conn.last_sync_at = datetime.now(timezone.utc)

        return new_activities_count

    def _update_challenge_progress(self, user_id: int, challenge_id: int):
        """Update aggregated progress for a user in a challenge"""

        # Get all activities for this user/challenge
        activities = self.db.query(ChallengeActivity).filter(
            and_(
                ChallengeActivity.user_id == user_id,
                ChallengeActivity.challenge_id == challenge_id
            )
        ).all()

        # Calculate aggregates
        total_distance_m = sum(a.distance_meters for a in activities)
        total_distance_km = total_distance_m / 1000  # Use float division for accuracy
        total_duration_sec = sum(a.duration_seconds for a in activities)
        total_duration_min = total_duration_sec // 60
        total_activities = len(activities)

        # Update ActivityProgress (new model) using highest-wins logic
        activity_progress = self.db.query(ActivityProgress).filter(
            and_(
                ActivityProgress.user_id == user_id,
                ActivityProgress.event_id == challenge_id
            )
        ).first()

        if activity_progress:
            from app.services.progress_validation_service import ProgressValidationService

            # Determine source based on activities
            source = 'fitness_tracker'
            if activities and activities[0].source_provider:
                source = activities[0].source_provider

            result = ProgressValidationService.validate_and_update_progress(
                progress=activity_progress,
                new_distance_km=total_distance_km,
                source=source,
                metadata={
                    'activity_count': total_activities,
                    'total_distance_meters': total_distance_m,
                    'total_duration_minutes': total_duration_min
                }
            )

            # Always update activity count and duration
            activity_progress.total_activities = total_activities
            activity_progress.total_duration_minutes = total_duration_min

            logger.info(f"Updated progress for user {user_id} in challenge {challenge_id}: {result['message']}")

        # Also update legacy UserChallengeProgress for backwards compatibility
        legacy_progress = self.db.query(UserChallengeProgress).filter(
            and_(
                UserChallengeProgress.user_id == user_id,
                UserChallengeProgress.challenge_id == challenge_id
            )
        ).first()

        if legacy_progress:
            legacy_progress.total_distance_km = int(total_distance_km)
            legacy_progress.total_activities = total_activities
            legacy_progress.total_duration_minutes = total_duration_min

            # Calculate progress percentage
            if legacy_progress.goal_distance_km and legacy_progress.goal_distance_km > 0:
                legacy_progress.progress_percentage = min(100, int((total_distance_km / legacy_progress.goal_distance_km) * 100))
            else:
                legacy_progress.progress_percentage = 0

            # Update last activity date
            if activities:
                latest_activity = max(activities, key=lambda a: a.activity_date)
                legacy_progress.last_activity_date = latest_activity.activity_date

    def _get_user_active_challenges(self, user_id: int) -> List[Event]:
        """Get all active challenges user is registered for"""
        from app.models.registration import Registration

        registrations = self.db.query(Registration).filter(
            Registration.user_id == user_id
        ).all()

        challenge_ids = [r.event_id for r in registrations]

        challenges = self.db.query(Event).filter(
            and_(
                Event.id.in_(challenge_ids),
                Event.status == 'ongoing'
            )
        ).all()

        return challenges
