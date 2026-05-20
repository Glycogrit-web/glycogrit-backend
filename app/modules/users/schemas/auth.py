"""
Authentication Schemas
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator, root_validator
from typing import Optional
import re
from app.core.validators import ValidationHelper


class UserRegister(BaseModel):
    """User registration schema - supports email OR phone registration"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, description="10-digit phone number")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be 8-128 characters with uppercase, lowercase, digit, and special character"
    )
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)

    @root_validator(skip_on_failure=True)
    def check_identifier(cls, values):
        """Ensure at least one identifier (email or phone) is provided"""
        email = values.get('email')
        phone = values.get('phone')

        if not email and not phone:
            raise ValueError('Either email or phone must be provided')

        return values

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength using enhanced security requirements"""
        return ValidationHelper.validate_password_strength(v, min_length=8, require_special=True)

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format (10 digits)"""
        if v is not None:
            # Remove any spaces, dashes, or other formatting
            cleaned = re.sub(r'[^\d]', '', v)
            if not cleaned.isdigit() or len(cleaned) != 10:
                raise ValueError('Phone must be exactly 10 digits')
            return cleaned
        return v


class UserLogin(BaseModel):
    """User login schema - supports email OR phone login"""
    identifier: str = Field(..., description="Email or phone number")
    password: str
    identifier_type: Optional[str] = Field(None, description="'email' or 'phone' (auto-detected if not provided)")

    @validator('identifier_type')
    def validate_identifier_type(cls, v):
        """Validate identifier type"""
        if v and v not in ['email', 'phone']:
            raise ValueError("identifier_type must be 'email' or 'phone'")
        return v


class GoogleAuthRequest(BaseModel):
    """Google OAuth authentication request schema"""
    token: str = Field(..., description="Google OAuth ID token from frontend")


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema"""
    user_id: Optional[int] = None


class ConnectEmail(BaseModel):
    """Schema for connecting email to existing account"""
    email: EmailStr


class ConnectPhone(BaseModel):
    """Schema for connecting phone to existing account"""
    phone: str = Field(..., description="10-digit phone number")

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format (10 digits)"""
        cleaned = re.sub(r'[^\d]', '', v)
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Phone must be exactly 10 digits')
        return cleaned


class SetPasswordForOAuth(BaseModel):
    """Schema for OAuth users to set password for phone login"""
    phone: str = Field(..., description="10-digit phone number")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be 8-128 characters with uppercase, lowercase, digit, and special character"
    )

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength using enhanced security requirements"""
        return ValidationHelper.validate_password_strength(v, min_length=8, require_special=True)

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format (10 digits)"""
        cleaned = re.sub(r'[^\d]', '', v)
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Phone must be exactly 10 digits')
        return cleaned
