"""
Unified OAuth Integration Framework
Reduces boilerplate code for OAuth providers (Strava, Fitbit, Garmin, etc.)
"""

from .base import OAuthProvider, OAuthConfig, OAuthTokens, OAuthCallbackResult
from .exceptions import OAuthException, TokenRefreshException, ProviderConfigException

__all__ = [
    "OAuthProvider",
    "OAuthConfig",
    "OAuthTokens",
    "OAuthCallbackResult",
    "OAuthException",
    "TokenRefreshException",
    "ProviderConfigException",
]
