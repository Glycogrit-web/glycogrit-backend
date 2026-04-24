"""
User Goodie Model
Stores goodies earned by users for completing challenges
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid as uuid_pkg
from app.core.database import Base


class GoodieStatus(str, enum.Enum):
    """Status of goodie fulfillment"""
    PENDING_DETAILS = "pending_details"  # User needs to provide shipping details
    PENDING_SHIPMENT = "pending_shipment"  # Admin needs to ship
    SHIPPED = "shipped"  # In transit
    DELIVERED = "delivered"  # Successfully delivered
    CANCELLED = "cancelled"  # Cancelled or invalid


class GoodieType(str, enum.Enum):
    """Type of goodie"""
    MEDAL = "medal"
    TSHIRT = "tshirt"
    CERTIFICATE = "certificate"
    TROPHY = "trophy"
    CUSTOM = "custom"


class UserGoodie(Base):
    """
    Stores goodies earned by users for completing challenges.
    Tracks the entire lifecycle from awarding to delivery.
    """
    __tablename__ = "user_goodies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)

    # Goodie details (copied from event.goodies at time of awarding)
    goodie_id = Column(String(100), nullable=False)  # ID from event.goodies array
    goodie_name = Column(String(200), nullable=False)
    goodie_description = Column(Text)
    goodie_type = Column(SQLEnum(GoodieType), nullable=False, default=GoodieType.CUSTOM)
    goodie_image_url = Column(Text)
    requires_shipping = Column(SQLEnum('true', 'false', name='boolean_enum'), nullable=False, default='true')

    # Status tracking
    status = Column(SQLEnum(GoodieStatus), nullable=False, default=GoodieStatus.PENDING_DETAILS, index=True)

    # Admin unlock/verification
    is_unlocked = Column(SQLEnum('true', 'false', name='boolean_enum_unlocked'), nullable=False, default='false', index=True)
    is_verified = Column(SQLEnum('true', 'false', name='boolean_enum_verified'), nullable=False, default='false', index=True)
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
    shiprocket_order_id = Column(Integer, nullable=True, index=True)
    shiprocket_shipment_id = Column(Integer, nullable=True, index=True)
    tracking_number = Column(String(100), nullable=True, index=True)  # AWB number
    courier_partner = Column(String(100), nullable=True)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    awarded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When goodie was earned
    claimed_at = Column(DateTime(timezone=True), nullable=True)  # When user submitted shipping details
    shipped_at = Column(DateTime(timezone=True), nullable=True)  # When goodie was shipped
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # When goodie was delivered
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # When goodie was cancelled

    # Admin notes
    admin_notes = Column(Text, nullable=True)  # Internal notes for admins

    # Standard timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="goodies")
    challenge = relationship("Event", back_populates="user_goodies")

    def __repr__(self):
        return f"<UserGoodie(id={self.id}, user_id={self.user_id}, goodie_name='{self.goodie_name}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "challenge_id": self.challenge_id,
            "goodie_id": self.goodie_id,
            "goodie_name": self.goodie_name,
            "goodie_description": self.goodie_description,
            "goodie_type": self.goodie_type,
            "goodie_image_url": self.goodie_image_url,
            "requires_shipping": self.requires_shipping == 'true',
            "status": self.status,
            "is_unlocked": self.is_unlocked == 'true',
            "is_verified": self.is_verified == 'true',
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "shipping_details": self.shipping_details,
            "shiprocket_order_id": self.shiprocket_order_id,
            "shiprocket_shipment_id": self.shiprocket_shipment_id,
            "tracking_number": self.tracking_number,
            "courier_partner": self.courier_partner,
            "estimated_delivery_date": self.estimated_delivery_date.isoformat() if self.estimated_delivery_date else None,
            "awarded_at": self.awarded_at.isoformat() if self.awarded_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
