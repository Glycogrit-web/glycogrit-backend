"""
User Reward Model
Stores rewards earned by users for completing challenges
"""

import uuid as uuid_pkg

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import RewardStatus, RewardType


class UserReward(Base):
    """
    Stores rewards earned by users for completing challenges.
    Tracks the entire lifecycle from awarding to delivery with Shiprocket integration.
    """

    __tablename__ = "user_rewards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey("registrations.id"), nullable=True, index=True)

    # Reward details (copied from tier rewards at time of awarding)
    reward_id = Column(String(100), nullable=False)  # ID/name from tier rewards array
    reward_name = Column(String(200), nullable=False)
    reward_description = Column(Text)
    reward_type = Column(
        SQLEnum(RewardType, native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RewardType.CUSTOM.value,
    )
    reward_image_url = Column(Text)
    requires_shipping = Column(Boolean, nullable=False, default=True)

    # Physical item properties (for Shiprocket)
    item_weight = Column(Numeric(10, 2), nullable=True)  # kg
    item_length = Column(Numeric(10, 2), nullable=True)  # cm
    item_breadth = Column(Numeric(10, 2), nullable=True)  # cm
    item_height = Column(Numeric(10, 2), nullable=True)  # cm
    item_sku = Column(String(100), nullable=True)  # Product SKU
    item_hsn = Column(String(50), nullable=True)  # HSN code for customs

    # Status tracking
    status = Column(
        SQLEnum(RewardStatus, native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RewardStatus.PENDING_DETAILS.value,
        index=True,
    )

    # Admin unlock/verification
    is_unlocked = Column(Boolean, nullable=False, default=False, index=True)
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    tracking_visible_to_user = Column(Boolean, nullable=False, default=False, index=True)
    unlocked_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    unlocked_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Shipping details (JSON)
    # {
    #   "full_name": "John Doe",
    #   "address_line1": "123 Main St",
    #   "address_line2": "Apt 4B",
    #   "city": "Mumbai",
    #   "state": "Maharashtra",
    #   "postal_code": "400001",
    #   "country": "India",
    #   "phone": "+91-9876543210",
    #   "email": "user@example.com",
    #   "tshirt_size": "L",  # Optional, only for t-shirts
    #   "special_instructions": "Leave at front desk"  # Optional
    # }
    shipping_details = Column(JSONB, nullable=True)

    # Shiprocket integration data
    shiprocket_order_id = Column(String(100), nullable=True, index=True)
    shiprocket_shipment_id = Column(String(100), nullable=True, index=True)
    shiprocket_awb = Column(String(100), nullable=True, index=True)  # AWB tracking number
    tracking_number = Column(String(100), nullable=True, index=True)  # AWB number (alias)
    courier_partner = Column(String(100), nullable=True)
    shiprocket_status_code = Column(Integer, nullable=True)  # Shiprocket sr-status
    tracking_url = Column(String(500), nullable=True)
    current_location = Column(String(200), nullable=True)
    last_tracking_update = Column(DateTime(timezone=True), nullable=True)
    pickup_scheduled_date = Column(Date, nullable=True)
    estimated_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)

    # Status updates
    status_history = Column(JSONB, nullable=True, default=list)  # Track all status changes

    # Timestamps
    awarded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # When reward was earned
    claimed_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When user submitted shipping details
    shipped_at = Column(DateTime(timezone=True), nullable=True)  # When reward was shipped
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # When reward was delivered
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # When reward was cancelled

    # Admin notes and errors
    admin_notes = Column(Text, nullable=True)  # Internal notes for admins
    fulfillment_error = Column(
        Text, nullable=True
    )  # Store any errors during Shiprocket order creation

    # Certificate-specific fields (for RewardType.CERTIFICATE)
    certificate_url = Column(Text, nullable=True)  # URL to generated certificate PDF
    certificate_number = Column(
        String(100), unique=True, nullable=True, index=True
    )  # Unique cert identifier (e.g., GLCG-2024-0001-00123)
    download_count = Column(Integer, default=0, nullable=False)  # Track certificate downloads
    download_limit = Column(
        Integer, default=10, nullable=False
    )  # Max downloads allowed (0 = unlimited)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)  # Last download timestamp

    # Standard timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="rewards", foreign_keys=[user_id])
    event = relationship("Event", back_populates="user_rewards")
    registration = relationship("Registration", back_populates="rewards")
    unlocked_by_admin = relationship("User", foreign_keys=[unlocked_by_admin_id])
    verified_by_admin = relationship("User", foreign_keys=[verified_by_admin_id])
    shiprocket_order = relationship("ShiprocketOrder", back_populates="user_reward", uselist=False)

    def __repr__(self):
        return f"<UserReward(id={self.id}, user_id={self.user_id}, reward_name='{self.reward_name}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "challenge_id": self.event_id,  # Map event_id to challenge_id for API consistency
            "registration_id": self.registration_id,
            "reward_id": self.reward_id,
            "reward_name": self.reward_name,
            "reward_description": self.reward_description,
            "reward_type": self.reward_type.value if self.reward_type else None,
            "reward_image_url": self.reward_image_url,
            "requires_shipping": self.requires_shipping,
            "status": self.status.value if self.status else None,
            "is_unlocked": self.is_unlocked,
            "is_verified": self.is_verified,
            "tracking_visible_to_user": self.tracking_visible_to_user,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "shipping_details": self.shipping_details,
            "shiprocket_order_id": self.shiprocket_order_id,
            "shiprocket_shipment_id": self.shiprocket_shipment_id,
            "tracking_number": self.tracking_number,
            "courier_partner": self.courier_partner,
            "tracking_url": self.tracking_url,
            "current_location": self.current_location,
            "shiprocket_status_code": self.shiprocket_status_code,
            "pickup_scheduled_date": (
                self.pickup_scheduled_date.isoformat() if self.pickup_scheduled_date else None
            ),
            "estimated_delivery_date": (
                self.estimated_delivery_date.isoformat() if self.estimated_delivery_date else None
            ),
            "actual_delivery_date": (
                self.actual_delivery_date.isoformat() if self.actual_delivery_date else None
            ),
            "status_history": self.status_history,
            "awarded_at": self.awarded_at.isoformat() if self.awarded_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "fulfillment_error": self.fulfillment_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
