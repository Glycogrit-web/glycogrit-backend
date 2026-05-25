"""
Strava Connection Model
Stores OAuth tokens and athlete data for Strava integration
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
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


# REMOVED: UserChallengeProgress class
# The user_challenge_progress table has been removed in favor of activity_progress
# See ActivityProgress model in app/models/activity_progress.py for the replacement
