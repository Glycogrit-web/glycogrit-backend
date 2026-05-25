"""
Google Fit Integration
Integrates with Google Fit API for activity tracking
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseFitnessTracker, FitnessActivity

logger = logging.getLogger(__name__)


class GoogleFitTracker(BaseFitnessTracker):
    """
    Google Fit API integration
    Requires: Google OAuth 2.0, Fitness API enabled
    """

    GOOGLE_FIT_API_BASE = "https://www.googleapis.com/fitness/v1/users/me"
    GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    def get_provider_name(self) -> str:
        return "google_fit"

    async def authenticate(self, auth_code: str) -> dict:
        """
        Exchange authorization code for access tokens

        Scopes needed:
        - https://www.googleapis.com/auth/fitness.activity.read
        - https://www.googleapis.com/auth/fitness.location.read
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "code": auth_code,
                    "client_id": self.connection_data.get("client_id"),
                    "client_secret": self.connection_data.get("client_secret"),
                    "redirect_uri": self.connection_data.get("redirect_uri"),
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            token_data = response.json()

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600),
                "scope": token_data.get("scope")
            }

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh expired access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self.connection_data.get("client_id"),
                    "client_secret": self.connection_data.get("client_secret"),
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()

            return {
                "access_token": token_data["access_token"],
                "expires_at": datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600)
            }

    async def get_activities(
        self,
        start_date: datetime,
        end_date: datetime,
        activity_types: list[str] | None = None
    ) -> list[FitnessActivity]:
        """
        Fetch activities from Google Fit

        Google Fit stores activities in "sessions" (structured workouts)
        """
        access_token = self.connection_data.get("access_token")

        # Convert datetime to nanoseconds (Google Fit format)
        int(start_date.timestamp() * 1e9)
        int(end_date.timestamp() * 1e9)

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get sessions (workouts)
            response = await client.get(
                f"{self.GOOGLE_FIT_API_BASE}/sessions",
                headers=headers,
                params={
                    "startTime": start_date.isoformat(),
                    "endTime": end_date.isoformat()
                }
            )
            response.raise_for_status()
            sessions_data = response.json()

            activities = []
            for session in sessions_data.get("session", []):
                try:
                    # Parse session and fetch distance data
                    activity = await self._parse_google_fit_session_with_distance(session, headers, client)

                    # Filter by activity type if specified
                    if activity_types and activity.activity_type not in activity_types:
                        continue

                    activities.append(activity)
                except Exception as e:
                    logger.error(f"Error parsing Google Fit session: {e}")
                    continue

            return activities

    async def get_activity_details(self, activity_id: str) -> FitnessActivity:
        """Get detailed information about a specific activity"""
        access_token = self.connection_data.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GOOGLE_FIT_API_BASE}/sessions/{activity_id}",
                headers=headers
            )
            response.raise_for_status()
            session_data = response.json()

            return self._parse_google_fit_session(session_data)

    async def revoke_access(self) -> bool:
        """Revoke Google Fit access token"""
        access_token = self.connection_data.get("access_token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://oauth2.googleapis.com/revoke?token={access_token}"
            )
            return response.status_code == 200

    async def _parse_google_fit_session_with_distance(
        self,
        session: dict,
        headers: dict,
        client: httpx.AsyncClient
    ) -> FitnessActivity:
        """Parse Google Fit session into FitnessActivity with distance from datasets API"""

        # Extract session details
        session_id = session.get("id", "")
        activity_type_code = session.get("activityType", 0)
        activity_name = session.get("name", "")

        # Convert timestamps (milliseconds to datetime)
        start_time_ms = int(session.get("startTimeMillis", 0))
        end_time_ms = int(session.get("endTimeMillis", 0))
        activity_date = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)

        # Calculate duration
        duration_seconds = (end_time_ms - start_time_ms) // 1000

        # Fetch distance from datasets API
        distance_meters = 0
        try:
            # Google Fit datasets API requires nanosecond timestamps
            start_time_ms * 1_000_000
            end_time_ms * 1_000_000

            # Query distance dataset
            dataset_response = await client.get(
                f"{self.GOOGLE_FIT_API_BASE}/dataset:aggregate",
                headers=headers,
                json={
                    "aggregateBy": [{
                        "dataTypeName": "com.google.distance.delta",
                        "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta"
                    }],
                    "bucketByTime": {"durationMillis": end_time_ms - start_time_ms},
                    "startTimeMillis": start_time_ms,
                    "endTimeMillis": end_time_ms
                }
            )

            if dataset_response.status_code == 200:
                dataset_data = dataset_response.json()
                for bucket in dataset_data.get("bucket", []):
                    for dataset in bucket.get("dataset", []):
                        for point in dataset.get("point", []):
                            for value in point.get("value", []):
                                if "fpVal" in value:
                                    distance_meters += value["fpVal"]
        except Exception as e:
            logger.warning(f"Failed to fetch distance for session {session_id}: {e}")

        # Map activity type code to readable name
        activity_type = self._map_google_fit_activity_type(activity_type_code)

        return FitnessActivity(
            external_id=session_id,
            activity_type=self._normalize_activity_type(activity_type),
            activity_name=activity_name or activity_type,
            distance_meters=int(distance_meters),
            duration_seconds=duration_seconds,
            activity_date=activity_date,
            elevation_gain_meters=None,  # Not directly available in session
            average_speed=None,
            max_speed=None,
            calories=None,  # Would need separate query
            raw_data=session
        )

    def _parse_google_fit_session(self, session: dict) -> FitnessActivity:
        """Parse Google Fit session into FitnessActivity (legacy method without distance fetch)"""

        # Extract session details
        session_id = session.get("id", "")
        activity_type_code = session.get("activityType", 0)
        activity_name = session.get("name", "")

        # Convert timestamps (milliseconds to datetime)
        start_time_ms = int(session.get("startTimeMillis", 0))
        end_time_ms = int(session.get("endTimeMillis", 0))
        activity_date = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)

        # Calculate duration
        duration_seconds = (end_time_ms - start_time_ms) // 1000

        # Extract distance (meters) from session aggregates if available
        distance_meters = 0
        for aggregate in session.get("aggregates", []):
            if "com.google.distance.delta" in aggregate.get("dataTypeName", ""):
                distance_meters = int(aggregate.get("value", [{}])[0].get("fpVal", 0))

        # Map activity type code to readable name
        activity_type = self._map_google_fit_activity_type(activity_type_code)

        return FitnessActivity(
            external_id=session_id,
            activity_type=self._normalize_activity_type(activity_type),
            activity_name=activity_name or activity_type,
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            activity_date=activity_date,
            elevation_gain_meters=None,  # Not directly available in session
            average_speed=None,
            max_speed=None,
            calories=None,  # Would need separate query
            raw_data=session
        )

    def _map_google_fit_activity_type(self, activity_code: int) -> str:
        """Map Google Fit activity type codes to readable names"""
        # Common Google Fit activity types
        # https://developers.google.com/fit/rest/v1/reference/activity-types
        activity_map = {
            1: "Biking",
            8: "Running",
            7: "Walking",
            79: "Hiking",
            82: "Swimming",
            9: "Aerobics",
            # Add more as needed
        }
        return activity_map.get(activity_code, "Workout")
