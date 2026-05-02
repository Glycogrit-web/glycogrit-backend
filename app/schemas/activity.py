"""
Activity Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class ActivitySubmit(BaseModel):
    """Activity submission schema"""
    distance: Optional[Decimal] = Field(None, ge=0, description="Distance in kilometers")
    duration: Optional[int] = Field(None, ge=0, description="Duration in minutes")
    activity_date: date = Field(..., description="Date of activity (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")


class ActivityUpdate(BaseModel):
    """Activity update schema"""
    distance: Optional[Decimal] = Field(None, ge=0, description="Distance in kilometers")
    duration: Optional[int] = Field(None, ge=0, description="Duration in minutes")
    activity_date: Optional[date] = Field(None, description="Date of activity (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")


class ActivityResponse(BaseModel):
    """Activity response schema"""
    id: int
    user_id: int
    event_id: int
    registration_id: Optional[int] = None
    distance: Optional[Decimal] = None
    duration: Optional[int] = None
    activity_date: date
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityListResponse(BaseModel):
    """Activity list response"""
    activities: list[ActivityResponse]
    total: int
    page: int
    page_size: int
