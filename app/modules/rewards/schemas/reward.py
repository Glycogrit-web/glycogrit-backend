"""
Reward Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ShippingAddressCreate(BaseModel):
    """Shipping address for physical rewards"""
    name: str = Field(..., min_length=1, max_length=255)
    address_line1: str = Field(..., min_length=1, max_length=500)
    address_line2: Optional[str] = Field(None, max_length=500)
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
                "phone": "+91-9876543210"
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
                    "phone": "+91-9876543210"
                }
            }
        }


class RewardResponse(BaseModel):
    """Reward response"""
    id: int
    user_id: int
    registration_id: int
    event_id: int
    reward_type: str = Field(..., description="physical_reward, e_certificate, badge")
    reward_name: str
    delivery_status: str = Field(..., description="pending, processing, shipped, delivered, failed")
    tracking_number: Optional[str] = None
    shiprocket_order_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 456,
                "user_id": 789,
                "registration_id": 123,
                "event_id": 10,
                "reward_type": "physical_reward",
                "reward_name": "Finisher Medal - Marathon 2026",
                "delivery_status": "pending",
                "tracking_number": None,
                "shiprocket_order_id": None,
                "created_at": "2026-05-21T10:00:00",
                "updated_at": None
            }
        }


class RewardStatusUpdate(BaseModel):
    """Update reward delivery status"""
    status: str = Field(..., description="pending, processing, shipped, delivered, failed, cancelled")
    tracking_number: Optional[str] = Field(None, max_length=100)
    shiprocket_order_id: Optional[str] = Field(None, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "shipped",
                "tracking_number": "AWB1234567890",
                "shiprocket_order_id": "SR123456"
            }
        }
