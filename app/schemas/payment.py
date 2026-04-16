"""
Payment Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PaymentCreate(BaseModel):
    """Schema for initiating a payment"""
    amount: Decimal = Field(..., ge=0, description="Payment amount")
    payment_method: str = Field(..., max_length=50, description="Payment method (credit_card, upi, net_banking, etc.)")
    currency: Optional[str] = Field("INR", max_length=10, description="Currency code")


class PaymentUpdate(BaseModel):
    """Schema for updating payment status"""
    status: str = Field(..., max_length=50, description="Payment status (pending, completed, failed, refunded)")
    transaction_id: Optional[str] = Field(None, max_length=100, description="Transaction ID from payment gateway")
    gateway_reference: Optional[str] = Field(None, max_length=100, description="Gateway reference number")
    gateway_name: Optional[str] = Field(None, max_length=50, description="Payment gateway name (razorpay, stripe, etc.)")


class PaymentResponse(BaseModel):
    """Payment response schema"""
    id: int
    user_id: int
    registration_id: int
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    transaction_id: Optional[str] = None
    gateway_reference: Optional[str] = None
    gateway_name: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
