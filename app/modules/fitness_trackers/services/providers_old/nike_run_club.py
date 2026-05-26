"""
Nike Run Club Integration
Note: Nike doesn't provide an official public API
This is a conceptual implementation for POC purposes
"""

import logging
from datetime import datetime

from .base import BaseFitnessTracker, FitnessActivity

logger = logging.getLogger(__name__)


class NikeRunClubTracker(BaseFitnessTracker):
    """
    Nike Run Club integration (Conceptual)

    WARNING: Nike does not provide an official public API for Nike Run Club.

    Possible approaches:
    1. Manual upload: Users export their runs from Nike Run Club app and upload
    2. Partner API: Apply for Nike partner program access (enterprise only)
    3. Web scraping: Not recommended, violates ToS

    This implementation assumes manual data upload flow.
    """

    def get_provider_name(self) -> str:
        return "nike_run_club"

    async def authenticate(self, auth_code: str) -> dict:
        """
        Nike Run Club authentication (manual flow)

        Since there's no official API, we use manual data upload:
        1. User connects account by verifying their Nike username
        2. User manually uploads exported runs
        """
        return {
            "access_token": f"manual_{auth_code}",  # User identifier
            "refresh_token": None,
            "expires_at": None,
            "scope": "manual_upload",
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        """No token refresh needed for manual upload"""
        return {"access_token": refresh_token, "expires_at": None}

    async def get_activities(
        self, start_date: datetime, end_date: datetime, activity_types: list[str] | None = None
    ) -> list[FitnessActivity]:
        """
        Get Nike Run Club activities

        In practice, queries manually uploaded activities from database
        """
        logger.info(f"Fetching Nike Run Club activities from {start_date} to {end_date}")

        # Query database for manually uploaded Nike runs
        return []

    async def get_activity_details(self, activity_id: str) -> FitnessActivity:
        """Get detailed information about a specific run"""
        raise NotImplementedError("Query database for activity_id")

    async def revoke_access(self) -> bool:
        """Disconnect Nike Run Club"""
        logger.info("Nike Run Club connection disconnected")
        return True

    def parse_nike_run_export(self, run_data: dict) -> FitnessActivity:
        """
        Parse manually uploaded Nike Run Club data

        Expected format (from Nike Run Club export/manual entry):
        {
            "run_id": "nike_abc123",
            "type": "run",
            "start_time": "2026-04-24T10:00:00Z",
            "distance_km": 5.2,
            "duration_minutes": 28,
            "pace_min_per_km": 5.4,
            "calories": 320,
            "elevation_gain": 45
        }
        """

        run_id = run_data.get("run_id", "")
        start_time = datetime.fromisoformat(run_data["start_time"].replace("Z", "+00:00"))

        # Convert to standard units
        distance_meters = int(run_data.get("distance_km", 0) * 1000)
        duration_seconds = int(run_data.get("duration_minutes", 0) * 60)

        # Calculate average speed (m/s)
        avg_speed = None
        if duration_seconds > 0:
            avg_speed = distance_meters / duration_seconds

        return FitnessActivity(
            external_id=run_id,
            activity_type="Run",
            activity_name=f"Nike Run - {run_data.get('distance_km')}km",
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            activity_date=start_time,
            elevation_gain_meters=run_data.get("elevation_gain"),
            average_speed=avg_speed,
            max_speed=None,
            calories=run_data.get("calories"),
            raw_data=run_data,
        )

    def generate_upload_instructions(self) -> dict:
        """
        Generate instructions for users to manually upload Nike runs

        Returns guide for exporting data from Nike Run Club
        """
        return {
            "provider": "nike_run_club",
            "connection_type": "manual_upload",
            "instructions": [
                "Open Nike Run Club app on your phone",
                "Go to Profile > Settings > Privacy Center",
                "Request 'Download Your Data'",
                "Nike will email you a data export (may take 30 days)",
                "Upload the exported JSON file to GlycoGrit",
                "We'll automatically import your runs",
            ],
            "alternative": "Manually log each run with distance, time, and date",
            "supported_data": [
                "Run distance (km)",
                "Duration (minutes)",
                "Date and time",
                "Pace",
                "Elevation gain",
                "Calories burned",
            ],
        }
