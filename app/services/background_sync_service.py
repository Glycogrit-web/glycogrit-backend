"""
Background Sync Service
Automatically syncs activities from connected fitness trackers (Strava, Google Fit, etc.)
Runs periodically to keep user progress up-to-date
"""

import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.core.database import get_db
from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection
from app.models.registration import Registration
from app.models.event import Event
from app.services.activity_sync_service import ActivitySyncService
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BackgroundSyncService:
    """
    Service for automatic background syncing of fitness tracker data
    """

    # Sync interval (in minutes)
    SYNC_INTERVAL_MINUTES = 30  # Sync every 30 minutes
    MIN_SYNC_INTERVAL_MINUTES = 15  # Don't sync if synced within last 15 minutes

    def __init__(self, db: Session):
        self.db = db

    async def sync_all_active_users(self) -> Dict:
        """
        Sync all users who have active tracker connections and ongoing events

        Returns:
            Dict with sync statistics
        """
        results = {
            "total_users_checked": 0,
            "total_users_synced": 0,
            "total_sync_errors": 0,
            "sync_time": datetime.now(timezone.utc).isoformat(),
            "details": []
        }

        try:
            # Get all active events (ongoing or upcoming within 7 days)
            now = datetime.now(timezone.utc)
            upcoming_date = now + timedelta(days=7)

            active_events = self.db.query(Event).filter(
                and_(
                    Event.status.in_(['ongoing', 'upcoming']),
                    Event.event_end_date >= now.date() if hasattr(Event, 'event_end_date') else True
                )
            ).all()

            if not active_events:
                logger.info("No active events found for sync")
                return results

            # Get all registrations for these events
            event_ids = [event.id for event in active_events]
            registrations = self.db.query(Registration).filter(
                Registration.event_id.in_(event_ids)
            ).all()

            # Get unique user IDs from registrations
            user_ids = list(set([reg.user_id for reg in registrations]))
            results["total_users_checked"] = len(user_ids)

            logger.info(f"Found {len(user_ids)} users with active event registrations")

            # Sync each user
            for user_id in user_ids:
                try:
                    user_result = await self.sync_user_if_needed(user_id)
                    if user_result["synced"]:
                        results["total_users_synced"] += 1
                        results["details"].append(user_result)
                except Exception as e:
                    logger.error(f"Error syncing user {user_id}: {e}")
                    results["total_sync_errors"] += 1
                    results["details"].append({
                        "user_id": user_id,
                        "synced": False,
                        "error": str(e)
                    })

            logger.info(
                f"Background sync completed: {results['total_users_synced']}/{results['total_users_checked']} users synced"
            )

        except Exception as e:
            logger.error(f"Error in sync_all_active_users: {e}")
            results["error"] = str(e)

        return results

    async def sync_user_if_needed(self, user_id: int) -> Dict:
        """
        Sync a specific user if they have active connections and need syncing
        Only syncs from the user's primary sync source (if set)

        Args:
            user_id: User ID to sync

        Returns:
            Dict with sync result
        """
        from app.models.user import User

        result = {
            "user_id": user_id,
            "synced": False,
            "reason": None,
            "providers_synced": [],
            "activities_added": 0
        }

        try:
            # Get user to check primary_sync_source
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                result["reason"] = "User not found"
                return result

            primary_source = user.primary_sync_source

            # If no primary source set, skip automatic sync
            if not primary_source:
                result["reason"] = "No primary sync source set"
                return result

            # Check only the primary source connection
            needs_sync = False
            connection = None

            if primary_source == 'strava':
                connection = self.db.query(StravaConnection).filter(
                    and_(
                        StravaConnection.user_id == user_id,
                        StravaConnection.is_active == True
                    )
                ).first()

                if connection:
                    if not connection.last_sync_at:
                        needs_sync = True
                    else:
                        time_since_last_sync = datetime.now(timezone.utc) - connection.last_sync_at
                        if time_since_last_sync.total_seconds() / 60 >= self.MIN_SYNC_INTERVAL_MINUTES:
                            needs_sync = True
            else:
                # Google Fit or other providers
                connection = self.db.query(FitnessTrackerConnection).filter(
                    and_(
                        FitnessTrackerConnection.user_id == user_id,
                        FitnessTrackerConnection.provider == primary_source,
                        FitnessTrackerConnection.is_active == True
                    )
                ).first()

                if connection:
                    if not connection.last_sync_at:
                        needs_sync = True
                    else:
                        time_since_last_sync = datetime.now(timezone.utc) - connection.last_sync_at
                        if time_since_last_sync.total_seconds() / 60 >= self.MIN_SYNC_INTERVAL_MINUTES:
                            needs_sync = True

            # If no connection or doesn't need syncing, skip
            if not connection:
                result["reason"] = f"No active connection for primary source: {primary_source}"
                return result

            if not needs_sync:
                result["reason"] = f"Primary source {primary_source} synced recently"
                return result

            # Perform sync only for primary source
            sync_service = ActivitySyncService(self.db)
            sync_result = await sync_service.sync_user_activities(
                user_id=user_id,
                challenge_id=None,  # Sync all active challenges
                force=False
            )

            result["synced"] = True
            result["providers_synced"] = sync_result.get("synced_providers", [])
            result["activities_added"] = sync_result.get("total_new_activities", 0)

            logger.info(
                f"Successfully synced user {user_id} from primary source {primary_source}: "
                f"{result['activities_added']} new activities"
            )

        except Exception as e:
            logger.error(f"Error syncing user {user_id}: {e}")
            result["error"] = str(e)

        return result

    async def sync_specific_providers(self, provider_names: List[str]) -> Dict:
        """
        Sync only specific providers (e.g., just Google Fit)

        Args:
            provider_names: List of provider names to sync ('strava', 'google_fit', etc.)

        Returns:
            Dict with sync statistics
        """
        results = {
            "providers": provider_names,
            "total_users_synced": 0,
            "total_sync_errors": 0,
            "details": []
        }

        try:
            user_ids = set()

            for provider in provider_names:
                if provider == 'strava':
                    # Get all active Strava connections
                    connections = self.db.query(StravaConnection).filter(
                        StravaConnection.is_active == True
                    ).all()
                    user_ids.update([conn.user_id for conn in connections])
                else:
                    # Get all active fitness tracker connections for this provider
                    connections = self.db.query(FitnessTrackerConnection).filter(
                        and_(
                            FitnessTrackerConnection.provider == provider,
                            FitnessTrackerConnection.is_active == True
                        )
                    ).all()
                    user_ids.update([conn.user_id for conn in connections])

            logger.info(f"Found {len(user_ids)} users to sync for providers: {provider_names}")

            # Sync each user
            for user_id in user_ids:
                try:
                    user_result = await self.sync_user_if_needed(user_id)
                    if user_result["synced"]:
                        results["total_users_synced"] += 1
                    results["details"].append(user_result)
                except Exception as e:
                    logger.error(f"Error syncing user {user_id}: {e}")
                    results["total_sync_errors"] += 1

        except Exception as e:
            logger.error(f"Error in sync_specific_providers: {e}")
            results["error"] = str(e)

        return results


