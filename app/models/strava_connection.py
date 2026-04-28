"""
Strava Connection Model
Stores OAuth tokens and athlete data for Strava integration
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class StravaConnection(Base):
    """
    Stores Strava OAuth connection details for users
    """
    __tablename__ = "strava_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    athlete_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(String(500))

    # Athlete data
    athlete_data = Column(Text)  # JSON string with athlete profile

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="strava_connection")
    activities = relationship("ChallengeActivity", back_populates="strava_connection", cascade="all, delete-orphan")


class ChallengeActivity(Base):
    """
    Stores individual activities from Strava for challenge tracking
    """
    __tablename__ = "challenge_activities"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strava_connection_id = Column(Integer, ForeignKey("strava_connections.id"))

    # Activity source tracking
    source_provider = Column(String(50), nullable=True)  # strava, google_fit, apple_health, nike_run_club
    external_activity_id = Column(String(255), nullable=True)  # Provider-specific activity ID

    # Strava activity details (deprecated in favor of external_activity_id)
    strava_activity_id = Column(BigInteger, unique=True, index=True)
    activity_type = Column(String(50), nullable=False)  # Run, Ride, Walk, etc.
    activity_name = Column(String(500))

    # Metrics
    distance_meters = Column(Integer)  # Distance in meters
    duration_seconds = Column(Integer)  # Moving time in seconds
    elevation_gain_meters = Column(Integer)
    average_speed = Column(Integer)  # m/s
    max_speed = Column(Integer)  # m/s

    # Activity timestamp
    activity_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Verification
    is_verified = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    challenge = relationship("Event")
    strava_connection = relationship("StravaConnection", back_populates="activities")


class UserChallengeProgress(Base):
    """
    Aggregated progress for users in challenges
    """
    __tablename__ = "user_challenge_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    # Progress metrics
    total_distance_km = Column(Integer, default=0)  # Distance in kilometers
    total_activities = Column(Integer, default=0)
    total_duration_minutes = Column(Integer, default=0)

    # Goal tracking
    goal_distance_km = Column(Integer)
    progress_percentage = Column(Integer, default=0)

    # Completion tracking
    completion_status = Column(String(50), nullable=True)  # failed, completed, exceeded, outstanding
    completion_percentage = Column(Integer, default=0)
    evaluation_date = Column(DateTime(timezone=True), nullable=True)
    badge_earned = Column(String(100), nullable=True)

    # Activity tracking
    last_activity_date = Column(DateTime(timezone=True))
    current_streak_days = Column(Integer, default=0)

    # Sync tracking - tracks metadata about last sync
    last_sync_source = Column(String(50), nullable=True)  # strava, apple_health, google_fit, admin_manual
    last_sync_at = Column(DateTime(timezone=True), nullable=True)  # When was the last sync
    last_synced_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # If admin synced manually

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    challenge = relationship("Event")
