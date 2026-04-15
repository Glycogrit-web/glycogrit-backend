from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.event import EventType


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: EventType = EventType.GROUP_RIDE
    location: str
    venue_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    distance: Optional[float] = None
    entry_fee: float = 0
    max_participants: Optional[int] = None


class EventCreate(EventBase):
    organizer_name: str
    organizer_contact: Optional[str] = None
    organizer_email: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    location: Optional[str] = None
    venue_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    distance: Optional[float] = None
    entry_fee: Optional[float] = None
    max_participants: Optional[int] = None
    is_registration_open: Optional[bool] = None
    is_published: Optional[bool] = None


class EventResponse(EventBase):
    id: int
    image_url: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    current_participants: int
    registration_url: Optional[str] = None
    is_registration_open: bool
    organizer_name: Optional[str] = None
    organizer_contact: Optional[str] = None
    organizer_email: Optional[str] = None
    is_featured: bool
    is_published: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
