"""
OAuth Provider Factory
Centralized provider instantiation
"""

from typing import Dict, Type
from .base import OAuthProvider
from .providers.strava import StravaOAuthProvider
from .providers.fitbit import FitbitOAuthProvider
from .providers.garmin import GarminOAuthProvider


class OAuthProviderFactory:
    """
    Factory for creating OAuth provider instances

    Usage:
        provider = OAuthProviderFactory.get_provider("strava")
        auth_url = provider.get_authorization_url()
    """

    _providers: Dict[str, Type[OAuthProvider]] = {
        "strava": StravaOAuthProvider,
        "fitbit": FitbitOAuthProvider,
        # Note: Garmin uses OAuth 1.0a, so it's handled separately
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> OAuthProvider:
        """
        Get OAuth provider instance by name

        Args:
            provider_name: Name of the provider (strava, fitbit, garmin, etc.)

        Returns:
            OAuth provider instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())

        if not provider_class:
            raise ValueError(
                f"Unknown OAuth provider: {provider_name}. "
                f"Supported providers: {', '.join(cls._providers.keys())}"
            )

        return provider_class()

    @classmethod
    def get_garmin_provider(cls) -> GarminOAuthProvider:
        """Get Garmin provider (OAuth 1.0a)"""
        return GarminOAuthProvider()

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[OAuthProvider]):
        """
        Register a new OAuth provider

        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names"""
        return list(cls._providers.keys()) + ["garmin"]
