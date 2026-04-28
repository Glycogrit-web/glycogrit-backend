"""
Event Registration Tier Schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class TierBase(BaseModel):
    """Base tier schema"""
    tier_name: str = Field(..., min_length=1, max_length=100)
    tier_slug: str = Field(..., min_length=1, max_length=100)
    tier_order: int = Field(default=0, ge=0)
    description: Optional[str] = None
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=10)
    requires_payment: bool = Field(default=False)
    max_registrations: Optional[int] = Field(default=None, ge=1)
    rewards: Optional[List[str]] = Field(default=None)

    @validator('rewards')
    def validate_rewards(cls, v):
        """Validate rewards list"""
        if v is not None and len(v) == 0:
            return None
        return v

    @validator('requires_payment')
    def validate_requires_payment(cls, v, values):
        """Auto-correct requires_payment based on price"""
        if 'price' in values:
            # If price is 0, force requires_payment to False
            if values['price'] == 0:
                return False
            # If price > 0, force requires_payment to True
            return True
        return v


class TierCreate(TierBase):
    """Schema for creating a new tier"""
    pass


class TierUpdate(BaseModel):
    """Schema for updating a tier"""
    tier_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    max_registrations: Optional[int] = Field(None, ge=1)
    rewards: Optional[List[str]] = None

    @validator('rewards')
    def validate_rewards(cls, v):
        """Validate rewards list"""
        if v is not None and len(v) == 0:
            return None
        return v


class TierResponse(TierBase):
    """Tier response schema"""
    id: int
    event_id: int
    is_active: bool
    current_registrations: int
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_free: bool = Field(default=False)
    capacity_remaining: Optional[int] = None
    is_sold_out: bool = Field(default=False)
    formatted_price: str = Field(default="Free")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_computed(cls, tier):
        """Create response with computed fields"""
        # Auto-correct requires_payment based on price
        requires_payment = tier.price > 0 if tier.price is not None else tier.requires_payment

        data = {
            'id': tier.id,
            'event_id': tier.event_id,
            'tier_name': tier.tier_name,
            'tier_slug': tier.tier_slug,
            'tier_order': tier.tier_order,
            'description': tier.description,
            'price': tier.price,
            'currency': tier.currency,
            'requires_payment': requires_payment,  # Use corrected value
            'is_active': tier.is_active,
            'max_registrations': tier.max_registrations,
            'current_registrations': tier.current_registrations,
            'rewards': tier.rewards,
            'created_at': tier.created_at,
            'updated_at': tier.updated_at,
            'is_free': tier.is_free,
            'capacity_remaining': tier.capacity_remaining,
            'is_sold_out': tier.is_sold_out,
            'formatted_price': tier.get_formatted_price(),
        }
        return cls(**data)


class RegistrationTierCreate(BaseModel):
    """Schema for registering for a specific tier"""
    tier_id: int = Field(..., gt=0)
    participant_name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = Field(None, max_length=20)
    t_shirt_size: Optional[str] = Field(None, max_length=10)


class TierUpgradeRequest(BaseModel):
    """Schema for upgrading to a new tier"""
    new_tier_id: int = Field(..., gt=0)


class RegistrationTierResponse(BaseModel):
    """Response schema for registration tier junction"""
    id: int
    registration_id: int
    tier_id: int
    tier_name: str
    tier_price: Decimal
    registered_at: datetime
    is_upgrade: bool
    upgraded_from_tier_id: Optional[int] = None
    upgrade_payment_id: Optional[int] = None

    class Config:
        from_attributes = True


class TierUpgradeResponse(BaseModel):
    """Response for tier upgrade request"""
    success: bool
    message: str
    upgrade_price: Decimal
    requires_payment: bool
    payment_order: Optional[dict] = None  # Payment order details if payment required
    registration_id: int
    new_tier_id: int
    new_tier_name: str


class EffectiveRewardsResponse(BaseModel):
    """Response for user's effective rewards"""
    registration_id: int
    tier_names: List[str]
    all_rewards: List[str]
    highest_tier: str
