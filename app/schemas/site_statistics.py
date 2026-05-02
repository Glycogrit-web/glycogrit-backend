"""
Site Statistics Schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SiteStatisticsBase(BaseModel):
    """Base schema for site statistics"""
    total_users: int = Field(..., ge=0, description="Total active users")
    total_events: int = Field(..., ge=0, description="Total challenges/events")
    total_registrations: int = Field(..., ge=0, description="Total registrations")
    total_medals_shipped: int = Field(..., ge=0, description="Total medals shipped")


class SiteStatisticsResponse(SiteStatisticsBase):
    """Response schema for site statistics"""
    last_updated: datetime
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class SiteStatisticsUpdate(BaseModel):
    """Schema for updating site statistics manually"""
    total_users: Optional[int] = Field(None, ge=0)
    total_events: Optional[int] = Field(None, ge=0)
    total_registrations: Optional[int] = Field(None, ge=0)
    total_medals_shipped: Optional[int] = Field(None, ge=0)
