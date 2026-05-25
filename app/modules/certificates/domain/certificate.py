"""
Certificate Model

Certificates are stored as UserReward records with reward_type='certificate'.
This maintains backward compatibility while enabling DDD migration.
"""

import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RewardType(str, enum.Enum):
    """Type of reward"""
    CERTIFICATE = "certificate"
    PHYSICAL_REWARD = "physical_reward"
    BADGE = "badge"


class UserReward(Base):
    """
    User rewards including certificates.

    For certificates:
    - reward_type = 'certificate'
    - certificate_url = URL to certificate file
    - certificate_number = Unique certificate identifier
    """
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey("registrations.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)

    # Reward details
    reward_type = Column(SQLEnum(RewardType), nullable=False, index=True)
    reward_name = Column(String(255))
    reward_description = Column(Text)

    # Certificate-specific fields
    certificate_url = Column(Text)  # Cloudflare R2 URL
    certificate_number = Column(String(100), unique=True, index=True)

    # Physical reward fields
    shiprocket_order_id = Column(String(100))
    tracking_number = Column(String(100))
    delivery_status = Column(String(50))

    # Download tracking
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="rewards")
    registration = relationship("Registration")
    event = relationship("Event")

    def __repr__(self):
        return f"<UserReward(id={self.id}, type={self.reward_type}, user_id={self.user_id})>"
