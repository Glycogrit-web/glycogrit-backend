"""
Fitbit Connection Model
Stores OAuth tokens and user data for Fitbit integration
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FitbitConnection(Base):
    """
    Stores Fitbit OAuth connection details for users
    """
    __tablename__ = "fitbit_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    fitbit_user_id = Column(String(255), unique=True, nullable=False, index=True)

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(String(500))

    # User data
    user_data = Column(Text)  # JSON string with user profile

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="fitbit_connection")
