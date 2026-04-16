"""
Event Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


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


class EventResponse(BaseModel):
    """Event response schema - maps to frontend Challenge interface"""
    id: int
    name: str
    slug: str
    description: str
    event_type: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    current_participants: int
    registration_fee: Optional[Decimal] = None
    currency: str
    difficulty_level: Optional[str] = None
    goals: Optional[List[str]] = None
    rewards: Optional[List[str]] = None
    banner_image_url: Optional[str] = None
    rules: Optional[str] = None
    is_virtual: bool
    is_featured: bool
    created_at: datetime

    class Config:
        from_attributes = True


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
    event_type: str = Field(..., max_length=50)
    status: Optional[str] = Field("draft", max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    event_date: datetime
    registration_start_date: datetime
    registration_end_date: datetime
    location: Optional[str] = Field(None, max_length=500)
    location_name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    country: str = Field(..., max_length=100)
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None
    currency: Optional[str] = Field("INR", max_length=10)
    difficulty_level: Optional[str] = Field(None, max_length=50)
    goals: Optional[List[str]] = None
    rewards: Optional[List[str]] = None
    banner_image_url: Optional[str] = Field(None, max_length=500)
    rules: Optional[str] = None
    is_virtual: Optional[bool] = False
    is_featured: Optional[bool] = False


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    event_type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    event_date: Optional[datetime] = None
    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=500)
    location_name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    total_distance: Optional[Decimal] = None
    max_participants: Optional[int] = None
    registration_fee: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=10)
    difficulty_level: Optional[str] = Field(None, max_length=50)
    goals: Optional[List[str]] = None
    rewards: Optional[List[str]] = None
    banner_image_url: Optional[str] = Field(None, max_length=500)
    rules: Optional[str] = None
    is_virtual: Optional[bool] = None
    is_featured: Optional[bool] = None


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
