"""
Shiprocket Configuration Model
Stores Shiprocket API credentials and settings
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class ShiprocketConfig(Base):
    """
    Stores Shiprocket API credentials and configuration settings.
    Single-row table for system-wide Shiprocket integration.
    """
    __tablename__ = "shiprocket_config"

    id = Column(Integer, primary_key=True, index=True)

    # Credentials (encrypted in production)
    email = Column(String(255), nullable=False)
    # Password should be encrypted using Fernet or similar in production
    encrypted_password = Column(Text, nullable=False)

    # Token management
    access_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Shiprocket settings
    default_pickup_location = Column(String(200), nullable=False, default="Primary")
    default_length = Column(Numeric(10, 2), nullable=False, default=15.0)  # cm
    default_breadth = Column(Numeric(10, 2), nullable=False, default=15.0)  # cm
    default_height = Column(Numeric(10, 2), nullable=False, default=10.0)  # cm
    default_weight = Column(Numeric(10, 2), nullable=False, default=0.5)  # kg

    # Feature flags
    is_active = Column(Boolean, nullable=False, default=True)
    auto_schedule_pickup = Column(Boolean, nullable=False, default=True)
    auto_generate_label = Column(Boolean, nullable=False, default=True)

    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ShiprocketConfig(id={self.id}, email='{self.email}', is_active={self.is_active})>"

    def to_dict(self):
        """Convert to dictionary for API responses (excluding sensitive data)"""
        return {
            "id": self.id,
            "email": self.email,
            "default_pickup_location": self.default_pickup_location,
            "default_length": float(self.default_length) if self.default_length else None,
            "default_breadth": float(self.default_breadth) if self.default_breadth else None,
            "default_height": float(self.default_height) if self.default_height else None,
            "default_weight": float(self.default_weight) if self.default_weight else None,
            "is_active": self.is_active,
            "auto_schedule_pickup": self.auto_schedule_pickup,
            "auto_generate_label": self.auto_generate_label,
            "webhook_url": self.webhook_url,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
