"""
User Schemas for CRUD operations
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator
from typing import Optional
from datetime import date
import re


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
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must be 8-100 characters with uppercase, lowercase, digit, and special character"
    )

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        # Check for lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        # Check for digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')

        return v


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    t_shirt_size: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    role: str = 'user'
    is_active: bool
    email_verified: bool
    oauth_provider: Optional[str] = None
    profile_picture_url: Optional[str] = None
    has_password: bool = Field(..., description="Whether user has password set")

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Detailed user response schema"""
    id: int
    email: Optional[str] = None
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
    primary_sync_source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
