"""
Activity Progress Model - Tracks user progress for event activities
"""
from sqlalchemy import Column, Integer, Numeric, Boolean, TIMESTAMP, String, ForeignKey, UniqueConstraint
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
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey('event_activities.id', ondelete='CASCADE'), nullable=False, index=True)

    # Progress Tracking
    distance_completed = Column(Numeric(10, 2), nullable=False, default=0.00)  # In kilometers
    target_distance = Column(Numeric(10, 2), nullable=False)  # Target distance for this activity
    progress_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)  # Calculated percentage
    is_completed = Column(Boolean, nullable=False, default=False)
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

    @property
    def progress_display(self):
        """Return formatted progress display"""
        return f"{float(self.distance_completed):.2f} / {float(self.target_distance):.2f} km ({float(self.progress_percentage):.1f}%)"

    @property
    def remaining_distance(self):
        """Calculate remaining distance"""
        return max(float(self.target_distance) - float(self.distance_completed), 0.0)

    def update_progress(self, distance_to_add: float):
        """Update progress with new distance"""
        self.distance_completed += distance_to_add
        self.progress_percentage = min((self.distance_completed / self.target_distance) * 100, 100.0)

        if self.progress_percentage >= 100.0 and not self.is_completed:
            self.is_completed = True
            self.completed_at = func.now()
