"""
Gallery Photo Schemas
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class PhotoSubmitRequest(BaseModel):
    """Photo submission request"""
    photo_url: str = Field(..., description="URL of uploaded photo (Cloudflare R2)")
    caption: Optional[str] = Field(None, max_length=500, description="Photo caption")
    event_id: Optional[int] = Field(None, description="Associated event ID")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_url": "https://r2.example.com/photos/12345.jpg",
                "caption": "Finished my first marathon!",
                "event_id": 10
            }
        }


class PhotoResponse(BaseModel):
    """Photo response"""
    id: int
    user_id: int
    photo_url: str
    thumbnail_url: Optional[str]
    caption: Optional[str]
    event_id: Optional[int]
    is_approved: bool
    is_featured: bool
    view_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PhotoApproveRequest(BaseModel):
    """Photo approval request"""
    is_featured: bool = Field(False, description="Mark as featured photo")


class PhotoListResponse(BaseModel):
    """Photo list response"""
    photos: list[PhotoResponse]
    total: int
    page: int
    page_size: int
