"""
Unified Fitness Tracker Connection Model

Single table for all provider connections using polymorphic pattern.
"""

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.modules.fitness_trackers.domain.value_objects import ProviderType


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

    __tablename__ = "fitness_tracker_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(SQLEnum(ProviderType), nullable=False)

    # Unique constraint: one connection per user per provider
    __table_args__ = (
        {
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
            "extend_existing": True,
        },
    )

    # Provider-specific athlete/user ID
    athlete_id = Column(String(255), nullable=False, index=True)

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)  # Optional for some providers
    token_expires_at = Column(DateTime(timezone=True))  # Optional for some providers
    scope = Column(String(500))

    # Provider-specific data (JSON)
    athlete_data = Column(Text)  # Store as JSON string

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
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    # Note: No back_populates because User.fitness_trackers points to FitnessTrackerConnection (old model)
    # This is a one-way relationship from FitnessConnection -> User
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<FitnessConnection(id={self.id}, provider={self.provider.value}, user_id={self.user_id})>"
