"""
OAuth Provider Manager

Centralizes OAuth provider configuration and operations to reduce
code duplication across fitness tracker integrations.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


@dataclass
class OAuthConfig:
    """Configuration for an OAuth provider"""
    provider_name: str
    display_name: str
    client_id_env: str
    client_secret_env: str
    redirect_uri_env: str
    authorization_url: str
    token_url: str
    scopes: list[str]
    extra_params: dict[str, str] | None = None


class OAuthProvider(ABC):
    """Base class for OAuth providers"""

    def __init__(self, config: OAuthConfig):
        self.config = config
        self.client_id = os.getenv(config.client_id_env)
        self.client_secret = os.getenv(config.client_secret_env)
        self.redirect_uri = os.getenv(config.redirect_uri_env)

    def validate_configuration(self) -> None:
        """Validate that required environment variables are set"""
        if not self.client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{self.config.display_name} integration not configured"
            )

    def get_authorization_url(self) -> str:
        """
        Build OAuth authorization URL

        Returns:
            Authorization URL string
        """
        self.validate_configuration()

        scope_str = " ".join(self.config.scopes)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_str,
        }

        if self.config.extra_params:
            params.update(self.config.extra_params)

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.config.authorization_url}?{query_string}"

    async def exchange_code_for_tokens(self, auth_code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary with token data

        Raises:
            HTTPException: If token exchange fails
        """
        self.validate_configuration()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "code": auth_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed for {self.config.provider_name}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code: {response.text}"
                )

            token_data = response.json()

            if not token_data.get("refresh_token"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No refresh token received. User may need to revoke access and reconnect."
                )

            return token_data

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary with new token data
        """
        self.validate_configuration()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token"
                }
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed for {self.config.provider_name}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to refresh token"
                )

            return response.json()

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from the provider

        Args:
            access_token: Access token

        Returns:
            User info dictionary
        """
        pass


class GoogleFitProvider(OAuthProvider):
    """Google Fit OAuth provider"""

    def __init__(self):
        config = OAuthConfig(
            provider_name="google_fit",
            display_name="Google Fit",
            client_id_env="GOOGLE_FIT_CLIENT_ID",
            client_secret_env="GOOGLE_FIT_CLIENT_SECRET",
            redirect_uri_env="GOOGLE_FIT_REDIRECT_URI",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[
                "https://www.googleapis.com/auth/fitness.activity.read",
                "https://www.googleapis.com/auth/fitness.location.read",
                "https://www.googleapis.com/auth/userinfo.email"
            ],
            extra_params={
                "access_type": "offline",
                "prompt": "consent"
            }
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get Google user info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class StravaProvider(OAuthProvider):
    """Strava OAuth provider"""

    def __init__(self):
        config = OAuthConfig(
            provider_name="strava",
            display_name="Strava",
            client_id_env="STRAVA_CLIENT_ID",
            client_secret_env="STRAVA_CLIENT_SECRET",
            redirect_uri_env="STRAVA_REDIRECT_URI",
            authorization_url="https://www.strava.com/oauth/authorize",
            token_url="https://www.strava.com/oauth/token",
            scopes=["activity:read_all", "profile:read_all"],
            extra_params={"approval_prompt": "force"}
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get Strava athlete info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.strava.com/api/v3/athlete",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class FitbitProvider(OAuthProvider):
    """Fitbit OAuth provider (via Google Health API)"""

    def __init__(self):
        config = OAuthConfig(
            provider_name="fitbit",
            display_name="Fitbit",
            client_id_env="FITBIT_CLIENT_ID",
            client_secret_env="FITBIT_CLIENT_SECRET",
            redirect_uri_env="FITBIT_REDIRECT_URI",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[
                "https://www.googleapis.com/auth/fitness.activity.read",
                "https://www.googleapis.com/auth/fitness.location.read",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            extra_params={
                "access_type": "offline",
                "prompt": "consent"
            }
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get Fitbit user info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class WahooProvider(OAuthProvider):
    """Wahoo OAuth provider"""

    def __init__(self):
        config = OAuthConfig(
            provider_name="wahoo",
            display_name="Wahoo",
            client_id_env="WAHOO_CLIENT_ID",
            client_secret_env="WAHOO_CLIENT_SECRET",
            redirect_uri_env="WAHOO_REDIRECT_URI",
            authorization_url="https://api.wahooligan.com/oauth/authorize",
            token_url="https://api.wahooligan.com/oauth/token",
            scopes=["workouts_read", "user_read"]
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get Wahoo user info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.wahooligan.com/v1/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class GarminProvider(OAuthProvider):
    """Garmin OAuth provider"""

    def __init__(self):
        config = OAuthConfig(
            provider_name="garmin",
            display_name="Garmin",
            client_id_env="GARMIN_CLIENT_ID",
            client_secret_env="GARMIN_CLIENT_SECRET",
            redirect_uri_env="GARMIN_REDIRECT_URI",
            authorization_url="https://connect.garmin.com/oauthConfirm",
            token_url="https://connect.garmin.com/oauth/token",
            scopes=["activity:read"]
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get Garmin user info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://connect.garmin.com/userprofile-service/userprofile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class OAuthProviderManager:
    """
    Manager for OAuth providers.

    Provides a centralized interface for OAuth operations across
    all fitness tracker providers.
    """

    _providers: dict[str, OAuthProvider] = {
        "google_fit": GoogleFitProvider(),
        "strava": StravaProvider(),
        "fitbit": FitbitProvider(),
        "wahoo": WahooProvider(),
        "garmin": GarminProvider(),
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> OAuthProvider:
        """
        Get OAuth provider by name

        Args:
            provider_name: Provider identifier

        Returns:
            OAuthProvider instance

        Raises:
            HTTPException: If provider not found
        """
        provider = cls._providers.get(provider_name)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {provider_name}"
            )
        return provider

    @classmethod
    def get_authorization_url(cls, provider_name: str) -> str:
        """
        Get authorization URL for provider

        Args:
            provider_name: Provider identifier

        Returns:
            Authorization URL
        """
        provider = cls.get_provider(provider_name)
        return provider.get_authorization_url()

    @classmethod
    async def handle_callback(
        cls,
        provider_name: str,
        auth_code: str
    ) -> dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens

        Args:
            provider_name: Provider identifier
            auth_code: Authorization code

        Returns:
            Token data dictionary with access_token, refresh_token, expires_in
        """
        provider = cls.get_provider(provider_name)
        token_data = await provider.exchange_code_for_tokens(auth_code)

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

        # Get user info
        user_info = await provider.get_user_info(token_data["access_token"])

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": expires_at,
            "scope": token_data.get("scope"),
            "user_info": user_info
        }

    @classmethod
    async def refresh_token(cls, provider_name: str, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token

        Args:
            provider_name: Provider identifier
            refresh_token: Refresh token

        Returns:
            New token data
        """
        provider = cls.get_provider(provider_name)
        return await provider.refresh_access_token(refresh_token)

    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        """
        Check if provider is supported

        Args:
            provider_name: Provider identifier

        Returns:
            True if supported, False otherwise
        """
        return provider_name in cls._providers

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        Get list of all supported providers

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
