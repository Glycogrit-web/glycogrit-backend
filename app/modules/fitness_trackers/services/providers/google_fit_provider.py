"""
Google Fit OAuth Provider Implementation
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider


class GoogleFitProvider(OAuthProvider):
    """Google Fit OAuth 2.0 implementation"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GOOGLE_FIT

    @property
    def provider_name(self) -> str:
        return "Google Fit"

    @property
    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"

    @property
    def api_base_url(self) -> str:
        return "https://www.googleapis.com/fitness/v1/users/me"

    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """Get Google Fit authorization parameters"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/userinfo.profile "
            "https://www.googleapis.com/auth/fitness.activity.read "
            "https://www.googleapis.com/auth/fitness.location.read",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        return params

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens"""
        response = await self._make_http_request(
            "POST",
            self.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
        )

        data = response.json()

        # Get user info
        user_response = await self._make_http_request(
            "GET",
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        user_data = user_response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"]),
            "athlete_id": user_data["id"],
            "athlete_data": user_data,
            "scope": data.get("scope", "fitness.activity.read"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh Google Fit access token"""
        response = await self._make_http_request(
            "POST",
            self.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": refresh_token,  # Google doesn't return new refresh token
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"]),
        }

    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """Get Google user profile"""
        response = await self._make_http_request(
            "GET",
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        return response.json()

    async def get_activities(
        self, access_token: str, sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """Get Google Fit activities (sessions) within sync window"""
        # Convert to nanoseconds (Google Fit uses nanoseconds)
        start_time_ns = int(sync_window.start_date.timestamp() * 1e9)
        end_time_ns = int(sync_window.end_date.timestamp() * 1e9)

        response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/sessions",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "startTime": start_time_ns,
                "endTime": end_time_ns,
            },
        )

        data = response.json()
        sessions = data.get("session", [])

        # Get detailed data for each session
        activities = []
        for session in sessions:
            # Get distance data for this session
            session_start = session["startTimeMillis"]
            session_end = session["endTimeMillis"]

            # Query distance data
            distance_response = await self._make_http_request(
                "POST",
                f"{self.api_base_url}/dataset:aggregate",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "aggregateBy": [
                        {
                            "dataTypeName": "com.google.distance.delta",
                            "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta",
                        }
                    ],
                    "bucketByTime": {"durationMillis": int(session_end) - int(session_start)},
                    "startTimeMillis": int(session_start),
                    "endTimeMillis": int(session_end),
                },
            )

            distance_data = distance_response.json()

            # Combine session with distance data
            session["distanceData"] = distance_data
            activities.append(session)

        return activities

    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """Parse distance from Google Fit session (convert meters to km)"""
        distance_data = activity.get("distanceData", {})
        buckets = distance_data.get("bucket", [])

        total_distance = 0.0
        for bucket in buckets:
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    for value in point.get("value", []):
                        if "fpVal" in value:
                            total_distance += value["fpVal"]

        return total_distance / 1000.0  # meters to km

    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """Parse duration from Google Fit session (convert ms to minutes)"""
        start_ms = int(activity.get("startTimeMillis", 0))
        end_ms = int(activity.get("endTimeMillis", 0))

        if start_ms and end_ms:
            duration_ms = end_ms - start_ms
            return int(duration_ms / 60000)

        return None

    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """Parse activity date from Google Fit session"""
        start_ms = int(activity.get("startTimeMillis", 0))
        return datetime.fromtimestamp(start_ms / 1000.0)
