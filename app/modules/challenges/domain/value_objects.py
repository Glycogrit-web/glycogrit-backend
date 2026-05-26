"""
Challenge Value Objects
"""

from dataclasses import dataclass
from enum import Enum


class ChallengeStatus(str, Enum):
    """Challenge completion status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BadgeLevel(str, Enum):
    """Badge achievement levels"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass(frozen=True)
class StreakDays:
    """Consecutive days streak"""

    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Streak days cannot be negative")

    @classmethod
    def zero(cls) -> "StreakDays":
        return cls(0)


@dataclass(frozen=True)
class ChallengeProgress:
    """Challenge progress calculation"""

    current_distance: float
    target_distance: float

    def __post_init__(self):
        if self.target_distance <= 0:
            raise ValueError("Target distance must be positive")
        if self.current_distance < 0:
            raise ValueError("Current distance cannot be negative")

    @property
    def percentage(self) -> float:
        """Progress percentage (0-100)"""
        if self.target_distance == 0:
            return 0.0
        return min(100.0, (self.current_distance / self.target_distance) * 100.0)

    @property
    def is_complete(self) -> bool:
        """Check if challenge is complete"""
        return self.current_distance >= self.target_distance

    @property
    def remaining_distance(self) -> float:
        """Remaining distance to goal"""
        return max(0.0, self.target_distance - self.current_distance)
