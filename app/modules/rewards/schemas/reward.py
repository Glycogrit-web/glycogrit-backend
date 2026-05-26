"""
Reward Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ShippingAddressCreate(BaseModel):
    """Shipping address for physical rewards"""

    name: str = Field(..., min_length=1, max_length=255)
    address_line1: str = Field(..., min_length=1, max_length=500)
    address_line2: str | None = Field(None, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")
    phone: str = Field(..., min_length=10, max_length=15, pattern="^[0-9+\\-\\s()]+$")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "address_line1": "123 Main Street",
                "address_line2": "Apt 4B",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "phone": "+91-9876543210",
            }
        }


class RewardOrderCreate(BaseModel):
    """Create reward order request"""

    registration_id: int = Field(..., description="Registration ID for which reward is claimed")
    reward_name: str = Field(..., min_length=1, max_length=255, description="Name of the reward")
    shipping_address: ShippingAddressCreate

    class Config:
        json_schema_extra = {
            "example": {
                "registration_id": 123,
                "reward_name": "Finisher Medal - Marathon 2026",
                "shipping_address": {
                    "name": "John Doe",
                    "address_line1": "123 Main Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "+91-9876543210",
                },
            }
        }


class RewardResponse(BaseModel):
    """Reward response"""

    id: UUID
    user_id: int
    registration_id: int | None = None
    event_id: int
    reward_type: str = Field(..., description="medal, tshirt, certificate, trophy, custom")
    reward_name: str
    status: str = Field(
        ..., description="pending_details, pending_shipment, shipped, delivered, cancelled"
    )
    tracking_number: str | None = None
    shiprocket_order_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "d2793282-8b1a-4f2e-9c3d-1234567890ab",
                "user_id": 789,
                "registration_id": 123,
                "event_id": 10,
                "reward_type": "medal",
                "reward_name": "Finisher Medal - Marathon 2026",
                "status": "pending_details",
                "tracking_number": None,
                "shiprocket_order_id": None,
                "created_at": "2026-05-21T10:00:00",
                "updated_at": None,
            }
        }


class RewardStatusUpdate(BaseModel):
    """Update reward delivery status"""

    status: str = Field(
        ..., description="pending, processing, shipped, delivered, failed, cancelled"
    )
    tracking_number: str | None = Field(None, max_length=100)
    shiprocket_order_id: str | None = Field(None, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "shipped",
                "tracking_number": "AWB1234567890",
                "shiprocket_order_id": "SR123456",
            }
        }
