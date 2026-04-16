"""
Registration Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RegistrationCreate(BaseModel):
    """Schema for creating a new registration"""
    category_id: Optional[int] = None
    participant_name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    t_shirt_size: Optional[str] = Field(None, max_length=10)


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration"""
    participant_name: Optional[str] = Field(None, min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    t_shirt_size: Optional[str] = Field(None, max_length=10)
    bib_number: Optional[str] = Field(None, max_length=50)


class RegistrationResponse(BaseModel):
    """Registration response schema"""
    id: int
    user_id: int
    event_id: int
    event_category_id: Optional[int] = None
    registration_number: str
    bib_number: Optional[str] = None
    status: str
    participant_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    t_shirt_size: Optional[str] = None
    registered_at: datetime
    confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
