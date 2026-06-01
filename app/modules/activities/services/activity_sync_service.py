"""
Activity Sync Service
Syncs activities from various fitness trackers and aggregates progress
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.activity_progress import ActivityProgress
from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection
from app.modules.events.domain.event import Event
# Legacy FitnessTrackerFactory removed - using new provider architecture
# from app.modules.fitness_trackers.services.legacy_trackers import FitnessTrackerFactory

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
        self, user_id: int, challenge_id: int | None = None, force: bool = False
    ) -> dict:
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
            "errors": [],
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

        # Sync from Garmin
        try:
            garmin_count = await self._sync_garmin_activities(user_id, challenges)
            if garmin_count > 0:
                results["synced_providers"].append("garmin")
                results["total_new_activities"] += garmin_count
        except Exception as e:
            logger.error(f"Error syncing Garmin for user {user_id}: {e}")
            results["errors"].append({"provider": "garmin", "error": str(e)})

        # Sync from other fitness trackers
        fitness_trackers = (
            self.db.query(FitnessTrackerConnection)
            .filter(
                and_(
                    FitnessTrackerConnection.user_id == user_id, FitnessTrackerConnection.is_active
                )
            )
            .all()
        )

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

    async def sync_challenge_activities(self, challenge_id: int) -> dict:
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

        # Get all users with progress in this challenge (using ActivityProgress)
        progress_records = (
            self.db.query(ActivityProgress).filter(ActivityProgress.event_id == challenge_id).all()
        )

        results = {
            "challenge_id": challenge_id,
            "total_users": len(progress_records),
            "synced_users": 0,
            "total_activities": 0,
            "errors": [],
        }

        for progress in progress_records:
            try:
                user_result = await self.sync_user_activities(
                    progress.user_id, challenge_id=challenge_id
                )
                results["synced_users"] += 1
                results["total_activities"] += user_result["total_new_activities"]
            except Exception as e:
                logger.error(f"Error syncing activities for user {progress.user_id}: {e}")
                results["errors"].append({"user_id": progress.user_id, "error": str(e)})

        return results

    async def _sync_strava_activities(self, user_id: int, challenges: list[Event]) -> int:
        """Sync activities from Strava"""
        strava_conn = (
            self.db.query(StravaConnection)
            .filter(and_(StravaConnection.user_id == user_id, StravaConnection.is_active))
            .first()
        )

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

    async def _sync_garmin_activities(self, user_id: int, challenges: list[Event]) -> int:
        """Sync activities from Garmin"""
        garmin_conn = (
            self.db.query(GarminConnection)
            .filter(and_(GarminConnection.user_id == user_id, GarminConnection.is_active))
            .first()
        )

        if not garmin_conn:
            return 0

        from app.modules.fitness_trackers.services.garmin_service import GarminService

        garmin_service = GarminService()
        new_activities_count = 0

        for challenge in challenges:
            if not challenge or not challenge.start_date or not challenge.end_date:
                continue

            try:
                # Fetch activities from Garmin API
                activities = garmin_service.get_activities(
                    access_token=garmin_conn.access_token,
                    access_token_secret=garmin_conn.access_token_secret,
                    start_date=datetime.combine(challenge.start_date, datetime.min.time()),
                    end_date=datetime.combine(challenge.end_date, datetime.max.time()),
                )

                # Calculate totals
                total_distance_m = sum(a.get("distance_meters", 0) for a in activities)
                total_distance_km = total_distance_m / 1000
                total_duration_sec = sum(a.get("duration_seconds", 0) for a in activities)
                total_duration_min = total_duration_sec // 60
                total_activities = len(activities)

                if total_activities > 0:
                    # Update ActivityProgress using highest-wins logic
                    activity_progress = (
                        self.db.query(ActivityProgress)
                        .filter(
                            and_(
                                ActivityProgress.user_id == user_id,
                                ActivityProgress.event_id == challenge.id,
                            )
                        )
                        .first()
                    )

                    if activity_progress:
                        from app.modules.activities.services.progress_validation_service import (
                            ProgressValidationService,
                        )

                        result = ProgressValidationService.validate_and_update_progress(
                            progress=activity_progress,
                            new_distance_km=total_distance_km,
                            source="garmin",
                            metadata={
                                "activity_count": total_activities,
                                "total_distance_meters": total_distance_m,
                                "total_duration_minutes": total_duration_min,
                            },
                        )

                        # Activity count and duration are now stored in distance_by_source metadata
                        logger.info(
                            f"Updated Garmin progress for user {user_id} in challenge {challenge.id}: {result['message']}"
                        )
                        new_activities_count += total_activities

                # Update last sync time
                garmin_conn.last_sync_at = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Error fetching activities from Garmin: {e}")
                raise

        return new_activities_count

    async def _sync_fitness_tracker_activities(
        self, tracker_conn: FitnessTrackerConnection, challenges: list[Event]
    ) -> int:
        """Sync activities from generic fitness tracker"""

        # Legacy FitnessTrackerFactory removed - using new provider architecture
        # This method is deprecated and will be removed in favor of new fitness tracker service
        logger.warning(
            f"Legacy fitness tracker sync called for provider {tracker_conn.provider}. "
            f"Use new fitness tracker service instead."
        )
        return 0

        # # Create tracker instance
        # connection_data = {
        #     "access_token": tracker_conn.access_token,
        #     "refresh_token": tracker_conn.refresh_token,
        #     "expires_at": tracker_conn.token_expires_at,
        #     "provider_data": (
        #         json.loads(tracker_conn.provider_data) if tracker_conn.provider_data else {}
        #     ),
        # }
        #
        # try:
        #     tracker = FitnessTrackerFactory.create_tracker(tracker_conn.provider, connection_data)
        # except ValueError as e:
        #     logger.error(f"Unsupported provider {tracker_conn.provider}: {e}")
        #     return 0

        new_activities_count = 0

        for challenge in challenges:
            if not challenge or not challenge.start_date or not challenge.end_date:
                continue

            # Convert dates to datetime
            start_datetime = datetime.combine(challenge.start_date, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            end_datetime = datetime.combine(challenge.end_date, datetime.max.time()).replace(
                tzinfo=timezone.utc
            )

            # Fetch activities from provider
            try:
                activities = await tracker.get_activities(start_datetime, end_datetime)

                # Calculate totals from all activities
                total_distance_m = sum(a.distance_meters for a in activities if a.distance_meters)
                total_distance_km = total_distance_m / 1000
                total_duration_sec = sum(
                    a.duration_seconds for a in activities if a.duration_seconds
                )
                total_duration_min = total_duration_sec // 60
                total_activities = len(activities)

                if total_activities > 0:
                    # Update ActivityProgress directly using highest-wins logic
                    activity_progress = (
                        self.db.query(ActivityProgress)
                        .filter(
                            and_(
                                ActivityProgress.user_id == tracker_conn.user_id,
                                ActivityProgress.event_id == challenge.id,
                            )
                        )
                        .first()
                    )

                    if activity_progress:
                        from app.modules.activities.services.progress_validation_service import (
                            ProgressValidationService,
                        )

                        result = ProgressValidationService.validate_and_update_progress(
                            progress=activity_progress,
                            new_distance_km=total_distance_km,
                            source=tracker_conn.provider,
                            metadata={
                                "activity_count": total_activities,
                                "total_distance_meters": total_distance_m,
                                "total_duration_minutes": total_duration_min,
                            },
                        )

                        # Activity count and duration are now stored in distance_by_source metadata
                        logger.info(
                            f"Updated progress for user {tracker_conn.user_id} in challenge {challenge.id}: {result['message']}"
                        )
                        new_activities_count += total_activities

            except Exception as e:
                logger.error(f"Error fetching activities from {tracker_conn.provider}: {e}")
                raise

        # Update last sync time
        tracker_conn.last_sync_at = datetime.now(timezone.utc)

        return new_activities_count

    def _update_challenge_progress(self, user_id: int, challenge_id: int):
        """
        Update aggregated progress for a user in a challenge

        NOTE: This method is now mostly handled inline during sync.
        ActivityProgress is updated directly when fetching activities.
        This method is kept for legacy compatibility and manual updates.

        Multi-tier support: If user has multiple tier registrations, logs all of them.
        """
        # Get ALL ActivityProgress records for this user and challenge (multi-tier support)
        all_progress = (
            self.db.query(ActivityProgress)
            .filter(
                and_(ActivityProgress.user_id == user_id, ActivityProgress.event_id == challenge_id)
            )
            .all()
        )

        if all_progress:
            for activity_progress in all_progress:
                logger.info(
                    f"Progress for user {user_id} in challenge {challenge_id}, "
                    f"registration {activity_progress.registration_id}: "
                    f"{activity_progress.distance_completed}km from {activity_progress.sync_source}"
                )

        # Legacy UserChallengeProgress update removed - now using activity_progress only

    def _get_user_active_challenges(self, user_id: int) -> list[Event]:
        """Get all active challenges user is registered for"""
        from app.modules.registrations.domain.registration import Registration

        registrations = self.db.query(Registration).filter(Registration.user_id == user_id).all()

        challenge_ids = [r.event_id for r in registrations]

        challenges = (
            self.db.query(Event)
            .filter(and_(Event.id.in_(challenge_ids), Event.status == "ongoing"))
            .all()
        )

        return challenges