async def run_periodic_sync():
    """
    Run periodic sync loop
    This should be called from a background task/scheduler
    """
    logger.info("Starting periodic sync loop")

    while True:
        try:
            # Get database session
            db = next(get_db())

            # Create sync service and run sync
            sync_service = BackgroundSyncService(db)
            results = await sync_service.sync_all_active_users()

            logger.info(f"Periodic sync completed: {results}")

        except Exception as e:
            logger.error(f"Error in periodic sync loop: {e}")

        finally:
            # Close database session
            if db:
                db.close()

        # Wait for next sync interval
        await asyncio.sleep(BackgroundSyncService.SYNC_INTERVAL_MINUTES * 60)


# Manual trigger endpoints can call this
async def trigger_manual_sync(db: Session, user_id: Optional[int] = None, provider: Optional[str] = None) -> Dict:
    """
    Manually trigger a sync

    Args:
        db: Database session
        user_id: Optional specific user to sync
        provider: Optional specific provider to sync

    Returns:
        Dict with sync results
    """
    sync_service = BackgroundSyncService(db)

    if user_id:
        # Sync specific user
        result = await sync_service.sync_user_if_needed(user_id)
        return {"user_sync": result}
    elif provider:
        # Sync specific provider
        return await sync_service.sync_specific_providers([provider])
    else:
        # Sync all
        return await sync_service.sync_all_active_users()
