"""
Reward Schemas
Pydantic schemas for reward-related API requests and responses
"""

from pydantic import BaseModel, Field, EmailStr, validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RewardType(str, Enum):
    """Type of reward"""
    MEDAL = "medal"
    TSHIRT = "tshirt"
    CERTIFICATE = "certificate"
    TROPHY = "trophy"
    CUSTOM = "custom"


class RewardStatus(str, Enum):
    """Status of reward fulfillment"""
    PENDING_DETAILS = "pending_details"
    PENDING_SHIPMENT = "pending_shipment"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class EligibilityCriteria(BaseModel):
    """Eligibility criteria for earning a reward"""
    min_completion_percentage: int = Field(ge=0, le=200, description="Minimum completion percentage required")
    required_badges: List[str] = Field(description="List of acceptable badge names")

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "min_completion_percentage": 100,
                "required_badges": ["Challenge Completed", "Goal Crusher", "Outstanding Performer"]
            }
        })


class RewardDefinition(BaseModel):
    """Reward definition (stored in Event.rewards JSONB)"""
    id: str = Field(description="Unique identifier for this reward")
    name: str = Field(min_length=1, max_length=200, description="Name of the reward")
    description: Optional[str] = Field(None, description="Description of the reward")
    image_url: Optional[str] = Field(None, description="URL to reward image")
    type: RewardType = Field(description="Type of reward")
    requires_shipping: bool = Field(default=True, description="Whether this reward requires physical shipping")
    eligibility_criteria: EligibilityCriteria = Field(description="Criteria to earn this reward")

    model_config = ConfigDict(json_schema_extra={
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
        })


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

    model_config = ConfigDict(json_schema_extra={
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
        })


class ClaimRewardRequest(BaseModel):
    """Request to claim a reward with shipping details"""
    shipping_details: ShippingDetails

    model_config = ConfigDict(json_schema_extra={
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
        })


class UpdateShippingDetailsRequest(BaseModel):
    """Request to update shipping details"""
    shipping_details: ShippingDetails


class ShipRewardRequest(BaseModel):
    """Admin request to mark reward as shipped"""
    tracking_number: str = Field(min_length=1, max_length=100, description="Tracking/AWB number")
    courier_partner: str = Field(min_length=1, max_length=100, description="Courier company name")
    estimated_delivery_date: Optional[datetime] = Field(None, description="Estimated delivery date")
    shiprocket_order_id: Optional[int] = Field(None, description="Shiprocket order ID")
    shiprocket_shipment_id: Optional[int] = Field(None, description="Shiprocket shipment ID")
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Admin notes")

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "tracking_number": "AWB123456789",
                "courier_partner": "BlueDart",
                "estimated_delivery_date": "2024-12-25T00:00:00Z",
                "admin_notes": "Shipped via express delivery"
            }
        })


class TrackingInfo(BaseModel):
    """Tracking information for a shipped reward"""
    tracking_number: Optional[str] = None
    courier_partner: Optional[str] = None
    current_status: Optional[str] = None
    shipped_date: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    tracking_url: Optional[str] = None


class UserRewardResponse(BaseModel):
    """Response schema for user reward"""
    id: str
    user_id: int
    challenge_id: int
    reward_id: str
    reward_name: str
    reward_description: Optional[str] = None
    reward_type: str
    reward_image_url: Optional[str] = None
    requires_shipping: bool
    status: RewardStatus
    is_unlocked: bool = False
    is_verified: bool = False
    shipping_details: Optional[Dict[str, Any]] = None
    tracking_info: Optional[TrackingInfo] = None

    # Top-level tracking fields (for easy frontend access)
    tracking_number: Optional[str] = None
    courier_partner: Optional[str] = None
    tracking_url: Optional[str] = None

    awarded_at: datetime
    claimed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Challenge details (joined data)
    challenge_name: Optional[str] = None
    challenge_banner_image_url: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 123,
                "challenge_id": 456,
                "reward_id": "goodie_finisher_medal",
                "reward_name": "Finisher Medal",
                "reward_description": "Gold-plated finisher medal",
                "reward_type": "medal",
                "reward_image_url": "https://example.com/medal.png",
                "requires_shipping": True,
                "status": "shipped",
                "is_unlocked": True,
                "is_verified": True,
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


    )
class UserRewardListResponse(BaseModel):
    """Response schema for list of user rewards"""
    rewards: List[UserRewardResponse]
    total: int
    pending_details_count: int
    pending_shipment_count: int
    shipped_count: int
    delivered_count: int


class ChallengeRewardsResponse(BaseModel):
    """Response schema for rewards available for a challenge"""
    challenge_id: int
    challenge_name: str
    rewards: List[RewardDefinition]


class AdminRewardResponse(UserRewardResponse):
    """Admin response with additional fields"""
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    shiprocket_order_id: Optional[int] = None
    shiprocket_shipment_id: Optional[int] = None
    admin_notes: Optional[str] = None


class AdminRewardListResponse(BaseModel):
    """Admin response for list of rewards"""
    rewards: List[AdminRewardResponse]
    total: int
    filters: Dict[str, int]  # Count by status


class RewardStatsResponse(BaseModel):
    """Statistics for rewards"""
    total_goodies: int
    pending_details: int
    pending_shipment: int
    shipped: int
    delivered: int
    cancelled: int
    total_users_with_goodies: int
