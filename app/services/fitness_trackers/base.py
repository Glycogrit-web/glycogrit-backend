"""
Base Fitness Tracker Interface
All fitness tracker integrations must implement this interface
"""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class FitnessActivity(BaseModel):
    """Standard activity model across all fitness trackers"""
    external_id: str
    activity_type: str  # Run, Ride, Walk, etc.
    activity_name: str | None = None
    distance_meters: int
    duration_seconds: int
    activity_date: datetime
    elevation_gain_meters: int | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    calories: int | None = None
    raw_data: dict | None = None  # Provider-specific data


class BaseFitnessTracker(ABC):
    """
    Abstract base class for fitness tracker integrations
    """

    def __init__(self, connection_data: dict):
        """
        Initialize tracker with connection data

        Args:
            connection_data: Dictionary containing access tokens and provider info
        """
        self.connection_data = connection_data
        self.provider_name = self.get_provider_name()

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'google_fit', 'apple_health')"""
        pass

    @abstractmethod
    async def authenticate(self, auth_code: str) -> dict:
        """
        Exchange authorization code for access tokens

        Args:
            auth_code: Authorization code from OAuth flow

        Returns:
            Dict with access_token, refresh_token, expires_at, etc.
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh expired access token

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new access_token and expires_at
        """
        pass

    @abstractmethod
    async def get_activities(
        self,
        start_date: datetime,
        end_date: datetime,
        activity_types: list[str] | None = None
    ) -> list[FitnessActivity]:
        """
        Fetch activities within date range

        Args:
            start_date: Start of date range
            end_date: End of date range
            activity_types: Filter by activity types (Run, Ride, etc.)

        Returns:
            List of FitnessActivity objects
        """
        pass

    @abstractmethod
    async def get_activity_details(self, activity_id: str) -> FitnessActivity:
        """
        Get detailed information about a specific activity

        Args:
            activity_id: External activity ID

        Returns:
            FitnessActivity object with detailed info
        """
        pass

    @abstractmethod
    async def revoke_access(self) -> bool:
        """
        Revoke access token and disconnect

        Returns:
            True if successful
        """
        pass

    async def validate_connection(self) -> bool:
        """
        Validate that connection is working

        Returns:
            True if connection is valid
        """
        try:
            # Try to fetch a small amount of data to verify connection
            now = datetime.now()
            await self.get_activities(now, now)
            return True
        except Exception:
            return False

    def _normalize_activity_type(self, provider_type: str) -> str:
        """
        Normalize activity type from provider-specific to standard

        Args:
            provider_type: Provider's activity type string

        Returns:
            Standardized activity type
        """
        # Common activity type mappings
        type_map = {
            'running': 'Run',
            'run': 'Run',
            'cycling': 'Ride',
            'ride': 'Ride',
            'biking': 'Ride',
            'walking': 'Walk',
            'walk': 'Walk',
            'hiking': 'Hike',
            'swimming': 'Swim',
            'yoga': 'Yoga',
            'workout': 'Workout'
        }

        normalized = provider_type.lower().strip()
        return type_map.get(normalized, provider_type.title())
