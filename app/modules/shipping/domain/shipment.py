"""
Shiprocket Order Model
Stores Shiprocket order details and tracks shipment lifecycle
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ShiprocketOrderStatus(str, enum.Enum):
    """Status of Shiprocket order processing"""
    PENDING = "pending"  # Order created in our system, not yet sent to Shiprocket
    CREATED = "created"  # Order created in Shiprocket
    LABEL_GENERATED = "label_generated"  # AWB assigned and label generated
    PICKUP_SCHEDULED = "pickup_scheduled"  # Pickup scheduled with courier
    MANIFESTED = "manifested"  # Manifest generated
    FAILED = "failed"  # Order creation failed


class ShiprocketOrder(Base):
    """
    Tracks Shiprocket orders for physical reward fulfillment.
    Maintains complete audit trail of order creation and shipping process.
    """
    __tablename__ = "shiprocket_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Our system references
    user_reward_id = Column(UUID(as_uuid=True), ForeignKey("user_rewards.id"), nullable=False, unique=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Shiprocket IDs
    shiprocket_order_id = Column(String(100), nullable=True, unique=True, index=True)
    shiprocket_shipment_id = Column(String(100), nullable=True, index=True)
    shiprocket_awb = Column(String(100), nullable=True, index=True)  # Air Waybill / Tracking Number

    # Order details
    order_reference = Column(String(200), nullable=False, unique=True, index=True)  # RNR-EVT-123-USR-456-RWD-789
    courier_id = Column(Integer, nullable=True)
    courier_name = Column(String(100), nullable=True)

    # Status
    status = Column(SQLEnum(ShiprocketOrderStatus), nullable=False, default=ShiprocketOrderStatus.PENDING, index=True)

    # URLs
    label_url = Column(String(500), nullable=True)
    manifest_url = Column(String(500), nullable=True)
    tracking_url = Column(String(500), nullable=True)

    # Pickup details
    pickup_location = Column(String(200), nullable=True)  # From Shiprocket settings
    pickup_scheduled_date = Column(Date, nullable=True)
    pickup_token_number = Column(String(100), nullable=True)

    # API request/response logs (for debugging)
    shiprocket_request = Column(JSONB, nullable=True)  # Store request payload
    shiprocket_response = Column(JSONB, nullable=True)  # Store response
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    order_sent_at = Column(DateTime(timezone=True), nullable=True)  # When sent to Shiprocket
    label_generated_at = Column(DateTime(timezone=True), nullable=True)
    pickup_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user_reward = relationship("UserReward", back_populates="shiprocket_order")
    event = relationship("Event")
    user = relationship("User")

    def __repr__(self):
        return f"<ShiprocketOrder(id={self.id}, order_reference='{self.order_reference}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_reward_id": str(self.user_reward_id),
            "event_id": self.event_id,
            "user_id": self.user_id,
            "shiprocket_order_id": self.shiprocket_order_id,
            "shiprocket_shipment_id": self.shiprocket_shipment_id,
            "shiprocket_awb": self.shiprocket_awb,
            "order_reference": self.order_reference,
            "courier_id": self.courier_id,
            "courier_name": self.courier_name,
            "status": self.status.value if self.status else None,
            "label_url": self.label_url,
            "manifest_url": self.manifest_url,
            "tracking_url": self.tracking_url,
            "pickup_location": self.pickup_location,
            "pickup_scheduled_date": self.pickup_scheduled_date.isoformat() if self.pickup_scheduled_date else None,
            "pickup_token_number": self.pickup_token_number,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "order_sent_at": self.order_sent_at.isoformat() if self.order_sent_at else None,
            "label_generated_at": self.label_generated_at.isoformat() if self.label_generated_at else None,
            "pickup_scheduled_at": self.pickup_scheduled_at.isoformat() if self.pickup_scheduled_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
