"""
Activity Pydantic Schemas

Schemas for API request/response validation and serialization.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, validator


class ActivityBase(BaseModel):
    """Base schema for activity data"""
    activity_date: date = Field(..., description="Date of the activity")
    distance: Decimal | None = Field(None, ge=0, description="Distance in kilometers")
    duration: int | None = Field(None, ge=0, description="Duration in minutes")
    notes: str | None = Field(None, max_length=500, description="Activity notes")

    @validator('activity_date')
    def validate_activity_date(cls, v):
        """Validate activity date is not in future"""
        if v > date.today():
            raise ValueError("Activity date cannot be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "activity_date": "2024-01-15",
                "distance": 5.5,
                "duration": 30,
                "notes": "Morning run in the park"
            }
        }


class ActivityCreate(ActivityBase):
    """Schema for creating a new activity"""
    event_id: int = Field(..., description="Event ID")
    registration_id: int | None = Field(None, description="Registration ID")


class ActivityUpdate(BaseModel):
    """Schema for updating an activity"""
    distance: Decimal | None = Field(None, ge=0, description="Distance in kilometers")
    duration: int | None = Field(None, ge=0, description="Duration in minutes")
    activity_date: date | None = Field(None, description="Activity date")
    notes: str | None = Field(None, max_length=500, description="Activity notes")

    @validator('activity_date')
    def validate_activity_date(cls, v):
        """Validate activity date is not in future"""
        if v and v > date.today():
            raise ValueError("Activity date cannot be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "distance": 6.2,
                "duration": 35,
                "notes": "Updated distance and time"
            }
        }


class ActivityResponse(BaseModel):
    """Schema for activity response"""
    id: int
    user_id: int
    event_id: int
    registration_id: int | None
    activity_date: date
    distance: Decimal | None
    duration: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    pace: str | None = Field(None, description="Pace in min/km format (e.g., '5:30')")
    speed: float | None = Field(None, description="Speed in km/h")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "event_id": 456,
                "registration_id": 789,
                "activity_date": "2024-01-15",
                "distance": 5.5,
                "duration": 30,
                "notes": "Morning run in the park",
                "pace": "5:27",
                "speed": 11.0,
                "created_at": "2024-01-15T08:30:00",
                "updated_at": "2024-01-15T08:30:00"
            }
        }


class ActivityListResponse(BaseModel):
    """Schema for paginated activity list"""
    activities: list[ActivityResponse]
    total: int
    skip: int
    limit: int

    class Config:
        json_schema_extra = {
            "example": {
                "activities": [],
                "total": 25,
                "skip": 0,
                "limit": 10
            }
        }


class ActivityStatsResponse(BaseModel):
    """Schema for activity statistics"""
    total_distance_km: float = Field(..., description="Total distance in kilometers")
    total_duration_minutes: int = Field(..., description="Total duration in minutes")
    activity_count: int = Field(..., description="Number of activities")
    average_distance_km: float = Field(..., description="Average distance per activity")
    average_duration_minutes: float = Field(..., description="Average duration per activity")
    average_pace: str | None = Field(None, description="Average pace in min/km")

    class Config:
        json_schema_extra = {
            "example": {
                "total_distance_km": 125.5,
                "total_duration_minutes": 720,
                "activity_count": 20,
                "average_distance_km": 6.28,
                "average_duration_minutes": 36.0,
                "average_pace": "5:44"
            }
        }
