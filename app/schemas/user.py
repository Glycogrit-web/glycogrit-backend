"""
User Schemas for CRUD operations
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import date


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    age: Optional[int] = Field(None, ge=1, le=150)
    t_shirt_size: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=100)


class PasswordChange(BaseModel):
    """Schema for changing password"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


class UserDetailResponse(BaseModel):
    """Detailed user response schema"""
    id: int
    email: Optional[str] = None  # Made optional for phone-only users
    phone: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    t_shirt_size: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    role: str = 'user'
    is_active: bool
    email_verified: bool
    oauth_provider: Optional[str] = None
    profile_picture_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
