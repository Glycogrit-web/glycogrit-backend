"""
Fitbit OAuth Provider Implementation
"""

from datetime import datetime
from typing import Any

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider


class FitbitProvider(OAuthProvider):
    """Fitbit OAuth 2.0 implementation"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.FITBIT

    @property
    def provider_name(self) -> str:
        return "Fitbit"

    @property
    def authorization_url(self) -> str:
        return "https://www.fitbit.com/oauth2/authorize"

    @property
    def token_url(self) -> str:
        return "https://api.fitbit.com/oauth2/token"

    @property
    def api_base_url(self) -> str:
        return "https://api.fitbit.com/1"

    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """Get Fitbit authorization parameters"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "activity heartrate location nutrition profile settings sleep social weight",
            "expires_in": "31536000",  # 1 year
        }
        if state:
            params["state"] = state
        return params

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens"""
        import base64

        # Fitbit requires Basic Auth with client credentials
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        response = await self._make_http_request(
            "POST",
            self.token_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
        )

        data = response.json()

        # Get user profile
        user_response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/user/-/profile.json",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        user_data = user_response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": datetime.utcnow()
            .replace(microsecond=0)
            .replace(hour=0, minute=0, second=0),  # Tokens expire at midnight
            "athlete_id": user_data["user"]["encodedId"],
            "athlete_data": user_data["user"],
            "scope": data.get("scope", "activity"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh Fitbit access token"""
        import base64

        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        response = await self._make_http_request(
            "POST",
            self.token_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": datetime.utcnow()
            .replace(microsecond=0)
            .replace(hour=0, minute=0, second=0),
        }

    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """Get Fitbit user profile"""
        response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/user/-/profile.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        return response.json()["user"]

    async def get_activities(
        self, access_token: str, sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """Get Fitbit activities within sync window"""
        activities = []

        # Fitbit requires date-by-date queries
        current_date = sync_window.start_date.date()
        end_date = sync_window.end_date.date()

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            response = await self._make_http_request(
                "GET",
                f"{self.api_base_url}/user/-/activities/date/{date_str}.json",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()
            if "activities" in data:
                activities.extend(data["activities"])

            current_date = current_date.replace(day=current_date.day + 1)

            # Safety limit
            if len(activities) > 1000:
                break

        return activities

    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """Parse distance from Fitbit activity (already in km)"""
        return activity.get("distance", 0.0)

    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """Parse duration from Fitbit activity (convert ms to minutes)"""
        duration_ms = activity.get("duration")
        if duration_ms:
            return int(duration_ms / 60000)
        return None

    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """Parse activity date from Fitbit activity"""
        start_time = activity.get("startTime")
        start_date = activity.get("startDate")

        if start_time and start_date:
            datetime_str = f"{start_date}T{start_time}"
            return datetime.fromisoformat(datetime_str)

        return datetime.fromisoformat(start_date)
