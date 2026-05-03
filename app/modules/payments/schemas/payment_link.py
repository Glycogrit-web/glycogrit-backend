"""
Payment Link Schemas
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PaymentLinkCreate(BaseModel):
    """Schema for creating a payment link"""
    registration_id: int = Field(..., description="Registration ID for which payment link is being created")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    customer_email: EmailStr = Field(..., description="Customer email")
    customer_contact: str = Field(..., min_length=10, max_length=20, description="Customer phone number with country code")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    callback_url: Optional[str] = Field(None, description="URL to redirect after payment")
    expire_in_days: Optional[int] = Field(7, ge=1, le=30, description="Number of days until link expires (default: 7)")


class PaymentLinkResponse(BaseModel):
    """Payment link response schema"""
    id: int
    user_id: int
    registration_id: Optional[int]
    razorpay_link_id: str
    short_url: str
    amount: Decimal
    currency: str
    description: Optional[str]
    reference_id: Optional[str]
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_contact: Optional[str]
    callback_url: Optional[str]
    status: str
    expires_at: datetime
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentLinkUpdate(BaseModel):
    """Schema for updating payment link status"""
    status: str = Field(..., description="New status (active, paid, expired, cancelled)")
