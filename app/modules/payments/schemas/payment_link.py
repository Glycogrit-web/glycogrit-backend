"""
Payment Link Schemas
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class PaymentLinkCreate(BaseModel):
    """Schema for creating a payment link"""

    registration_id: int = Field(
        ..., description="Registration ID for which payment link is being created"
    )
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    customer_email: EmailStr = Field(..., description="Customer email")
    customer_contact: str = Field(
        ..., min_length=10, max_length=20, description="Customer phone number with country code"
    )
    description: str | None = Field(None, max_length=500, description="Payment description")
    callback_url: str | None = Field(None, description="URL to redirect after payment")
    expire_in_days: int | None = Field(
        7, ge=1, le=30, description="Number of days until link expires (default: 7)"
    )


class PaymentLinkResponse(BaseModel):
    """Payment link response schema"""

    id: int
    user_id: int
    registration_id: int | None
    razorpay_link_id: str
    short_url: str
    amount: Decimal
    currency: str
    description: str | None
    reference_id: str | None
    customer_name: str | None
    customer_email: str | None
    customer_contact: str | None
    callback_url: str | None
    status: str
    expires_at: datetime
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentLinkUpdate(BaseModel):
    """Schema for updating payment link status"""

    status: str = Field(..., description="New status (active, paid, expired, cancelled)")
