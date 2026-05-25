"""
Payment Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Schema for initiating a payment"""
    amount: Decimal = Field(..., ge=0, description="Payment amount")
    payment_method: str = Field(..., max_length=50, description="Payment method (credit_card, upi, net_banking, etc.)")
    currency: str | None = Field("INR", max_length=10, description="Currency code")


class PaymentOrderCreate(BaseModel):
    """Schema for creating payment order (generic for any gateway)"""
    registration_id: int = Field(..., description="Registration ID for which payment is being made")
    gateway: str | None = Field(None, description="Payment gateway to use (razorpay, stripe, etc.). Uses default if not specified.")
    notes: dict[str, Any] | None = Field(None, description="Additional notes/metadata")


class PaymentVerify(BaseModel):
    """Schema for verifying payment (generic for any gateway)"""
    order_id: str = Field(..., description="Gateway order ID")
    payment_id: str = Field(..., description="Gateway payment ID")
    signature: str = Field(..., description="Payment signature for verification")
    gateway: str | None = Field(None, description="Payment gateway used")


# Deprecated: Kept for backward compatibility
class RazorpayOrderCreate(BaseModel):
    """Schema for creating Razorpay order (deprecated - use PaymentOrderCreate instead)"""
    registration_id: int = Field(..., description="Registration ID for which payment is being made")
    notes: dict[str, Any] | None = Field(None, description="Additional notes/metadata")


class RazorpayPaymentVerify(BaseModel):
    """Schema for verifying Razorpay payment (deprecated - use PaymentVerify instead)"""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature for verification")


class PaymentCaptureRequest(BaseModel):
    """Schema for capturing an authorized payment"""
    amount: Decimal | None = Field(None, ge=0, description="Amount to capture (None for full authorized amount)")


class RefundCreate(BaseModel):
    """Schema for creating a refund"""
    amount: Decimal | None = Field(None, ge=0, description="Amount to refund (None for full refund)")
    reason: str | None = Field(None, max_length=500, description="Reason for refund")
    notes: dict[str, Any] | None = Field(None, description="Additional notes")


class PaymentUpdate(BaseModel):
    """Schema for updating payment status"""
    status: str = Field(..., max_length=50, description="Payment status (pending, completed, failed, refunded)")
    transaction_id: str | None = Field(None, max_length=100, description="Transaction ID from payment gateway")
    gateway_reference: str | None = Field(None, max_length=100, description="Gateway reference number")
    gateway_name: str | None = Field(None, max_length=50, description="Payment gateway name (razorpay, stripe, etc.)")


class PaymentResponse(BaseModel):
    """Payment response schema"""
    id: int
    user_id: int
    registration_id: int
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    transaction_id: str | None = None
    gateway_reference: str | None = None
    gateway_name: str | None = None
    gateway_order_id: str | None = None  # Generic gateway order ID
    gateway_payment_id: str | None = None  # Generic gateway payment ID
    razorpay_order_id: str | None = None  # Kept for backward compatibility
    razorpay_payment_id: str | None = None  # Kept for backward compatibility
    refund_id: str | None = None
    refund_amount: Decimal | None = None
    refund_status: str | None = None
    refunded_at: datetime | None = None
    initiated_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else 0.0
        }


class PaymentOrderResponse(BaseModel):
    """Response schema for payment order creation (generic for any gateway)"""
    order_id: str
    amount: int  # Amount in smallest currency unit (paise for INR, cents for USD, etc.)
    currency: str
    gateway: str  # Gateway name (razorpay, stripe, etc.)
    payment: PaymentResponse


# Deprecated: Kept for backward compatibility
class RazorpayOrderResponse(BaseModel):
    """Response schema for Razorpay order creation (deprecated - use PaymentOrderResponse instead)"""
    order_id: str
    amount: int  # Amount in paise
    currency: str
    payment: PaymentResponse
