"""
Activity Progress Model - Tracks user progress for event activities
"""
from sqlalchemy import Column, Integer, Numeric, Boolean, TIMESTAMP, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
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
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey('event_activities.id', ondelete='CASCADE'), nullable=False, index=True)

    # Progress Tracking
    distance_completed = Column(Numeric(10, 2), nullable=False, default=0.00)  # In kilometers
    target_distance = Column(Numeric(10, 2), nullable=False)  # Target distance for this activity
    # TEMPORARY: Keep columns for backward compatibility until migration runs
    # These will be dropped by migration 0d45922d16b5
    _progress_percentage = Column('progress_percentage', Numeric(5, 2), nullable=True, default=0.00)
    _is_completed = Column('is_completed', Boolean, nullable=True, default=False)
    completed_at = Column(TIMESTAMP, nullable=True)

    # Manual Entry Support (for now, before Strava integration)
    last_manual_entry = Column(Numeric(10, 2), nullable=True)  # Last manual distance entry
    last_manual_entry_at = Column(TIMESTAMP, nullable=True)

    # 3rd Party Sync (Strava, Garmin, etc. - for future)
    last_sync_at = Column(TIMESTAMP, nullable=True)
    sync_source = Column(String(50), nullable=True)  # 'manual', 'strava', 'garmin', etc.

    # Proof & Stats (migrated from user_challenge_progress)
    proof_image_url = Column(String(500), nullable=True)  # Cloudflare R2 URL for proof image
    total_activities = Column(Integer, nullable=False, default=0)  # Count from user_activity_logs
    total_duration_minutes = Column(Integer, nullable=False, default=0)  # Sum from user_activity_logs

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
        UniqueConstraint('registration_id', name='uq_activity_progress_registration'),
    )

    @hybrid_property
    def progress_percentage(self):
        """Calculate progress percentage dynamically"""
        if not self.target_distance or self.target_distance == 0:
            return 0.0
        percentage = (float(self.distance_completed) / float(self.target_distance)) * 100
        return min(percentage, 100.0)

    @hybrid_property
    def is_completed(self):
        """Determine if activity is completed based on distance"""
        return float(self.distance_completed) >= float(self.target_distance)

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
