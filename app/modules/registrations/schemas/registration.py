"""
Registration Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RegistrationCreate(BaseModel):
    """Schema for creating a new registration"""

    activity_id: int = Field(
        ..., description="ID of the selected activity (e.g., 5K Run, 10K Cycle) - REQUIRED"
    )
    participant_name: str = Field(..., min_length=1, max_length=255)
    age: int | None = Field(None, ge=1, le=150)
    gender: str | None = Field(None, max_length=20)
    t_shirt_size: str | None = Field(None, max_length=10)


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration"""

    participant_name: str | None = Field(None, min_length=1, max_length=255)
    age: int | None = Field(None, ge=1, le=150)
    gender: str | None = Field(None, max_length=20)
    t_shirt_size: str | None = Field(None, max_length=10)
    bib_number: str | None = Field(None, max_length=50)

    # Shipping information (for reward delivery)
    shipping_address_line1: str | None = Field(None, max_length=255)
    shipping_address_line2: str | None = Field(None, max_length=255)
    shipping_city: str | None = Field(None, max_length=100)
    shipping_state: str | None = Field(None, max_length=100)
    shipping_postal_code: str | None = Field(None, max_length=20)
    shipping_country: str | None = Field(None, max_length=100)
    shipping_phone: str | None = Field(None, max_length=20)
    shipping_email: str | None = Field(None, max_length=255)


class RegistrationResponse(BaseModel):
    """Registration response schema"""

    id: int
    user_id: int
    event_id: int
    event_activity_id: int | None = None
    registration_number: str
    bib_number: str | None = None
    status: str
    participant_name: str
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None
    registered_at: datetime
    confirmed_at: datetime | None = None
    current_tier_id: int | None = None  # For tier system - tracks user's current tier

    # Tier information (detailed)
    tier_name: str | None = None
    tier_price: float | None = None
    tier_rewards: list[str] | None = None
    tier_description: str | None = None
    tier_order: int | None = None
    can_upgrade: bool = False  # Whether user can upgrade to higher tier
    available_upgrades: list[dict] | None = None  # List of available higher tiers

    # Payment information
    total_amount_paid: float = 0.0

    # Shipping information (for reward delivery)
    shipping_address_line1: str | None = None
    shipping_address_line2: str | None = None
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_postal_code: str | None = None
    shipping_country: str | None = None
    shipping_phone: str | None = None
    shipping_email: str | None = None

    # Activity progress information (from activity_progress table)
    total_distance_km: float | None = None
    goal_distance_km: float | None = None
    progress_percentage: float | None = None
    last_sync_source: str | None = None
    last_sync_at: datetime | None = None
    proof_image_url: str | None = None
    proof_image_viewed_by_admin: bool | None = None

    # Reward status (for admin views)
    reward_status: dict | None = None

    # External certificate fields (for bulk certificate distribution via Google Drive)
    external_certificate_url: str | None = None
    external_certificate_unlocked: bool = False
    external_certificate_distance: float | None = None
    external_certificate_activity_type: str | None = None
    external_certificate_uploaded_at: datetime | None = None

    class Config:
        from_attributes = True
