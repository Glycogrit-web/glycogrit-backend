"""
Fitness Trackers Value Objects

Immutable, validated domain primitives for fitness tracker integrations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class ProviderType(str, Enum):
    """Supported fitness tracker providers"""

    STRAVA = "strava"
    FITBIT = "fitbit"
    GOOGLE_FIT = "google_fit"
    GOOGLE_HEALTH = "google_health"
    POLAR = "polar"


class OAuthScope(str, Enum):
    """OAuth permission scopes"""

    READ = "read"
    READ_ALL = "read_all"
    ACTIVITY_READ = "activity:read"
    ACTIVITY_READ_ALL = "activity:read_all"
    ACTIVITY_WRITE = "activity:write"
    PROFILE = "profile"


@dataclass(frozen=True)
class AccessToken:
    """OAuth access token with expiration"""

    value: str
    expires_at: datetime

    def __post_init__(self):
        if not self.value:
            raise ValueError("Access token cannot be empty")

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def expires_in_seconds(self) -> int:
        """Get seconds until expiration"""
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expires in < 1 hour)"""
        return self.expires_in_seconds < 3600


@dataclass(frozen=True)
class RefreshToken:
    """OAuth refresh token"""

    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Refresh token cannot be empty")


@dataclass(frozen=True)
class AthleteId:
    """Provider-specific athlete ID"""

    provider: ProviderType
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Athlete ID cannot be empty")

    def __str__(self) -> str:
        return f"{self.provider.value}:{self.value}"


@dataclass(frozen=True)
class SyncWindow:
    """Time window for activity synchronization"""

    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

        # Validate window is not too large (max 1 year)
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Sync window cannot exceed 1 year")

        # Validate end date is not in the future (allow 5 second tolerance for clock skew)
        now = datetime.now(timezone.utc)
        if self.end_date > now + timedelta(seconds=5):
            raise ValueError(
                f"Sync window end date cannot be in the future. "
                f"End: {self.end_date.isoformat()}, Now: {now.isoformat()}"
            )

    @property
    def days(self) -> int:
        """Get number of days in window"""
        return (self.end_date - self.start_date).days

    @classmethod
    def last_n_days(cls, days: int) -> "SyncWindow":
        """Create window for last N days"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return cls(start, end)

    @classmethod
    def since(cls, start_date: datetime) -> "SyncWindow":
        """Create window from date to now"""
        return cls(start_date, datetime.now(timezone.utc))


@dataclass(frozen=True)
class ActivityCount:
    """Number of activities synced"""

    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Activity count cannot be negative")

    def __add__(self, other: "ActivityCount") -> "ActivityCount":
        return ActivityCount(self.value + other.value)

    @classmethod
    def zero(cls) -> "ActivityCount":
        return cls(0)


@dataclass(frozen=True)
class SyncStatus:
    """Status of sync operation"""

    is_success: bool
    activities_synced: ActivityCount
    error_message: str | None = None

    @classmethod
    def success(cls, count: ActivityCount) -> "SyncStatus":
        return cls(True, count, None)

    @classmethod
    def failure(cls, error: str) -> "SyncStatus":
        return cls(False, ActivityCount.zero(), error)


@dataclass(frozen=True)
class WebhookSubscription:
    """Webhook subscription details"""

    provider: ProviderType
    subscription_id: str
    callback_url: str
    is_active: bool

    def __post_init__(self):
        if not self.subscription_id:
            raise ValueError("Subscription ID cannot be empty")
        if not self.callback_url:
            raise ValueError("Callback URL cannot be empty")
        if not self.callback_url.startswith(("http://", "https://")):
            raise ValueError("Callback URL must be HTTP(S)")
