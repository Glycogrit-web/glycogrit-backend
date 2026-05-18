"""
OAuth Provider Implementations
"""

from .strava import StravaOAuthProvider
from .fitbit import FitbitOAuthProvider
from .garmin import GarminOAuthProvider

__all__ = [
    "StravaOAuthProvider",
    "FitbitOAuthProvider",
    "GarminOAuthProvider",
]
