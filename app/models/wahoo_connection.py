"""
Wahoo Fitness Connection Model
Stores OAuth connection details for Wahoo Fitness integration
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class WahooConnection(Base):
    """
    Wahoo Fitness OAuth connection
    Stores access tokens and user information for Wahoo API integration
    """
    __tablename__ = "wahoo_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Wahoo OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    token_type = Column(String(50), default="Bearer", nullable=False)
    scope = Column(Text, nullable=True)

    # Wahoo user info
    wahoo_user_id = Column(String(255), unique=True, nullable=False, index=True)
    user_data = Column(Text, nullable=True)  # JSON string for Wahoo user profile

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="wahoo_connection")

    def __repr__(self):
        return f"<WahooConnection(id={self.id}, user_id={self.user_id}, wahoo_user_id={self.wahoo_user_id})>"
