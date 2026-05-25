from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class GarminConnection(Base):
    __tablename__ = "garmin_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # OAuth 1.0a tokens (Garmin uses OAuth 1.0a)
    access_token = Column(String(512), nullable=False)
    access_token_secret = Column(String(512), nullable=False)

    # Garmin user information
    user_id_garmin = Column(String(255), unique=True, nullable=False, index=True)
    user_data = Column(JSONB, nullable=True)  # Store user profile data from Garmin

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to User
    user = relationship("User", back_populates="garmin_connection")

    def __repr__(self):
        return f"<GarminConnection(user_id={self.user_id}, user_id_garmin={self.user_id_garmin}, is_active={self.is_active})>"
