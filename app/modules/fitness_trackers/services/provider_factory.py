"""
OAuth Provider Factory

Creates appropriate provider instances based on provider type.
"""

import os

from app.modules.fitness_trackers.domain.value_objects import ProviderType
from app.modules.fitness_trackers.services.oauth_provider import OAuthProvider
from app.modules.fitness_trackers.services.providers.strava_provider import StravaProvider


class ProviderFactory:
    """Factory for creating OAuth provider instances"""

    # Provider configurations from environment
    CONFIGS: dict[ProviderType, dict[str, str]] = {
        ProviderType.STRAVA: {
            "client_id": os.getenv("STRAVA_CLIENT_ID", ""),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("STRAVA_REDIRECT_URI", ""),
        },
        ProviderType.FITBIT: {
            "client_id": os.getenv("FITBIT_CLIENT_ID", ""),
            "client_secret": os.getenv("FITBIT_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("FITBIT_REDIRECT_URI", ""),
        },
        ProviderType.GOOGLE_FIT: {
            "client_id": os.getenv("GOOGLE_FIT_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_FIT_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_FIT_REDIRECT_URI") or os.getenv("GOOGLE_REDIRECT_URI", ""),
        },
        ProviderType.GOOGLE_HEALTH: {
            "client_id": os.getenv("GOOGLE_HEALTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_HEALTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_HEALTH_REDIRECT_URI") or os.getenv("GOOGLE_REDIRECT_URI", ""),
        },
    }

    @classmethod
    def create(cls, provider_type: ProviderType) -> OAuthProvider:
        """
        Create provider instance.

        Args:
            provider_type: Provider type enum

        Returns:
            OAuthProvider instance

        Raises:
            ValueError: If provider not supported or missing config
        """
        config = cls.CONFIGS.get(provider_type)
        if not config:
            raise ValueError(f"Unsupported provider: {provider_type}")

        if not all([config["client_id"], config["client_secret"]]):
            raise ValueError(
                f"Missing configuration for {provider_type.value}. "
                f"Set {provider_type.value.upper()}_CLIENT_ID and "
                f"{provider_type.value.upper()}_CLIENT_SECRET environment variables."
            )

        # Import providers lazily to avoid circular imports
        if provider_type == ProviderType.STRAVA:
            return StravaProvider(**config)

        elif provider_type == ProviderType.GOOGLE_FIT:
            from app.modules.fitness_trackers.services.providers.google_fit_provider import GoogleFitProvider
            return GoogleFitProvider(**config)

        elif provider_type == ProviderType.GOOGLE_HEALTH:
            from app.modules.fitness_trackers.services.providers.google_health_provider import GoogleHealthProvider
            return GoogleHealthProvider(**config)

        # NOTE: Fitbit provider has template implementation but needs testing
        # and validation with actual API credentials before production use.
        # elif provider_type == ProviderType.FITBIT:
        #     from app.modules.fitness_trackers.services.providers.fitbit_provider import FitbitProvider
        #     return FitbitProvider(**config)

        raise NotImplementedError(
            f"Provider {provider_type.value} is not yet enabled. "
            f"Only Strava, Google Fit, and Google Health are currently available. "
            f"Framework is ready for {provider_type.value} - needs API credentials and testing."
        )

    @classmethod
    def is_configured(cls, provider_type: ProviderType) -> bool:
        """
        Check if provider is configured.

        Args:
            provider_type: Provider type

        Returns:
            True if provider has valid configuration
        """
        config = cls.CONFIGS.get(provider_type)
        if not config:
            return False
        return bool(config["client_id"] and config["client_secret"])

    @classmethod
    def get_available_providers(cls) -> list[ProviderType]:
        """
        Get list of configured providers.

        Returns:
            List of available ProviderType enums
        """
        return [provider_type for provider_type in ProviderType if cls.is_configured(provider_type)]
