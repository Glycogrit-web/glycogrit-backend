"""
User Schemas for CRUD operations
"""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator


class UserUpdate(BaseModel):
    """Schema for updating user profile"""

    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(None, max_length=20)
    age: int | None = Field(None, ge=1, le=150)
    t_shirt_size: str | None = Field(None, max_length=10)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=10)
    country: str | None = Field(None, max_length=100)


class PasswordChange(BaseModel):
    """Schema for changing password"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must be 8-100 characters with uppercase, lowercase, digit, and special character",
    )

    @validator("new_password")
    def validate_password_strength(cls, v):
        """Validate password strength requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(
                'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'
            )

        return v


class UserResponse(BaseModel):
    """User response schema"""

    id: int
    email: str | None = None
    phone: str | None = None
    first_name: str
    last_name: str
    date_of_birth: str | None = None
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    role: str = "user"
    is_active: bool
    email_verified: bool
    oauth_provider: str | None = None
    profile_picture_url: str | None = None
    has_password: bool = Field(..., description="Whether user has password set")

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Detailed user response schema"""

    id: int
    email: str | None = None
    phone: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    age: int | None = None
    t_shirt_size: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    role: str = "user"
    is_active: bool
    email_verified: bool
    oauth_provider: str | None = None
    profile_picture_url: str | None = None
    primary_sync_source: str | None = None

    model_config = ConfigDict(from_attributes=True)
