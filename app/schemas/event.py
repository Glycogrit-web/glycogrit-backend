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
