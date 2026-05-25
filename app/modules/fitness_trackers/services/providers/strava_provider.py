"""
Strava OAuth Provider Implementation
"""

from datetime import datetime
from typing import Any

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider


class StravaProvider(OAuthProvider):
    """Strava-specific OAuth implementation"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.STRAVA

    @property
    def provider_name(self) -> str:
        return "Strava"

    @property
    def authorization_url(self) -> str:
        return "https://www.strava.com/oauth/authorize"

    @property
    def token_url(self) -> str:
        return "https://www.strava.com/oauth/token"

    @property
    def api_base_url(self) -> str:
        return "https://www.strava.com/api/v3"

    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """Get Strava authorization parameters"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "read,activity:read_all",
            "approval_prompt": "auto",
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
            }
        )

        data = response.json()

        # Strava returns athlete data with token response
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": datetime.fromtimestamp(data["expires_at"]),
            "athlete_id": str(data["athlete"]["id"]),
            "athlete_data": data["athlete"],
            "scope": data.get("scope", "read,activity:read_all"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh Strava access token"""
        response = await self._make_http_request(
            "POST",
            self.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": datetime.fromtimestamp(data["expires_at"]),
        }

    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """Get Strava athlete profile"""
        response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/athlete",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        return response.json()

    async def get_activities(
        self,
        access_token: str,
        sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """Get Strava activities within sync window"""
        activities = []
        page = 1
        per_page = 100

        # Convert to Unix timestamps
        after = int(sync_window.start_date.timestamp())
        before = int(sync_window.end_date.timestamp())

        while True:
            params = {
                "after": after,
                "before": before,
                "page": page,
                "per_page": per_page,
            }

            response = await self._make_http_request(
                "GET",
                f"{self.api_base_url}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )

            page_activities = response.json()

            if not page_activities:
                break

            activities.extend(page_activities)
            page += 1

            # Safety limit
            if page > 10:
                break

        return activities

    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """Parse distance from Strava activity (convert meters to km)"""
        distance_meters = activity.get("distance", 0)
        return distance_meters / 1000.0

    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """Parse duration from Strava activity (convert seconds to minutes)"""
        moving_time_seconds = activity.get("moving_time")
        if moving_time_seconds:
            return int(moving_time_seconds / 60)
        return None

    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """Parse activity date from Strava activity"""
        start_date_str = activity.get("start_date", activity.get("start_date_local"))
        return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

    def supports_webhook(self) -> bool:
        """Strava supports webhooks"""
        return True

    async def subscribe_webhook(
        self,
        callback_url: str,
        access_token: str
    ) -> str | None:
        """Subscribe to Strava webhook"""
        # Strava webhook subscription
        # Note: Strava uses application-level subscriptions, not user-level
        response = await self._make_http_request(
            "POST",
            "https://www.strava.com/api/v3/push_subscriptions",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "callback_url": callback_url,
                "verify_token": "STRAVA_WEBHOOK_VERIFY",
            }
        )

        data = response.json()
        return str(data.get("id"))

    async def unsubscribe_webhook(
        self,
        subscription_id: str,
        access_token: str
    ) -> bool:
        """Unsubscribe from Strava webhook"""
        await self._make_http_request(
            "DELETE",
            f"https://www.strava.com/api/v3/push_subscriptions/{subscription_id}",
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )

        return True
