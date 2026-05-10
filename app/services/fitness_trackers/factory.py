"""
Fitness Tracker Factory
Creates appropriate tracker instance based on provider
"""

from typing import Dict
from .base import BaseFitnessTracker
from .google_fit import GoogleFitTracker
from .apple_health import AppleHealthTracker
from .nike_run_club import NikeRunClubTracker


class FitnessTrackerFactory:
    """Factory for creating fitness tracker instances"""

    @staticmethod
    def create_tracker(provider: str, connection_data: Dict) -> BaseFitnessTracker:
        """
        Create a fitness tracker instance

        Args:
            provider: Provider name (google_fit, apple_health, nike_run_club, strava)
            connection_data: Connection credentials and config

        Returns:
            Appropriate BaseFitnessTracker instance

        Raises:
            ValueError: If provider is not supported
        """
        tracker_map = {
            "google_fit": GoogleFitTracker,
            "apple_health": AppleHealthTracker,
            "nike_run_club": NikeRunClubTracker,
            # Strava is handled separately via existing StravaConnection model
        }

        tracker_class = tracker_map.get(provider.lower())
        if not tracker_class:
            raise ValueError(f"Unsupported fitness tracker provider: {provider}")

        return tracker_class(connection_data)

    @staticmethod
    def get_supported_providers() -> list:
        """Get list of supported fitness tracker providers"""
        return [
            {
                "name": "strava",
                "display_name": "Strava",
                "auth_type": "oauth2",
                "description": "Connect your Strava account to sync runs and rides",
                "features": ["auto_sync", "realtime", "activities"]
            },
            {
                "name": "fitbit",
                "display_name": "Fitbit",
                "auth_type": "oauth2",
                "description": "Connect your Fitbit to sync activities and track progress",
                "features": ["auto_sync", "activities", "steps", "heart_rate"]
            },
            {
                "name": "wahoo",
                "display_name": "Wahoo Fitness",
                "auth_type": "oauth2",
                "description": "Connect your Wahoo to sync workouts from cycling and running",
                "features": ["auto_sync", "activities", "cycling", "running"]
            },
            {
                "name": "google_fit",
                "display_name": "Google Fit",
                "auth_type": "oauth2",
                "description": "Sync workouts from Google Fit",
                "features": ["auto_sync", "activities", "heart_rate"]
            },
            {
                "name": "apple_health",
                "display_name": "Apple Health",
                "auth_type": "native_app",
                "description": "Sync workouts from Apple Health (requires iOS app)",
                "features": ["activities", "heart_rate", "ios_only"]
            },
            {
                "name": "nike_run_club",
                "display_name": "Nike Run Club",
                "auth_type": "manual",
                "description": "Manually upload runs from Nike Run Club",
                "features": ["manual_upload", "runs_only"]
            }
        ]
