"""
Registration Schemas
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class RegistrationCreate(BaseModel):
    """Schema for creating a new registration"""
    activity_id: int = Field(..., description="ID of the selected activity (e.g., 5K Run, 10K Cycle) - REQUIRED")
    participant_name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    t_shirt_size: Optional[str] = Field(None, max_length=10)

    # Shipping address for reward delivery
    shipping_address_line1: Optional[str] = Field(None, max_length=255)
    shipping_address_line2: Optional[str] = Field(None, max_length=255)
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_state: Optional[str] = Field(None, max_length=100)
    shipping_postal_code: Optional[str] = Field(None, max_length=20)
    shipping_country: Optional[str] = Field(default='India', max_length=100)
    shipping_phone: Optional[str] = Field(None, max_length=20)
    shipping_email: Optional[str] = Field(None, max_length=255)


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration"""
    participant_name: Optional[str] = Field(None, min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    t_shirt_size: Optional[str] = Field(None, max_length=10)
    bib_number: Optional[str] = Field(None, max_length=50)


class RegistrationResponse(BaseModel):
    """Registration response schema"""
    id: int
    user_id: int
    event_id: int
    event_activity_id: Optional[int] = None
    registration_number: str
    bib_number: Optional[str] = None
    status: str
    participant_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    t_shirt_size: Optional[str] = None
    registered_at: datetime
    confirmed_at: Optional[datetime] = None
    current_tier_id: Optional[int] = None  # For tier system - tracks user's current tier

    # Shipping address
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
