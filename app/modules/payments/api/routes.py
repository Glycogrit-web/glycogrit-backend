"""
Payment API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, status, Query, Request, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
from app.modules.payments.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentOrderCreate,
    PaymentOrderResponse,
    PaymentVerify,
    RefundCreate,
    # Deprecated schemas kept for backward compatibility
    RazorpayOrderCreate,
    RazorpayOrderResponse,
    RazorpayPaymentVerify
)
from app.models.user import User
from app.modules.payments.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/registrations/{registration_id}/payment", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def initiate_payment(
    request: Request,
    response: Response,
    registration_id: int,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    Initiate a payment for a registration.

    Creates a new payment for a registration. Users can only initiate payments for their own registrations.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID to create payment for
        payment_data: Payment creation data (amount, method, currency)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentResponse: Created payment details

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner
        ValidationException: If payment data is invalid

    Rate Limit:
        20 requests per minute

    Authorization:
        Users can only initiate payments for their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.initiate_payment(
        registration_id=registration_id,
        user_id=current_user.id,
        amount=float(payment_data.amount),
        payment_method=payment_data.payment_method,
        currency=payment_data.currency
    )
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_payment(
    request: Request,
    response: Response,
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    Get payment details by ID.

    Returns detailed information about a specific payment.

    Args:
        request: FastAPI Request object (required for rate limiting)
        payment_id: Payment ID
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentResponse: Payment details

    Raises:
        NotFoundException: If payment not found
        PermissionDeniedException: If user is not the payment owner

    Rate Limit:
        100 requests per minute

    Authorization:
        Users can only view their own payments

    Requires:
        Bearer token in Authorization header
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.get_payment_by_id(payment_id)

    # Check ownership
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(payment.user_id, current_user.id, "payment")

    return payment


@router.put("/{payment_id}/status", response_model=PaymentResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_payment_status(
    request: Request,
    response: Response,
    payment_id: int,
    payment_data: PaymentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    Update payment status.

    Updates payment status and gateway information. Typically used by payment gateway webhooks.

    Args:
        request: FastAPI Request object (required for rate limiting)
        payment_id: Payment ID
        payment_data: Updated payment status and gateway information
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentResponse: Updated payment details

    Raises:
        NotFoundException: If payment not found
        PermissionDeniedException: If user is not the payment owner

    Rate Limit:
        30 requests per minute

    Authorization:
        Only payment owner can update status

    Requires:
        Bearer token in Authorization header

    Note:
        This endpoint is typically used by payment gateway webhooks or admin users.
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.get_payment_by_id(payment_id)

    # Check ownership - only payment owner can update status
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(payment.user_id, current_user.id, "payment")

    updated_payment: PaymentResponse = service.update_payment_status(
        payment_id=payment_id,
        status=payment_data.status,
        transaction_id=payment_data.transaction_id,
        gateway_reference=payment_data.gateway_reference,
        gateway_name=payment_data.gateway_name
    )
    return updated_payment


@router.get("/users/{user_id}/payments", response_model=List[PaymentResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_user_payments(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> List[PaymentResponse]:
    """
    Get all payments for a user.

    Returns list of all payments for a specific user.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: User ID
        current_user: Current authenticated user from JWT token
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session dependency

    Returns:
        List of PaymentResponse objects

    Raises:
        PermissionDeniedException: If user tries to view another user's payments

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view their own payments

    Requires:
        Bearer token in Authorization header
    """
    service: PaymentService = PaymentService(db)
    payments: List[PaymentResponse] = service.get_payments_by_user(user_id, current_user.id, skip, limit)
    return payments


@router.get("/registrations/{registration_id}/payments", response_model=List[PaymentResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_registration_payments(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[PaymentResponse]:
    """
    Get all payments for a registration.

    Returns list of all payments associated with a specific registration.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        List of PaymentResponse objects

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view payments for their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: PaymentService = PaymentService(db)
    payments: List[PaymentResponse] = service.get_payments_by_registration(registration_id, current_user.id)
    return payments


