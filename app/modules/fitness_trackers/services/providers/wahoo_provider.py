"""
Wahoo OAuth Provider Implementation
"""

from datetime import datetime, timedelta
from typing import Any

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider


class WahooProvider(OAuthProvider):
    """Wahoo Fitness OAuth 2.0 implementation"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.WAHOO

    @property
    def provider_name(self) -> str:
        return "Wahoo"

    @property
    def authorization_url(self) -> str:
        return "https://api.wahooligan.com/oauth/authorize"

    @property
    def token_url(self) -> str:
        return "https://api.wahooligan.com/oauth/token"

    @property
    def api_base_url(self) -> str:
        return "https://api.wahooligan.com/v1"

    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """Get Wahoo authorization parameters"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "workouts_read user_read",
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

        # Get user profile
        user_response = await self._make_http_request(
            "GET",
            f"{self.api_base_url}/user",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        user_data = user_response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
            "athlete_id": str(user_data["id"]),
            "athlete_data": user_data,
            "scope": data.get("scope", "workouts_read"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh Wahoo access token"""
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
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
        }

    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """Get Wahoo user profile"""
        response = await self._make_http_request(
            "GET", f"{self.api_base_url}/user", headers={"Authorization": f"Bearer {access_token}"}
        )

        return response.json()

    async def get_activities(
        self, access_token: str, sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """Get Wahoo workouts within sync window"""
        workouts = []
        page = 1
        per_page = 100

        while True:
            response = await self._make_http_request(
                "GET",
                f"{self.api_base_url}/workouts",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "starts_after": sync_window.start_date.isoformat(),
                    "starts_before": sync_window.end_date.isoformat(),
                    "page": page,
                    "per_page": per_page,
                },
            )

            data = response.json()
            page_workouts = data.get("workouts", [])

            if not page_workouts:
                break

            workouts.extend(page_workouts)
            page += 1

            # Safety limit
            if page > 10:
                break

        return workouts

    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """Parse distance from Wahoo workout (convert meters to km)"""
        distance_meters = activity.get("distance_meters", 0)
        return distance_meters / 1000.0

    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """Parse duration from Wahoo workout (convert seconds to minutes)"""
        duration_seconds = activity.get("duration_seconds")
        if duration_seconds:
            return int(duration_seconds / 60)
        return None

    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """Parse activity date from Wahoo workout"""
        starts_at_str = activity.get("starts_at")
        return datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
