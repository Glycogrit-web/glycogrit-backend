"""
Fitness Tracker Connection Models
Supports multiple fitness tracking platforms: Strava, Google Fit, Apple Health, Nike Run Club

Provider values should use FitnessTrackerProvider enum from app.core.enums
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import FitnessTrackerProvider


class FitnessTrackerConnection(Base):
    """
    Generic fitness tracker connection for non-Strava providers
    Supports: Google Fit, Apple Health, Nike Run Club, etc.
    """
    __tablename__ = "fitness_tracker_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Provider info
    # Use FitnessTrackerProvider enum values: strava, google_fit, apple_health, nike_run_club, garmin, wahoo, fitbit
    provider = Column(String(50), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=True)

    # OAuth tokens (for OAuth-based providers)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String(500), nullable=True)

    # Provider-specific data (JSON string)
    provider_data = Column(Text, nullable=True)

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="fitness_trackers")

    # Unique constraint on user_id + provider
    __table_args__ = (
        Index('idx_fitness_tracker_user_provider', 'user_id', 'provider', unique=True),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<FitnessTrackerConnection(id={self.id}, user_id={self.user_id}, provider='{self.provider}')>"
