"""
Activity Progress Model - Tracks user progress for event activities
"""

from sqlalchemy import Boolean, TIMESTAMP, Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ActivityProgress(Base):
    """
    Tracks individual user progress for a specific event activity.
    Each registration can have ONE activity progress record.
    """

    __tablename__ = "activity_progress"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registration_id = Column(
        Integer, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id = Column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id = Column(
        Integer, ForeignKey("event_activities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Progress Tracking
    distance_completed = Column(Numeric(10, 2), nullable=False, default=0.00)  # In kilometers
    target_distance = Column(Numeric(10, 2), nullable=False)  # Target distance for this activity
    completed_at = Column(TIMESTAMP, nullable=True)

    # Manual Entry Support (for now, before Strava integration)
    last_manual_entry = Column(Numeric(10, 2), nullable=True)  # Last manual distance entry
    last_manual_entry_at = Column(TIMESTAMP, nullable=True)

    # 3rd Party Sync (Strava, Garmin, etc. - for future)
    last_sync_at = Column(TIMESTAMP, nullable=True)
    sync_source = Column(String(50), nullable=True)  # 'manual', 'strava', 'garmin', etc.

    # Highest-Wins Tracking
    highest_distance_source = Column(
        String(50), nullable=True
    )  # Source that set the highest distance
    highest_distance_set_at = Column(TIMESTAMP, nullable=True)  # When the highest distance was set
    distance_by_source = Column(
        JSONB, nullable=False, default={}
    )  # JSON tracking distance from each source

    # Proof & Stats (migrated from user_challenge_progress)
    proof_image_url = Column(String(500), nullable=True)  # Cloudflare R2 URL for proof image
    proof_image_viewed_by_admin = Column(Boolean, default=False, nullable=False)  # Admin verification flag
    # NOTE: total_activities and total_duration_minutes columns removed
    # Use get_total_activities() and get_total_duration_minutes() methods instead

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="activity_progress")
    registration = relationship("Registration", back_populates="activity_progress")
    event = relationship("Event")
    activity = relationship("EventActivity", back_populates="activity_progress")

    # Constraints
    __table_args__ = (
        UniqueConstraint("registration_id", name="uq_activity_progress_registration"),
    )

    @hybrid_property
    def progress_percentage(self):
        """Calculate progress percentage dynamically (can exceed 100%)"""
        if not self.target_distance or self.target_distance == 0:
            return 0.0
        percentage = (float(self.distance_completed) / float(self.target_distance)) * 100
        return percentage

    @progress_percentage.expression
    def progress_percentage(cls):
        """SQL expression for progress percentage"""
        from sqlalchemy import Float, case, cast

        return case(
            (cls.target_distance == 0, 0.0),
            else_=(cast(cls.distance_completed, Float) / cast(cls.target_distance, Float)) * 100,
        )

    @hybrid_property
    def is_completed(self):
        """Determine if activity is completed based on distance"""
        return float(self.distance_completed) >= float(self.target_distance)

    @is_completed.expression
    def is_completed(cls):
        """SQL expression for is_completed"""
        return cls.distance_completed >= cls.target_distance

    @property
    def progress_display(self):
        """Return formatted progress display"""
        return f"{float(self.distance_completed):.2f} / {float(self.target_distance):.2f} km ({self.progress_percentage:.1f}%)"

    @property
    def remaining_distance(self):
        """Calculate remaining distance"""
        return max(float(self.target_distance) - float(self.distance_completed), 0.0)

    def update_progress(self, distance_to_add: float):
        """Update progress with new distance"""
        from decimal import Decimal

        self.distance_completed += Decimal(str(distance_to_add))

        # Auto-set completed_at when target is reached
        if self.is_completed and not self.completed_at:
            from datetime import datetime

            self.completed_at = datetime.utcnow()

    def update_progress_highest_wins(
        self, new_distance_km: float, source: str, metadata: dict = None
    ):
        """
        Update progress using highest-value-wins logic.
        This method delegates to ProgressValidationService.

        Args:
            new_distance_km: New distance in kilometers
            source: Source identifier (e.g., 'strava', 'admin_manual')
            metadata: Optional metadata to store with this source

        Returns:
            dict: Result dictionary with update status and details
        """
        from app.modules.activities.services.progress_validation_service import ProgressValidationService

        return ProgressValidationService.validate_and_update_progress(
            progress=self, new_distance_km=new_distance_km, source=source, metadata=metadata
        )

    def get_total_activities(self) -> int:
        """
        Get activity count from the highest distance source.

        Returns:
            Activity count from the winning source, or 0 if none
        """
        if not self.distance_by_source or not self.highest_distance_source:
            return 0

        source_data = self.distance_by_source.get(self.highest_distance_source, {})
        return source_data.get("activity_count", 0)

    def get_total_duration_minutes(self) -> int:
        """
        Get duration from the highest distance source.

        Returns:
            Duration in minutes from the winning source, or 0 if none
        """
        if not self.distance_by_source or not self.highest_distance_source:
            return 0

        source_data = self.distance_by_source.get(self.highest_distance_source, {})
        return source_data.get("total_duration_minutes", 0)
