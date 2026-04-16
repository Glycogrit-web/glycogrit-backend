"""
Payment API Endpoints
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse
from app.models.user import User
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/registrations/{registration_id}/payment", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    registration_id: int,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate a payment for a registration

    Users can only initiate payments for their own registrations.

    - **registration_id**: Registration ID
    - **amount**: Payment amount
    - **payment_method**: Payment method (credit_card, upi, net_banking, etc.)
    - **currency**: Currency code (default: INR)

    Requires: Bearer token in Authorization header
    """
    service = PaymentService(db)
    payment = service.initiate_payment(
        registration_id=registration_id,
        user_id=current_user.id,
        amount=float(payment_data.amount),
        payment_method=payment_data.payment_method,
        currency=payment_data.currency
    )
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get payment details by ID

    Users can only view their own payments.

    - **payment_id**: Payment ID

    Requires: Bearer token in Authorization header
    """
    service = PaymentService(db)
    payment = service.get_payment_by_id(payment_id)

    # Check ownership
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(payment.user_id, current_user.id, "payment")

    return payment


@router.put("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: int,
    payment_data: PaymentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update payment status

    This endpoint is typically used by payment gateway webhooks or admin users.
    Users can view the updated status but cannot directly modify it.

    - **payment_id**: Payment ID
    - **status**: New payment status (pending, completed, failed, refunded)
    - **transaction_id**: Transaction ID from payment gateway
    - **gateway_reference**: Gateway reference number
    - **gateway_name**: Payment gateway name

    Requires: Bearer token in Authorization header
    """
    service = PaymentService(db)
    payment = service.get_payment_by_id(payment_id)

    # Check ownership - only payment owner can update status
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(payment.user_id, current_user.id, "payment")

    updated_payment = service.update_payment_status(
        payment_id=payment_id,
        status=payment_data.status,
        transaction_id=payment_data.transaction_id,
        gateway_reference=payment_data.gateway_reference,
        gateway_name=payment_data.gateway_name
    )
    return updated_payment


@router.get("/users/{user_id}/payments", response_model=list[PaymentResponse])
async def get_user_payments(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get all payments for a user

    Users can only view their own payments.

    - **user_id**: User ID
    - **skip**: Number of records to skip (offset)
    - **limit**: Maximum number of records to return

    Requires: Bearer token in Authorization header
    """
    service = PaymentService(db)
    payments = service.get_payments_by_user(user_id, current_user.id, skip, limit)
    return payments


@router.get("/registrations/{registration_id}/payments", response_model=list[PaymentResponse])
async def get_registration_payments(
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all payments for a registration

    Users can only view payments for their own registrations.

    - **registration_id**: Registration ID

    Requires: Bearer token in Authorization header
    """
    service = PaymentService(db)
    payments = service.get_payments_by_registration(registration_id, current_user.id)
    return payments
