"""
Goodie Schemas
Pydantic schemas for goodie-related API requests and responses
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class GoodieType(str, Enum):
    """Type of goodie"""
    MEDAL = "medal"
    TSHIRT = "tshirt"
    CERTIFICATE = "certificate"
    TROPHY = "trophy"
    CUSTOM = "custom"


class GoodieStatus(str, Enum):
    """Status of goodie fulfillment"""
    PENDING_DETAILS = "pending_details"
    PENDING_SHIPMENT = "pending_shipment"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class EligibilityCriteria(BaseModel):
    """Eligibility criteria for earning a goodie"""
    min_completion_percentage: int = Field(ge=0, le=200, description="Minimum completion percentage required")
    required_badges: List[str] = Field(description="List of acceptable badge names")

    class Config:
        schema_extra = {
            "example": {
                "min_completion_percentage": 100,
                "required_badges": ["Challenge Completed", "Goal Crusher", "Outstanding Performer"]
            }
        }


class GoodieDefinition(BaseModel):
    """Goodie definition (stored in Event.goodies JSONB)"""
    id: str = Field(description="Unique identifier for this goodie")
    name: str = Field(min_length=1, max_length=200, description="Name of the goodie")
    description: Optional[str] = Field(None, description="Description of the goodie")
    image_url: Optional[str] = Field(None, description="URL to goodie image")
    type: GoodieType = Field(description="Type of goodie")
    requires_shipping: bool = Field(default=True, description="Whether this goodie requires physical shipping")
    eligibility_criteria: EligibilityCriteria = Field(description="Criteria to earn this goodie")

    class Config:
        schema_extra = {
            "example": {
                "id": "goodie_finisher_medal",
                "name": "Finisher Medal",
                "description": "Gold-plated finisher medal with event logo",
                "image_url": "https://example.com/images/medal.png",
                "type": "medal",
                "requires_shipping": True,
                "eligibility_criteria": {
                    "min_completion_percentage": 100,
                    "required_badges": ["Challenge Completed", "Goal Crusher", "Outstanding Performer"]
                }
            }
        }


class TShirtSize(str, Enum):
    """T-shirt sizes"""
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    XXXL = "XXXL"


class ShippingDetails(BaseModel):
    """Shipping address details"""
    full_name: str = Field(min_length=1, max_length=200, description="Full name for shipping")
    address_line1: str = Field(min_length=1, max_length=500, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=500, description="Address line 2")
    city: str = Field(min_length=1, max_length=100, description="City")
    state: str = Field(min_length=1, max_length=100, description="State/Province")
    postal_code: str = Field(min_length=1, max_length=20, description="Postal/ZIP code")
    country: str = Field(min_length=1, max_length=100, description="Country")
    phone: str = Field(min_length=10, max_length=20, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email for shipping notifications")
    tshirt_size: Optional[TShirtSize] = Field(None, description="T-shirt size (if applicable)")
    special_instructions: Optional[str] = Field(None, max_length=500, description="Special delivery instructions")

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        import re
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?[\d]{10,15}$', cleaned):
            raise ValueError('Invalid phone number format')
        return v

    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Doe",
                "address_line1": "123 Main Street",
                "address_line2": "Apt 4B",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
                "country": "India",
                "phone": "+91-9876543210",
                "email": "john.doe@example.com",
                "tshirt_size": "L",
                "special_instructions": "Please leave at front desk"
            }
        }


class ClaimGoodieRequest(BaseModel):
    """Request to claim a goodie with shipping details"""
    shipping_details: ShippingDetails

    class Config:
        schema_extra = {
            "example": {
                "shipping_details": {
                    "full_name": "John Doe",
                    "address_line1": "123 Main Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "postal_code": "400001",
                    "country": "India",
                    "phone": "+91-9876543210"
                }
            }
        }


class UpdateShippingDetailsRequest(BaseModel):
    """Request to update shipping details"""
    shipping_details: ShippingDetails


class ShipGoodieRequest(BaseModel):
    """Admin request to mark goodie as shipped"""
    tracking_number: str = Field(min_length=1, max_length=100, description="Tracking/AWB number")
    courier_partner: str = Field(min_length=1, max_length=100, description="Courier company name")
    estimated_delivery_date: Optional[datetime] = Field(None, description="Estimated delivery date")
    shiprocket_order_id: Optional[int] = Field(None, description="Shiprocket order ID")
    shiprocket_shipment_id: Optional[int] = Field(None, description="Shiprocket shipment ID")
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Admin notes")

    class Config:
        schema_extra = {
            "example": {
                "tracking_number": "AWB123456789",
                "courier_partner": "BlueDart",
                "estimated_delivery_date": "2024-12-25T00:00:00Z",
                "admin_notes": "Shipped via express delivery"
            }
        }


class TrackingInfo(BaseModel):
    """Tracking information for a shipped goodie"""
    tracking_number: Optional[str] = None
    courier_partner: Optional[str] = None
    current_status: Optional[str] = None
    shipped_date: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    tracking_url: Optional[str] = None


class UserGoodieResponse(BaseModel):
    """Response schema for user goodie"""
    id: str
    user_id: int
    challenge_id: int
    goodie_id: str
    goodie_name: str
    goodie_description: Optional[str] = None
    goodie_type: str
    goodie_image_url: Optional[str] = None
    requires_shipping: bool
    status: GoodieStatus
    shipping_details: Optional[Dict[str, Any]] = None
    tracking_info: Optional[TrackingInfo] = None
    awarded_at: datetime
    claimed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Challenge details (joined data)
    challenge_name: Optional[str] = None
    challenge_banner_image_url: Optional[str] = None

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 123,
                "challenge_id": 456,
                "goodie_id": "goodie_finisher_medal",
                "goodie_name": "Finisher Medal",
                "goodie_description": "Gold-plated finisher medal",
                "goodie_type": "medal",
                "goodie_image_url": "https://example.com/medal.png",
                "requires_shipping": True,
                "status": "shipped",
                "shipping_details": {
                    "full_name": "John Doe",
                    "city": "Mumbai",
                    "state": "Maharashtra"
                },
                "tracking_info": {
                    "tracking_number": "AWB123456789",
                    "courier_partner": "BlueDart",
                    "current_status": "In Transit",
                    "tracking_url": "https://shiprocket.co/tracking/AWB123456789"
                },
                "awarded_at": "2024-01-15T10:00:00Z",
                "claimed_at": "2024-01-16T14:30:00Z",
                "shipped_at": "2024-01-17T09:00:00Z",
                "challenge_name": "100km Running Challenge",
                "challenge_banner_image_url": "https://example.com/challenge.png"
            }
        }


class UserGoodieListResponse(BaseModel):
    """Response schema for list of user goodies"""
    goodies: List[UserGoodieResponse]
    total: int
    pending_details_count: int
    pending_shipment_count: int
    shipped_count: int
    delivered_count: int


class ChallengeGoodiesResponse(BaseModel):
    """Response schema for goodies available for a challenge"""
    challenge_id: int
    challenge_name: str
    goodies: List[GoodieDefinition]


class AdminGoodieResponse(UserGoodieResponse):
    """Admin response with additional fields"""
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    shiprocket_order_id: Optional[int] = None
    shiprocket_shipment_id: Optional[int] = None
    admin_notes: Optional[str] = None


class AdminGoodieListResponse(BaseModel):
    """Admin response for list of goodies"""
    goodies: List[AdminGoodieResponse]
    total: int
    filters: Dict[str, int]  # Count by status


class GoodieStatsResponse(BaseModel):
    """Statistics for goodies"""
    total_goodies: int
    pending_details: int
    pending_shipment: int
    shipped: int
    delivered: int
    cancelled: int
    total_users_with_goodies: int
