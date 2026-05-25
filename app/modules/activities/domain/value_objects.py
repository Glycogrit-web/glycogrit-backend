"""
Value Objects for Activities Domain

Value objects are immutable and defined by their attributes.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class ActivityType(str, Enum):
    """Activity type enumeration"""
    RUN = "run"
    RIDE = "ride"
    WALK = "walk"
    SWIM = "swim"
    OTHER = "other"


class SyncSource(str, Enum):
    """Activity sync source enumeration"""
    MANUAL = "manual"
    STRAVA = "strava"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    WAHOO = "wahoo"
    GOOGLE_FIT = "google_fit"
    ADMIN_MANUAL = "admin_manual"


@dataclass(frozen=True)
class Distance:
    """
    Distance value object.

    Business Rules:
    - Must be non-negative
    - Stored in kilometers
    - Up to 2 decimal places precision
    """
    kilometers: Decimal

    def __post_init__(self):
        """Validate distance"""
        if self.kilometers < 0:
            raise ValueError("Distance cannot be negative")

        # Round to 2 decimal places
        object.__setattr__(self, 'kilometers', round(Decimal(str(self.kilometers)), 2))

    def __str__(self) -> str:
        return f"{float(self.kilometers):.2f} km"

    def __float__(self) -> float:
        return float(self.kilometers)

    def __add__(self, other: 'Distance') -> 'Distance':
        """Add two distances"""
        if not isinstance(other, Distance):
            raise TypeError("Can only add Distance to Distance")
        return Distance(self.kilometers + other.kilometers)

    def __sub__(self, other: 'Distance') -> 'Distance':
        """Subtract distances"""
        if not isinstance(other, Distance):
            raise TypeError("Can only subtract Distance from Distance")
        result = self.kilometers - other.kilometers
        if result < 0:
            raise ValueError("Result distance cannot be negative")
        return Distance(result)

    def __ge__(self, other: 'Distance') -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Distance):
            raise TypeError("Can only compare Distance with Distance")
        return self.kilometers >= other.kilometers

    def __le__(self, other: 'Distance') -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Distance):
            raise TypeError("Can only compare Distance with Distance")
        return self.kilometers <= other.kilometers

    def __gt__(self, other: 'Distance') -> bool:
        """Greater than comparison"""
        if not isinstance(other, Distance):
            raise TypeError("Can only compare Distance with Distance")
        return self.kilometers > other.kilometers

    def __lt__(self, other: 'Distance') -> bool:
        """Less than comparison"""
        if not isinstance(other, Distance):
            raise TypeError("Can only compare Distance with Distance")
        return self.kilometers < other.kilometers

    @property
    def miles(self) -> float:
        """Convert to miles"""
        return float(self.kilometers) * 0.621371

    @property
    def meters(self) -> float:
        """Convert to meters"""
        return float(self.kilometers) * 1000

    @classmethod
    def from_miles(cls, miles: float) -> 'Distance':
        """Create distance from miles"""
        return cls(Decimal(str(miles / 0.621371)))

    @classmethod
    def from_meters(cls, meters: float) -> 'Distance':
        """Create distance from meters"""
        return cls(Decimal(str(meters / 1000)))

    @classmethod
    def zero(cls) -> 'Distance':
        """Create zero distance"""
        return cls(Decimal('0.00'))


@dataclass(frozen=True)
class Duration:
    """
    Duration value object.

    Business Rules:
    - Must be non-negative
    - Stored in minutes
    """
    minutes: int

    def __post_init__(self):
        """Validate duration"""
        if self.minutes < 0:
            raise ValueError("Duration cannot be negative")

    def __str__(self) -> str:
        hours = self.minutes // 60
        mins = self.minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def __int__(self) -> int:
        return self.minutes

    def __add__(self, other: 'Duration') -> 'Duration':
        """Add two durations"""
        if not isinstance(other, Duration):
            raise TypeError("Can only add Duration to Duration")
        return Duration(self.minutes + other.minutes)

    @property
    def hours(self) -> float:
        """Get duration in hours"""
        return self.minutes / 60.0

    @property
    def seconds(self) -> int:
        """Get duration in seconds"""
        return self.minutes * 60

    @classmethod
    def from_hours(cls, hours: float) -> 'Duration':
        """Create duration from hours"""
        return cls(int(hours * 60))

    @classmethod
    def from_seconds(cls, seconds: int) -> 'Duration':
        """Create duration from seconds"""
        return cls(seconds // 60)

    @classmethod
    def zero(cls) -> 'Duration':
        """Create zero duration"""
        return cls(0)


@dataclass(frozen=True)
class ActivityDate:
    """
    Activity date value object.

    Business Rules:
    - Cannot be in the future
    - Reasonable range (not too far in the past)
    """
    value: date

    def __post_init__(self):
        """Validate activity date"""
        today = date.today()

        # Cannot be in future
        if self.value > today:
            raise ValueError("Activity date cannot be in the future")

        # Reasonable range (not more than 10 years ago)
        from datetime import timedelta
        ten_years_ago = today - timedelta(days=365 * 10)
        if self.value < ten_years_ago:
            raise ValueError("Activity date cannot be more than 10 years in the past")

    def __str__(self) -> str:
        return self.value.isoformat()

    def __eq__(self, other) -> bool:
        if isinstance(other, ActivityDate):
            return self.value == other.value
        return False

    def __lt__(self, other: 'ActivityDate') -> bool:
        if not isinstance(other, ActivityDate):
            raise TypeError("Can only compare ActivityDate with ActivityDate")
        return self.value < other.value

    def __le__(self, other: 'ActivityDate') -> bool:
        if not isinstance(other, ActivityDate):
            raise TypeError("Can only compare ActivityDate with ActivityDate")
        return self.value <= other.value

    def is_today(self) -> bool:
        """Check if activity was today"""
        return self.value == date.today()

    def days_ago(self) -> int:
        """Calculate how many days ago the activity was"""
        return (date.today() - self.value).days


@dataclass(frozen=True)
class ProgressPercentage:
    """
    Progress percentage value object.

    Business Rules:
    - Must be between 0 and 100
    - Rounded to 1 decimal place
    """
    value: Decimal

    def __post_init__(self):
        """Validate percentage"""
        if self.value < 0 or self.value > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        # Round to 1 decimal place
        object.__setattr__(self, 'value', round(Decimal(str(self.value)), 1))

    def __str__(self) -> str:
        return f"{float(self.value):.1f}%"

    def __float__(self) -> float:
        return float(self.value)

    def is_complete(self) -> bool:
        """Check if progress is 100%"""
        return self.value >= 100

    @classmethod
    def calculate(cls, completed: Distance, target: Distance) -> 'ProgressPercentage':
        """Calculate percentage from distances"""
        if target.kilometers == 0:
            return cls(Decimal('0.0'))

        percentage = (completed.kilometers / target.kilometers) * 100
        return cls(min(percentage, Decimal('100.0')))


@dataclass(frozen=True)
class Pace:
    """
    Pace value object (min/km).

    Business Rules:
    - Calculated from distance and duration
    - Must be positive
    """
    minutes_per_km: Decimal

    def __post_init__(self):
        """Validate pace"""
        if self.minutes_per_km <= 0:
            raise ValueError("Pace must be positive")

    def __str__(self) -> str:
        minutes = int(self.minutes_per_km)
        seconds = int((self.minutes_per_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} /km"

    @classmethod
    def calculate(cls, distance: Distance, duration: Duration) -> Optional['Pace']:
        """Calculate pace from distance and duration"""
        if distance.kilometers == 0 or duration.minutes == 0:
            return None

        minutes_per_km = Decimal(str(duration.minutes)) / distance.kilometers
        return cls(minutes_per_km)

    @property
    def speed_kmh(self) -> float:
        """Get speed in km/h"""
        return 60.0 / float(self.minutes_per_km)
