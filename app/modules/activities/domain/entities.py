"""
Activity Entities - Contains business logic and rules

Entities are defined by their identity (ID) and contain business rules.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.modules.activities.domain.value_objects import (
    ActivityDate,
    Distance,
    Duration,
    Pace,
    ProgressPercentage,
    SyncSource,
)


class ActivityEntity:
    """
    Activity entity representing a user's activity submission.

    Business Rules:
    1. Activity date cannot be in future
    2. Activity must be within event date range (if applicable)
    3. Distance and duration must be non-negative
    4. User must own the activity
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        event_id: int,
        activity_date: ActivityDate,
        distance: Distance | None = None,
        duration: Duration | None = None,
        notes: str | None = None,
        registration_id: int | None = None,
        created_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.activity_date = activity_date
        self.distance = distance or Distance.zero()
        self.duration = duration or Duration.zero()
        self.notes = notes
        self.registration_id = registration_id
        self.created_at = created_at or datetime.utcnow()

        # Validate business rules
        self._validate()

    def _validate(self):
        """Validate business rules"""
        # Activity date validation is handled by ActivityDate value object
        pass

    @property
    def pace(self) -> Pace | None:
        """Calculate pace from distance and duration"""
        if self.distance.kilometers > 0 and self.duration.minutes > 0:
            return Pace.calculate(self.distance, self.duration)
        return None

    @property
    def has_distance(self) -> bool:
        """Check if activity has distance"""
        return self.distance.kilometers > 0

    @property
    def has_duration(self) -> bool:
        """Check if activity has duration"""
        return self.duration.minutes > 0

    def update(
        self,
        distance: Distance | None = None,
        duration: Duration | None = None,
        activity_date: ActivityDate | None = None,
        notes: str | None = None,
    ):
        """
        Update activity details.

        Business Rule: Can only update own activities
        """
        if distance is not None:
            self.distance = distance
        if duration is not None:
            self.duration = duration
        if activity_date is not None:
            self.activity_date = activity_date
        if notes is not None:
            self.notes = notes

    def can_be_deleted_by(self, user_id: int) -> bool:
        """
        Check if activity can be deleted by user.

        Business Rule: Only owner can delete
        """
        return self.user_id == user_id

    def can_be_edited_by(self, user_id: int) -> bool:
        """
        Check if activity can be edited by user.

        Business Rule: Only owner can edit
        """
        return self.user_id == user_id

    def __repr__(self) -> str:
        return f"<ActivityEntity(id={self.id}, user_id={self.user_id}, date={self.activity_date}, distance={self.distance})>"

    def __eq__(self, other) -> bool:
        """Entities are equal if they have the same ID"""
        if not isinstance(other, ActivityEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Entities are hashed by their ID"""
        return hash(self.id)


class ProgressEntity:
    """
    Progress entity representing user progress toward event goal.

    Business Rules:
    1. Progress cannot exceed 100% (distance_completed <= target_distance)
    2. Highest distance wins (conflict resolution between sources)
    3. Each source tracks its own distance
    4. Auto-complete when target reached
    5. Track source metadata
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        registration_id: int,
        event_id: int,
        activity_id: int,
        target_distance: Distance,
        distance_completed: Distance,
        completed_at: datetime | None = None,
        last_sync_at: datetime | None = None,
        sync_source: SyncSource | None = None,
        highest_distance_source: str | None = None,
        highest_distance_set_at: datetime | None = None,
        distance_by_source: dict[str, dict[str, Any]] | None = None,
        proof_image_url: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.registration_id = registration_id
        self.event_id = event_id
        self.activity_id = activity_id
        self.target_distance = target_distance
        self.distance_completed = distance_completed
        self.completed_at = completed_at
        self.last_sync_at = last_sync_at
        self.sync_source = sync_source
        self.highest_distance_source = highest_distance_source
        self.highest_distance_set_at = highest_distance_set_at
        self.distance_by_source = distance_by_source or {}
        self.proof_image_url = proof_image_url
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

        # Validate business rules
        self._validate()

    def _validate(self):
        """Validate business rules"""
        # Target distance must be positive
        if self.target_distance.kilometers <= 0:
            raise ValueError("Target distance must be positive")

    @property
    def progress_percentage(self) -> ProgressPercentage:
        """Calculate progress percentage"""
        return ProgressPercentage.calculate(self.distance_completed, self.target_distance)

    @property
    def is_completed(self) -> bool:
        """Check if goal is completed"""
        return self.distance_completed >= self.target_distance

    @property
    def remaining_distance(self) -> Distance:
        """Calculate remaining distance to goal"""
        if self.is_completed:
            return Distance.zero()
        return self.target_distance - self.distance_completed

    def update_distance_from_source(
        self,
        source: SyncSource,
        distance: Distance,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Update distance from a specific source using highest-wins logic.

        Business Rules:
        1. Each source maintains its own distance
        2. Highest distance becomes active
        3. Store metadata per source
        4. Track when highest distance was set

        Args:
            source: Source identifier
            distance: Distance from this source
            metadata: Optional metadata (activity_count, duration, etc.)

        Returns:
            Dict with update result and details
        """
        source_key = source.value if isinstance(source, SyncSource) else source

        # Initialize source data if not exists
        if source_key not in self.distance_by_source:
            self.distance_by_source[source_key] = {}

        # Store distance and metadata for this source
        source_data = {
            'distance_km': float(distance.kilometers),
            'last_updated': datetime.utcnow().isoformat(),
        }

        if metadata:
            source_data.update(metadata)

        self.distance_by_source[source_key] = source_data

        # Find highest distance across all sources
        highest_distance = Distance.zero()
        highest_source = None

        for src, data in self.distance_by_source.items():
            src_distance = Distance(Decimal(str(data.get('distance_km', 0))))
            if src_distance > highest_distance:
                highest_distance = src_distance
                highest_source = src

        # Update if this is new highest
        was_updated = False
        if highest_source and (
            not self.highest_distance_source or
            highest_distance > self.distance_completed
        ):
            self.distance_completed = highest_distance
            self.highest_distance_source = highest_source
            self.highest_distance_set_at = datetime.utcnow()
            was_updated = True

            # Auto-complete if target reached
            if self.is_completed and not self.completed_at:
                self.completed_at = datetime.utcnow()

        # Update sync tracking
        self.last_sync_at = datetime.utcnow()
        self.sync_source = source
        self.updated_at = datetime.utcnow()

        return {
            'was_updated': was_updated,
            'source': source_key,
            'source_distance': float(distance.kilometers),
            'active_distance': float(self.distance_completed.kilometers),
            'highest_source': self.highest_distance_source,
            'is_completed': self.is_completed,
            'progress_percentage': float(self.progress_percentage.value),
        }

    def add_manual_distance(self, distance: Distance) -> dict[str, Any]:
        """
        Add distance manually (simple addition, not highest-wins).

        Business Rule: Manual entries are cumulative

        Args:
            distance: Distance to add

        Returns:
            Dict with update result
        """
        old_distance = self.distance_completed
        self.distance_completed = self.distance_completed + distance

        # Auto-complete if target reached
        if self.is_completed and not self.completed_at:
            self.completed_at = datetime.utcnow()

        self.updated_at = datetime.utcnow()

        return {
            'old_distance': float(old_distance.kilometers),
            'added_distance': float(distance.kilometers),
            'new_distance': float(self.distance_completed.kilometers),
            'is_completed': self.is_completed,
            'progress_percentage': float(self.progress_percentage.value),
        }

    def set_proof_image(self, image_url: str):
        """
        Set proof image URL.

        Business Rule: Only one proof image per progress
        """
        self.proof_image_url = image_url
        self.updated_at = datetime.utcnow()

    def remove_proof_image(self):
        """Remove proof image"""
        self.proof_image_url = None
        self.updated_at = datetime.utcnow()

    def reset_progress(self):
        """
        Reset progress to zero.

        Business Rule: Clears all distances and completion
        """
        self.distance_completed = Distance.zero()
        self.completed_at = None
        self.highest_distance_source = None
        self.highest_distance_set_at = None
        self.distance_by_source = {}
        self.updated_at = datetime.utcnow()

    def get_source_distance(self, source: SyncSource) -> Distance | None:
        """Get distance for a specific source"""
        source_key = source.value if isinstance(source, SyncSource) else source
        source_data = self.distance_by_source.get(source_key)

        if source_data and 'distance_km' in source_data:
            return Distance(Decimal(str(source_data['distance_km'])))

        return None

    def get_source_metadata(self, source: SyncSource) -> dict[str, Any] | None:
        """Get metadata for a specific source"""
        source_key = source.value if isinstance(source, SyncSource) else source
        return self.distance_by_source.get(source_key)

    def get_activity_count(self) -> int:
        """Get activity count from highest distance source"""
        if not self.highest_distance_source:
            return 0

        source_data = self.distance_by_source.get(self.highest_distance_source, {})
        return source_data.get('activity_count', 0)

    def get_total_duration(self) -> Duration:
        """Get total duration from highest distance source"""
        if not self.highest_distance_source:
            return Duration.zero()

        source_data = self.distance_by_source.get(self.highest_distance_source, {})
        minutes = source_data.get('total_duration_minutes', 0)
        return Duration(minutes)

    def __repr__(self) -> str:
        return (
            f"<ProgressEntity(id={self.id}, user_id={self.user_id}, "
            f"progress={self.distance_completed}/{self.target_distance}, "
            f"{self.progress_percentage})>"
        )

    def __eq__(self, other) -> bool:
        """Entities are equal if they have the same ID"""
        if not isinstance(other, ProgressEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Entities are hashed by their ID"""
        return hash(self.id)
