"""
Google Fit Configuration
Centralized settings for Google Fit integration
"""

from typing import Dict, Any


class GoogleFitConfig:
    """
    Configuration settings for Google Fit API integration
    """

    # ===== API ENDPOINTS =====
    API_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    # ===== OAUTH SCOPES =====
    # Required scopes for reading fitness data
    OAUTH_SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",  # User email for profile
        "https://www.googleapis.com/auth/userinfo.profile",  # User profile info
        "https://www.googleapis.com/auth/fitness.activity.read",  # Read activity data
        "https://www.googleapis.com/auth/fitness.location.read",  # Read location data for routes
    ]

    OAUTH_SCOPE_STRING = " ".join(OAUTH_SCOPES)

    # ===== DATA TYPE NAMES =====
    # Google Fit data type identifiers
    DATA_TYPES = {
        "distance": "com.google.distance.delta",
        "steps": "com.google.step_count.delta",
        "calories": "com.google.calories.expended",
        "heart_rate": "com.google.heart_rate.bpm",
        "speed": "com.google.speed",
        "activity": "com.google.activity.segment",
    }

    # ===== DATA SOURCE IDs =====
    # Merged/derived data sources (aggregated from multiple sources)
    DATA_SOURCES = {
        "distance_merged": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta",
        "steps_merged": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
        "calories_merged": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
    }

    # ===== ACTIVITY TYPE IDs =====
    # Google Fit activity type constants
    # See: https://developers.google.com/fit/rest/v1/reference/activity-types
    ACTIVITY_TYPES = {
        "running": 8,
        "walking": 7,
        "cycling": 1,
        "hiking": 35,
        "swimming": 82,
        "workout": 9,
        "other": 108,
    }

    # Reverse mapping: ID -> name
    ACTIVITY_TYPE_NAMES = {v: k for k, v in ACTIVITY_TYPES.items()}

    # ===== SYNC SETTINGS =====
    # Default sync window (days)
    DEFAULT_SYNC_DAYS = 30

    # Maximum sync window to prevent API overload (days)
    MAX_SYNC_WINDOW_DAYS = 365

    # Throttle duration: minimum time between syncs (seconds)
    SYNC_THROTTLE_SECONDS = 3600  # 1 hour

    # Force sync bypasses throttle
    ALLOW_FORCE_SYNC = True

    # ===== DISTANCE CALCULATION =====
    # Minimum distance to consider as valid activity (meters)
    MIN_DISTANCE_THRESHOLD_METERS = 100  # 0.1 km

    # Conversion factor: meters to kilometers
    METERS_TO_KM = 0.001

    # ===== TIMEOUT SETTINGS =====
    # HTTP request timeout (seconds)
    REQUEST_TIMEOUT_SECONDS = 30

    # Token refresh timeout (seconds)
    TOKEN_REFRESH_TIMEOUT_SECONDS = 10

    # ===== ERROR HANDLING =====
    # Maximum retry attempts for failed API calls
    MAX_RETRY_ATTEMPTS = 3

    # Retry delay (seconds)
    RETRY_DELAY_SECONDS = 2

    # ===== LOGGING =====
    # Enable detailed request/response logging
    ENABLE_DEBUG_LOGGING = False

    # Log activity data details
    LOG_ACTIVITY_DETAILS = True

    # ===== PROVIDER METADATA =====
    PROVIDER_NAME = "google_fit"
    DISPLAY_NAME = "Google Fit"
    SUPPORTS_OAUTH = True
    REQUIRES_FILE_UPLOAD = False

    # ===== SESSION FILTERING =====
    # Activity types to include (None = all types)
    INCLUDE_ACTIVITY_TYPES = None  # [1, 7, 8]  # cycling, walking, running

    # Activity types to exclude
    EXCLUDE_ACTIVITY_TYPES = None

    # Minimum session duration to include (seconds)
    MIN_SESSION_DURATION_SECONDS = 60  # 1 minute

    # ===== RESPONSE FORMAT =====
    # RFC3339 timestamp format for sessions API
    TIMESTAMP_FORMAT_RFC3339 = "%Y-%m-%dT%H:%M:%S.%fZ"

    # Date format for logging
    DATE_FORMAT_LOG = "%Y-%m-%d %H:%M:%S"

    # ===== FEATURES =====
    # Support for passive movement tracking (no explicit sessions)
    SUPPORT_PASSIVE_MOVEMENT = True

    # Support for heart rate data
    SUPPORT_HEART_RATE = True

    # Support for GPS routes
    SUPPORT_GPS_ROUTES = True

    # ===== VALIDATION =====
    # Maximum reasonable distance for single session (km)
    MAX_SESSION_DISTANCE_KM = 500

    # Maximum reasonable speed (km/h)
    MAX_REASONABLE_SPEED_KMH = 50

    @classmethod
    def get_oauth_params(cls, redirect_uri: str, client_id: str) -> Dict[str, str]:
        """
        Get OAuth authorization parameters
        """
        return {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": cls.OAUTH_SCOPE_STRING,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Always show consent screen for refresh token
        }

    @classmethod
    def get_activity_type_name(cls, type_id: int) -> str:
        """
        Get human-readable activity type name from ID
        """
        return cls.ACTIVITY_TYPE_NAMES.get(type_id, "other")

    @classmethod
    def is_valid_distance(cls, distance_meters: float) -> bool:
        """
        Check if distance value is valid
        """
        return (
            distance_meters >= cls.MIN_DISTANCE_THRESHOLD_METERS
            and distance_meters <= cls.MAX_SESSION_DISTANCE_KM * 1000
        )

    @classmethod
    def should_include_session(cls, session: Dict[str, Any]) -> bool:
        """
        Determine if a session should be included based on filters
        """
        # Check activity type filter
        if cls.INCLUDE_ACTIVITY_TYPES:
            activity_type = session.get("activityType")
            if activity_type not in cls.INCLUDE_ACTIVITY_TYPES:
                return False

        if cls.EXCLUDE_ACTIVITY_TYPES:
            activity_type = session.get("activityType")
            if activity_type in cls.EXCLUDE_ACTIVITY_TYPES:
                return False

        # Check duration filter
        start_ms = int(session.get("startTimeMillis", 0))
        end_ms = int(session.get("endTimeMillis", 0))
        duration_sec = (end_ms - start_ms) / 1000

        if duration_sec < cls.MIN_SESSION_DURATION_SECONDS:
            return False

        return True
