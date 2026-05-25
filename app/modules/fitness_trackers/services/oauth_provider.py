"""
Abstract OAuth Provider Base Class

Defines the interface that all fitness tracker providers must implement.
This enables a unified API for all OAuth integrations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

from app.modules.fitness_trackers.domain.value_objects import (
    ProviderType,
    SyncWindow,
)


class OAuthProvider(ABC):
    """
    Abstract base class for OAuth fitness tracker providers.

    All providers (Strava, Garmin, Fitbit, etc.) inherit from this
    and implement provider-specific logic.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ):
        """
        Initialize OAuth provider.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Get provider type enum"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get human-readable provider name"""
        pass

    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """Get OAuth authorization URL base"""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """Get OAuth token exchange URL"""
        pass

    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """Get API base URL"""
        pass

    @abstractmethod
    def get_authorization_params(self, state: str | None = None) -> dict[str, str]:
        """
        Get OAuth authorization parameters.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Dict of authorization parameters
        """
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code

        Returns:
            Dict with token data

        Raises:
            HTTPException: If token exchange fails
        """
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new token data

        Raises:
            HTTPException: If refresh fails
        """
        pass

    @abstractmethod
    async def get_athlete_profile(self, access_token: str) -> dict[str, Any]:
        """
        Get athlete profile from provider.

        Args:
            access_token: Access token

        Returns:
            Dict with athlete data

        Raises:
            HTTPException: If API call fails
        """
        pass

    @abstractmethod
    async def get_activities(
        self,
        access_token: str,
        sync_window: SyncWindow
    ) -> list[dict[str, Any]]:
        """
        Get activities from provider within sync window.

        Args:
            access_token: Access token
            sync_window: Time window for activities

        Returns:
            List of activity dicts

        Raises:
            HTTPException: If API call fails
        """
        pass

    @abstractmethod
    def parse_activity_distance(self, activity: dict[str, Any]) -> float:
        """
        Parse distance from activity data (in kilometers).

        Args:
            activity: Provider-specific activity dict

        Returns:
            Distance in kilometers
        """
        pass

    @abstractmethod
    def parse_activity_duration(self, activity: dict[str, Any]) -> int | None:
        """
        Parse duration from activity data (in minutes).

        Args:
            activity: Provider-specific activity dict

        Returns:
            Duration in minutes or None
        """
        pass

    @abstractmethod
    def parse_activity_date(self, activity: dict[str, Any]) -> datetime:
        """
        Parse activity date from activity data.

        Args:
            activity: Provider-specific activity dict

        Returns:
            Activity datetime
        """
        pass

    def get_full_authorization_url(self, state: str | None = None) -> str:
        """
        Get complete authorization URL with parameters.

        Args:
            state: Optional state parameter

        Returns:
            Full authorization URL
        """
        params = self.get_authorization_params(state)
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authorization_url}?{param_str}"

    async def _make_http_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            httpx.Response

        Raises:
            HTTPException: If request fails
        """
        from fastapi import HTTPException
        from fastapi import status as http_status

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=http_status.HTTP_502_BAD_GATEWAY,
                    detail=f"{self.provider_name} API error: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"{self.provider_name} API unavailable: {str(e)}"
                )

    def supports_webhook(self) -> bool:
        """
        Check if provider supports webhooks.

        Default: False. Override in provider if supported.

        Returns:
            True if webhooks supported
        """
        return False

    async def subscribe_webhook(
        self,
        callback_url: str,
        access_token: str
    ) -> str | None:
        """
        Subscribe to webhook notifications.

        Default: Not implemented. Override in provider if supported.

        Args:
            callback_url: Callback URL for webhook
            access_token: Access token

        Returns:
            Subscription ID or None

        Raises:
            NotImplementedError: If not supported
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support webhooks"
        )

    async def unsubscribe_webhook(
        self,
        subscription_id: str,
        access_token: str
    ) -> bool:
        """
        Unsubscribe from webhook notifications.

        Default: Not implemented. Override in provider if supported.

        Args:
            subscription_id: Subscription ID
            access_token: Access token

        Returns:
            True if successful

        Raises:
            NotImplementedError: If not supported
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support webhooks"
        )

    def calculate_sync_stats(
        self,
        activities: list[dict[str, Any]]
    ) -> tuple[float, int]:
        """
        Calculate total distance and duration from activities.

        Args:
            activities: List of activity dicts

        Returns:
            Tuple of (total_distance_km, total_duration_minutes)
        """
        total_distance = 0.0
        total_duration = 0

        for activity in activities:
            total_distance += self.parse_activity_distance(activity)
            duration = self.parse_activity_duration(activity)
            if duration:
                total_duration += duration

        return total_distance, total_duration