@router.post("/order/create", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_payment_order(
    request: Request,
    response: Response,
    order_data: PaymentOrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentOrderResponse:
    """
    Create a payment order for a registration (works with any payment gateway).

    Creates a payment order and initiates the payment process. Returns order details
    that should be used to open payment gateway checkout on the frontend.

    Args:
        request: FastAPI Request object (required for rate limiting)
        order_data: Order creation data with registration_id, optional gateway, and notes
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentOrderResponse: Order details including order_id, amount, currency, gateway, and payment record

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user doesn't own the registration
        ValidationException: If payment already completed or order creation fails

    Rate Limit:
        20 requests per minute

    Authorization:
        Users can only create orders for their own registrations

    Requires:
        Bearer token in Authorization header

    Example Request:
        {
            "registration_id": 123,
            "gateway": "razorpay",  // Optional: razorpay, stripe, etc. Uses default if not specified
            "notes": {"custom_field": "value"}
        }

    Example Response:
        {
            "order_id": "order_MNhgJKL123456",
            "amount": 50000,  // Amount in smallest unit (paise for INR)
            "currency": "INR",
            "gateway": "razorpay",
            "payment": { ... }  // Payment record details
        }
    """
    service: PaymentService = PaymentService(db)
    order: PaymentOrderResponse = service.create_payment_order(
        registration_id=order_data.registration_id,
        user_id=current_user.id,
        notes=order_data.notes,
        gateway=order_data.gateway
    )
    return order


@router.post("/verify", response_model=PaymentResponse)
@limiter.limit(RateLimits.WRITE_CREATE)
async def verify_payment(
    request: Request,
    response: Response,
    verify_data: PaymentVerify,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    Verify and complete a payment (works with any payment gateway).

    Verifies the payment signature and completes the payment if valid.
    Updates registration status to confirmed upon successful payment.

    Args:
        request: FastAPI Request object (required for rate limiting)
        verify_data: Payment verification data from payment gateway
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentResponse: Updated payment with completed status

    Raises:
        NotFoundException: If payment not found
        ValidationException: If signature verification fails
        PermissionDeniedException: If user doesn't own the payment

    Rate Limit:
        20 requests per minute

    Authorization:
        Users can only verify their own payments

    Requires:
        Bearer token in Authorization header

    Example Request:
        {
            "order_id": "order_MNhgJKL123456",
            "payment_id": "pay_MNhgJKL654321",
            "signature": "abc123...",
            "gateway": "razorpay"  // Optional
        }
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.verify_payment(
        order_id=verify_data.order_id,
        payment_id=verify_data.payment_id,
        signature=verify_data.signature,
        user_id=current_user.id,
        gateway=verify_data.gateway
    )
    return payment


# Deprecated endpoints kept for backward compatibility
@router.post("/razorpay/create-order", response_model=RazorpayOrderResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_razorpay_order_deprecated(
    request: Request,
    response: Response,
    order_data: RazorpayOrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> RazorpayOrderResponse:
    """
    [DEPRECATED] Create a Razorpay order - use /order/create instead.

    This endpoint is deprecated and will be removed in a future version.
    Use the generic /order/create endpoint instead.
    """
    service: PaymentService = PaymentService(db)
    order = service.create_payment_order(
        registration_id=order_data.registration_id,
        user_id=current_user.id,
        notes=order_data.notes,
        gateway="razorpay"
    )
    return order


@router.post("/razorpay/verify", response_model=PaymentResponse, deprecated=True)
@limiter.limit(RateLimits.WRITE_CREATE)
async def verify_razorpay_payment_deprecated(
    request: Request,
    response: Response,
    verify_data: RazorpayPaymentVerify,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    [DEPRECATED] Verify Razorpay payment - use /verify instead.

    This endpoint is deprecated and will be removed in a future version.
    Use the generic /verify endpoint instead.
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.verify_payment(
        order_id=verify_data.razorpay_order_id,
        payment_id=verify_data.razorpay_payment_id,
        signature=verify_data.razorpay_signature,
        user_id=current_user.id,
        gateway="razorpay"
    )
    return payment


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
@limiter.limit(RateLimits.WRITE_CREATE)
async def refund_payment(
    request: Request,
    response: Response,
    payment_id: int,
    refund_data: RefundCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    Create a refund for a payment.

    Initiates a refund for a completed payment through Razorpay.
    Updates payment status to refunded and cancels the associated registration.

    Args:
        request: FastAPI Request object (required for rate limiting)
        payment_id: Payment ID to refund
        refund_data: Refund details (amount, reason, notes)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        PaymentResponse: Updated payment with refund details

    Raises:
        NotFoundException: If payment not found
        ValidationException: If payment cannot be refunded (not completed, already refunded, etc.)
        PermissionDeniedException: If user doesn't own the payment

    Rate Limit:
        20 requests per minute

    Authorization:
        Users can only refund their own payments

    Requires:
        Bearer token in Authorization header

    Example Request:
        {
            "amount": null,  // null for full refund, or specific amount
            "reason": "Event cancelled",
            "notes": {"refund_reason": "user_request"}
        }
    """
    service: PaymentService = PaymentService(db)
    payment: PaymentResponse = service.create_refund(
        payment_id=payment_id,
        user_id=current_user.id,
        amount=refund_data.amount,
        reason=refund_data.reason,
        notes=refund_data.notes
    )
    return payment
