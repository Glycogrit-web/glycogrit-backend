"""
Event Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal

if TYPE_CHECKING:
    from app.schemas.tier import TierResponse


class ActivityTypeResponse(BaseModel):
    """Activity type response schema"""
    id: int
    activity_type: str
    is_primary: bool

    class Config:
        from_attributes = True


class EventBase(BaseModel):
    """Base event schema"""
    name: str
    description: str
    event_type: str
    difficulty_level: Optional[str] = None
    goals: Optional[List[str]] = None
    rewards: Optional[List[str]] = None
    banner_image_url: Optional[str] = None
    rules: Optional[str] = None


class CategoryResponse(BaseModel):
    """Event category response schema"""
    id: int
    event_id: int
    name: str
    distance: Optional[Decimal] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None
    current_participants: int
    registration_fee: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Event response schema - maps to frontend Challenge interface"""
    id: int
    name: str
    slug: str
    description: str
    event_type: str  # Kept for backward compatibility - primary activity type
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
    rules: Optional[str] = None
    is_virtual: bool
    is_featured: bool
    created_at: datetime
    categories: List['CategoryResponse'] = []
    tiers: List['TierResponse'] = Field(default=[], alias='registration_tiers', serialization_alias='tiers')  # Registration tiers
    activity_types: List['ActivityTypeResponse'] = []  # Multiple activity types (e.g., triathlon = running + cycling + swimming)

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow using both 'tiers' and 'registration_tiers' field names

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
    category_id: Optional[int] = None


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
    event_type: str = Field(..., max_length=50)  # Primary activity type (for backward compatibility)
    activity_types: Optional[List[str]] = None  # Multiple activity types (e.g., ["running", "cycling", "swimming"])
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
    event_type: Optional[str] = Field(None, max_length=50)  # Primary activity type
    activity_types: Optional[List[str]] = None  # Update multiple activity types
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
    rules: Optional[str] = None
    is_virtual: Optional[bool] = None
    is_featured: Optional[bool] = None


class CategoryCreate(BaseModel):
    """Schema for creating a new event category"""
    name: str = Field(..., min_length=1, max_length=100)
    distance: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=255)
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None


class CategoryUpdate(BaseModel):
    """Schema for updating an event category"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    distance: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=255)
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None
