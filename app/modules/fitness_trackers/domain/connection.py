"""
Unified Fitness Tracker Connection Model

Single table for all provider connections using polymorphic pattern.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProviderType(str, enum.Enum):
    """Fitness tracker provider types"""
    STRAVA = "strava"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    WAHOO = "wahoo"
    GOOGLE_FIT = "google_fit"
    POLAR = "polar"


class FitnessConnection(Base):
    """
    Unified model for all fitness tracker OAuth connections.

    Replaces separate tables:
    - strava_connections
    - garmin_connections
    - fitbit_connections
    - wahoo_connections

    Uses polymorphic pattern with provider_type discriminator.
    """
    __tablename__ = "fitness_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(SQLEnum(ProviderType), nullable=False, index=True)

    # Unique constraint: one connection per user per provider
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    # Provider-specific athlete/user ID
    athlete_id = Column(String(255), nullable=False, index=True)

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)  # Optional for some providers
    expires_at = Column(DateTime(timezone=True))  # Optional for some providers
    scope = Column(String(500))

    # Provider-specific data (JSON)
    athlete_data = Column(Text)  # Store as JSON string
    provider_metadata = Column(Text)  # Additional provider-specific metadata

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True))
    sync_enabled = Column(Boolean, default=True, nullable=False)

    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0, nullable=False)

    # Webhook subscription (if applicable)
    webhook_subscription_id = Column(String(255))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="fitness_connections")

    def __repr__(self):
        return f"<FitnessConnection(id={self.id}, provider={self.provider.value}, user_id={self.user_id})>"
