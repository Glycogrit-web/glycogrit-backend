"""
Garmin OAuth Provider Implementation
"""

from datetime import datetime
from typing import Any

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider


class GarminProvider(OAuthProvider):
    """Garmin Connect OAuth implementation"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GARMIN

    @property
    def provider_name(self) -> str:
        return "Garmin"

    @property
    def authorization_url(self) -> str:
        return "https://connect.garmin.com/oauthConfirm"

    @property
    def token_url(self) -> str:
        return "https://connect.garmin.com/oauth/token"

    @property
    def api_base_url(self) -> str:
        return "https://apis.garmin.com/wellness-api/rest"

    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """Get Garmin authorization parameters"""
        params = {
            "oauth_consumer_key": self.client_id,
            "oauth_signature_method": "HMAC-SHA1",
        }
        if state:
            params["state"] = state
        return params

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens (OAuth 1.0a)"""
        # Garmin uses OAuth 1.0a, different flow than 2.0
        response = await self._make_http_request(
            "POST",
            self.token_url,
            data={
                "oauth_token": code,
                "oauth_consumer_key": self.client_id,
            },
        )

        data = response.json()

        return {
            "access_token": data["oauth_token"],
            "refresh_token": data["oauth_token_secret"],
            "expires_at": None,  # Garmin tokens don't expire
            "athlete_id": str(data.get("user_id", data.get("oauth_token"))),
            "athlete_data": {},
            "scope": "wellness",
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Garmin tokens don't expire - return current token"""
        return {
            "access_token": refresh_token,
            "refresh_token": refresh_token,
            "expires_at": None,
        }

    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """Get Garmin user profile"""
        response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/user/id",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        return response.json()

    async def get_activities(
        self, access_token: str, sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """Get Garmin activities within sync window"""
        # Format dates for Garmin API
        sync_window.start_date.strftime("%Y-%m-%d")
        sync_window.end_date.strftime("%Y-%m-%d")

        response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "uploadStartTimeInSeconds": int(sync_window.start_date.timestamp()),
                "uploadEndTimeInSeconds": int(sync_window.end_date.timestamp()),
            },
        )

        return response.json()

    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """Parse distance from Garmin activity (already in km)"""
        return activity.get("distance", 0.0) / 1000.0  # meters to km

    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """Parse duration from Garmin activity (convert seconds to minutes)"""
        duration_seconds = activity.get("duration")
        if duration_seconds:
            return int(duration_seconds / 60)
        return None

    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """Parse activity date from Garmin activity"""
        start_time_str = activity.get("startTimeGMT", activity.get("startTimeLocal"))
        return datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))

    def supports_webhook(self) -> bool:
        """Garmin supports webhooks (push notifications)"""
        return True

    async def subscribe_webhook(self, callback_url: str, access_token: str) -> str | None:
        """Subscribe to Garmin push notifications"""
        response = await self._make_http_request(
            "POST",
            f"{self.api_base_url}/push/subscriptions",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "callbackUrl": callback_url,
            },
        )

        data = response.json()
        return str(data.get("subscriptionId"))

    async def unsubscribe_webhook(self, subscription_id: str, access_token: str) -> bool:
        """Unsubscribe from Garmin push notifications"""
        await self._make_http_request(
            "DELETE",
            f"{self.api_base_url}/push/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        return True
