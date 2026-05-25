"""
Event Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.core.tier_schemas import TierResponse


class EventBase(BaseModel):
    """Base event schema"""
    name: str
    description: str
    goals: list[str] | None = None
    rewards: list[str] | None = None
    banner_image_url: str | None = None
    rules: str | None = None


class ActivityResponse(BaseModel):
    """Event activity response schema - represents selectable activities like '5K Run', '10K Cycle'"""
    id: int
    event_id: int
    name: str  # "5K Run", "10K Cycle", etc.
    activity_type: str | None = None  # "running", "cycling", "walking", etc.
    distance: Decimal | None = None
    description: str | None = None
    max_participants: int | None = None
    current_participants: int
    registration_fee: Decimal | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Event response schema - maps to frontend Challenge interface"""
    id: int
    name: str
    slug: str
    description: str
    status: str
    event_date: datetime | None = None  # Event start date/time
    event_end_date: datetime | None = None  # Event end date/time (actual event timeline)
    registration_start_date: datetime | None = None
    registration_end_date: datetime | None = None
    current_participants: int
    currency: str
    goals: list[str] | None = None
    banner_image_url: str | None = None
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool
    is_featured: bool
    uses_tier_system: bool
    created_at: datetime
    activities: list['ActivityResponse'] = []  # Renamed from categories
    tiers: list['TierResponse'] = Field(default=[], alias='registration_tiers', serialization_alias='tiers')  # Registration tiers

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow using both 'tiers' and 'registration_tiers' field names

# Update forward references after all models are defined
from app.core.tier_schemas import TierResponse

EventResponse.model_rebuild()


class EventListResponse(BaseModel):
    """Event list response with pagination"""
    events: list[EventResponse]
    total: int
    page: int
    page_size: int


class EventRegisterRequest(BaseModel):
    """Event registration request"""
    activity_id: int = Field(..., description="ID of the selected activity (e.g., 5K Run, 10K Cycle)")


class EventRegisterResponse(BaseModel):
    """Event registration response"""
    id: int
    event_id: int
    user_id: int
    status: str
    registered_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    """Schema for creating a new event"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    status: str | None = Field("draft", max_length=50)
    event_date: datetime
    event_end_date: datetime | None = None
    registration_start_date: datetime
    registration_end_date: datetime
    currency: str | None = Field("INR", max_length=10)
    goals: list[str] | None = None
    banner_image_url: str | None = Field(None, max_length=500)
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool | None = True  # All events are virtual by default
    is_featured: bool | None = False


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    status: str | None = Field(None, max_length=50)
    event_date: datetime | None = None
    event_end_date: datetime | None = None  # Event end date/time (actual event timeline)
    registration_start_date: datetime | None = None
    registration_end_date: datetime | None = None
    currency: str | None = Field(None, max_length=10)
    goals: list[str] | None = None
    banner_image_url: str | None = Field(None, max_length=500)
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool | None = None
    is_featured: bool | None = None


class ActivityCreate(BaseModel):
    """Schema for creating a new event activity"""
    name: str = Field(..., min_length=1, max_length=100, description="Activity name (e.g., '5K Run', '10K Cycle')")
    activity_type: str = Field(..., max_length=50, description="Activity type: running, cycling, walking, etc.")
    distance: Decimal | None = Field(None, description="Distance in kilometers")
    description: str | None = Field(None, max_length=255)
    max_participants: int | None = None
    registration_fee: Decimal | None = None


class ActivityUpdate(BaseModel):
    """Schema for updating an event activity"""
    name: str | None = Field(None, min_length=1, max_length=100)
    activity_type: str | None = Field(None, max_length=50)
    distance: Decimal | None = None
    description: str | None = Field(None, max_length=255)
    max_participants: int | None = None
    registration_fee: Decimal | None = None
