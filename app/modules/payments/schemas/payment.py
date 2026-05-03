"""
Payment Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class PaymentCreate(BaseModel):
    """Schema for initiating a payment"""
    amount: Decimal = Field(..., ge=0, description="Payment amount")
    payment_method: str = Field(..., max_length=50, description="Payment method (credit_card, upi, net_banking, etc.)")
    currency: Optional[str] = Field("INR", max_length=10, description="Currency code")


class PaymentOrderCreate(BaseModel):
    """Schema for creating payment order (generic for any gateway)"""
    registration_id: int = Field(..., description="Registration ID for which payment is being made")
    gateway: Optional[str] = Field(None, description="Payment gateway to use (razorpay, stripe, etc.). Uses default if not specified.")
    notes: Optional[Dict[str, Any]] = Field(None, description="Additional notes/metadata")


class PaymentVerify(BaseModel):
    """Schema for verifying payment (generic for any gateway)"""
    order_id: str = Field(..., description="Gateway order ID")
    payment_id: str = Field(..., description="Gateway payment ID")
    signature: str = Field(..., description="Payment signature for verification")
    gateway: Optional[str] = Field(None, description="Payment gateway used")


# Deprecated: Kept for backward compatibility
class RazorpayOrderCreate(BaseModel):
    """Schema for creating Razorpay order (deprecated - use PaymentOrderCreate instead)"""
    registration_id: int = Field(..., description="Registration ID for which payment is being made")
    notes: Optional[Dict[str, Any]] = Field(None, description="Additional notes/metadata")


class RazorpayPaymentVerify(BaseModel):
    """Schema for verifying Razorpay payment (deprecated - use PaymentVerify instead)"""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature for verification")


class PaymentCaptureRequest(BaseModel):
    """Schema for capturing an authorized payment"""
    amount: Optional[Decimal] = Field(None, ge=0, description="Amount to capture (None for full authorized amount)")


class RefundCreate(BaseModel):
    """Schema for creating a refund"""
    amount: Optional[Decimal] = Field(None, ge=0, description="Amount to refund (None for full refund)")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for refund")
    notes: Optional[Dict[str, Any]] = Field(None, description="Additional notes")


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
    gateway_order_id: Optional[str] = None  # Generic gateway order ID
    gateway_payment_id: Optional[str] = None  # Generic gateway payment ID
    razorpay_order_id: Optional[str] = None  # Kept for backward compatibility
    razorpay_payment_id: Optional[str] = None  # Kept for backward compatibility
    refund_id: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    refund_status: Optional[str] = None
    refunded_at: Optional[datetime] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
