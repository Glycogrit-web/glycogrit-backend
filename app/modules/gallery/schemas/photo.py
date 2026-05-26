"""
Gallery Photo Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PhotoSubmitRequest(BaseModel):
    """Photo submission request"""

    photo_url: str = Field(..., description="URL of uploaded photo (Cloudflare R2)")
    caption: str | None = Field(None, max_length=500, description="Photo caption")
    event_id: int | None = Field(None, description="Associated event ID")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_url": "https://r2.example.com/photos/12345.jpg",
                "caption": "Finished my first marathon!",
                "event_id": 10,
            }
        }


class PhotoResponse(BaseModel):
    """Photo response"""

    id: int
    user_id: int
    photo_url: str
    thumbnail_url: str | None
    caption: str | None
    event_id: int | None
    is_approved: bool
    is_featured: bool
    view_count: int
    created_at: datetime
    updated_at: datetime | None

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
