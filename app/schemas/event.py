"""
Event Schemas
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal

if TYPE_CHECKING:
    from app.schemas.tier import TierResponse


class EventBase(BaseModel):
    """Base event schema"""
    name: str
    description: str
    difficulty_level: Optional[str] = None
    goals: Optional[List[str]] = None
    rewards: Optional[List[str]] = None
    banner_image_url: Optional[str] = None
    banner_crop_data: Optional[dict] = None
    banner_dominant_color: Optional[str] = None
    banner_accent_color: Optional[str] = None
    rules: Optional[str] = None


class ActivityResponse(BaseModel):
    """Event activity response schema - represents selectable activities like '5K Run', '10K Cycle'"""
    id: int
    event_id: int
    name: str  # "5K Run", "10K Cycle", etc.
    activity_type: Optional[str] = None  # "running", "cycling", "walking", etc.
    distance: Optional[Decimal] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None
    current_participants: int
    registration_fee: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    """Event response schema - maps to frontend Challenge interface"""
    id: int
    name: str
    slug: str
    description: str
    status: str
    event_date: Optional[datetime] = None  # Event start date/time
    event_end_date: Optional[datetime] = None  # Event end date/time (actual event timeline)
    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    location: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    current_participants: int
    currency: str
    difficulty_level: Optional[str] = None
    goals: Optional[List[str]] = None
    banner_image_url: Optional[str] = None
    banner_crop_data: Optional[dict] = None
    banner_dominant_color: Optional[str] = None
    banner_accent_color: Optional[str] = None
    rules: Optional[str] = None
    is_virtual: bool
    is_featured: bool
    uses_tier_system: bool
    created_at: datetime
    activities: List['ActivityResponse'] = []  # Renamed from categories
    tiers: List['TierResponse'] = Field(default=[], alias='registration_tiers', serialization_alias='tiers')  # Registration tiers

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True  # Allow using both 'tiers' and 'registration_tiers' field names
    )

# Update forward references after all models are defined
from app.schemas.tier import TierResponse
EventResponse.model_rebuild()


class EventListResponse(BaseModel):
    """Event list response with pagination"""
    events: List[EventResponse]
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

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    """Schema for creating a new event"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    status: Optional[str] = Field("draft", max_length=50)
    event_date: datetime
    event_end_date: Optional[datetime] = None
    registration_start_date: datetime
    registration_end_date: datetime
    location: Optional[str] = Field(None, max_length=500)
    location_name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    country: str = Field(..., max_length=100)
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    currency: Optional[str] = Field("INR", max_length=10)
    difficulty_level: Optional[str] = Field(None, max_length=50)
    goals: Optional[List[str]] = None
    banner_image_url: Optional[str] = Field(None, max_length=500)
    rules: Optional[str] = None
    is_virtual: Optional[bool] = False
    is_featured: Optional[bool] = False


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, max_length=50)
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None  # Event end date/time (actual event timeline)
    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=500)
    location_name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    currency: Optional[str] = Field(None, max_length=10)
    difficulty_level: Optional[str] = Field(None, max_length=50)
    goals: Optional[List[str]] = None
    banner_image_url: Optional[str] = Field(None, max_length=500)
    banner_dominant_color: Optional[str] = Field(None, max_length=50, description="Dominant color extracted from banner (#RRGGBB)")
    banner_accent_color: Optional[str] = Field(None, max_length=50, description="Accent color extracted from banner (#RRGGBB)")
    rules: Optional[str] = None
    is_virtual: Optional[bool] = None
    is_featured: Optional[bool] = None


class ActivityCreate(BaseModel):
    """Schema for creating a new event activity"""
    name: str = Field(..., min_length=1, max_length=100, description="Activity name (e.g., '5K Run', '10K Cycle')")
    activity_type: str = Field(..., max_length=50, description="Activity type: running, cycling, walking, etc.")
    distance: Optional[Decimal] = Field(None, description="Distance in kilometers")
    description: Optional[str] = Field(None, max_length=255)
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None


class ActivityUpdate(BaseModel):
    """Schema for updating an event activity"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    activity_type: Optional[str] = Field(None, max_length=50)
    distance: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=255)
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None
