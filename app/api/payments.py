"""
Payment API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse
from app.models.user import User
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/registrations/{registration_id}/payment", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def initiate_payment(
    request: Request,
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
