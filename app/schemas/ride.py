from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.ride import RideStatus, RideDifficulty


class RideBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_location: str
    end_location: Optional[str] = None
    distance: Optional[float] = None
    difficulty: RideDifficulty = RideDifficulty.MODERATE
    estimated_duration: Optional[int] = None
    elevation_gain: Optional[float] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    max_participants: Optional[int] = None


class RideCreate(RideBase):
    pass


class RideUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance: Optional[float] = None
    difficulty: Optional[RideDifficulty] = None
    estimated_duration: Optional[int] = None
    elevation_gain: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_participants: Optional[int] = None
    status: Optional[RideStatus] = None


class RideResponse(RideBase):
    id: int
    organizer_id: int
    image_url: Optional[str] = None
    route_map_url: Optional[str] = None
    current_participants: int
    status: RideStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
