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


class ManualShipmentDetails(BaseModel):
    """Manual shipping details for admin"""

    tracking_number: str = Field(..., min_length=1, max_length=100)
    courier_partner: str = Field(..., min_length=1, max_length=100)
    shipped_at: datetime | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "tracking_number": "AWB1234567890",
                "courier_partner": "Delhivery",
                "shipped_at": "2026-06-08T10:00:00",
            }
        }


class ShippingPreviewResponse(BaseModel):
    """Preview of shipping details before creating order"""

    reward_name: str
    reward_type: str

    # Package details
    length_cm: float
    breadth_cm: float
    height_cm: float
    weight_kg: float

    # Shipping address
    shipping_name: str
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_pincode: str
    shipping_phone: str

    # Pickup location
    pickup_location: str
    pickup_address: str

    # Estimated costs (from available couriers)
    available_couriers: list[dict] | None = None
    estimated_delivery_days: str | None = None
    is_serviceable: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "reward_name": "Finisher Medal - Marathon 2026",
                "reward_type": "medal",
                "length_cm": 15.0,
                "breadth_cm": 10.0,
                "height_cm": 5.0,
                "weight_kg": 0.5,
                "shipping_name": "John Doe",
                "shipping_address": "123 Main Street, Apt 4B",
                "shipping_city": "Mumbai",
                "shipping_state": "Maharashtra",
                "shipping_pincode": "400001",
                "shipping_phone": "+91-9876543210",
                "pickup_location": "Home",
                "pickup_address": "Gahlot House, Ground Floor, Gyan Sarover Colony, Tiraya, Rajasthan 324008",
                "available_couriers": [
                    {"name": "Delhivery Surface", "rate": 45.50, "etd": "3-5 days"},
                    {"name": "Blue Dart", "rate": 85.00, "etd": "2-3 days"}
                ],
                "estimated_delivery_days": "3-5 days",
                "is_serviceable": True
            }
        }


class ShiprocketShipmentResponse(BaseModel):
    """Response from Shiprocket shipment creation"""

    success: bool
    tracking_number: str | None = None
    courier_partner: str | None = None
    awb: str | None = None
    label_url: str | None = None
    shiprocket_order_id: int
    shiprocket_shipment_id: int
    pickup_scheduled_date: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tracking_number": "AWB1234567890",
                "courier_partner": "Delhivery Surface",
                "awb": "AWB1234567890",
                "label_url": "https://shiprocket.co/label/12345.pdf",
                "shiprocket_order_id": 12345,
                "shiprocket_shipment_id": 67890,
                "pickup_scheduled_date": "2026-06-09",
            }
        }


class RewardWithDetails(BaseModel):
    """Reward with full details for admin dashboard"""

    # Reward fields
    id: UUID
    reward_id: str
    reward_name: str
    reward_type: str
    status: str

    # User details
    user_id: int
    user_name: str
    user_email: str
    user_phone: str | None = None

    # Event details
    event_id: int
    event_name: str

    # Registration details
    registration_id: int
    registration_number: str
    tier_name: str | None = None

    # Shipping details
    shipping_address: dict | None = None  # JSON field from user_rewards
    tracking_number: str | None = None
    courier_partner: str | None = None
    shiprocket_order_id: str | None = None
    shiprocket_shipment_id: str | None = None

    # Timestamps
    created_at: datetime
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    estimated_delivery: datetime | None = None

    # Progress (for context)
    total_distance_km: float | None = None
    goal_distance_km: float | None = None
    progress_percentage: int | None = None
    proof_image_url: str | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "ec96e086-ed7d-4da9-8a3f-79ea56038eda",
                "reward_id": "medal-123",
                "reward_name": "Bronze Medal",
                "reward_type": "medal",
                "status": "pending_shipment",
                "user_id": 456,
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "user_phone": "+919876543210",
                "event_id": 789,
                "event_name": "Marathon 2026",
                "registration_id": 123,
                "registration_number": "REG-001",
                "tier_name": "Bronze",
                "shipping_address": {
                    "name": "John Doe",
                    "address_line1": "123 Main St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "+919876543210",
                },
                "tracking_number": None,
                "courier_partner": None,
                "shiprocket_order_id": None,
                "shiprocket_shipment_id": None,
                "created_at": "2026-06-08T10:00:00",
                "shipped_at": None,
                "delivered_at": None,
                "estimated_delivery": None,
                "total_distance_km": 42.0,
                "goal_distance_km": 42.195,
                "progress_percentage": 100,
                "proof_image_url": "https://example.com/proof.jpg",
            }
        }


class TrackingVisibilityRequest(BaseModel):
    """Request to toggle tracking visibility for user"""

    visible: bool = Field(..., description="True to show tracking to user, False to hide")

    class Config:
        json_schema_extra = {
            "example": {
                "visible": True
            }
        }


class BulkShipmentUpdateResponse(BaseModel):
    """Response from bulk shipment tracking import"""

    total_rows: int = Field(..., description="Total rows processed from Excel")
    successful_updates: int = Field(..., description="Number of rewards successfully updated")
    failed_updates: int = Field(..., description="Number of rewards that failed to update")
    errors: list[str] = Field(default_factory=list, description="List of error messages")

    class Config:
        json_schema_extra = {
            "example": {
                "total_rows": 50,
                "successful_updates": 48,
                "failed_updates": 2,
                "errors": [
                    "Row 5: Reward ID RNR-EVT-123-USR-456-RWD-789 not found",
                    "Row 12: Missing AWB code"
                ]
            }
        }
