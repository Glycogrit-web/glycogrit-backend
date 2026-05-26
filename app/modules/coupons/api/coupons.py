"""
Coupon API Endpoints - REST API for coupon management and validation
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import NotFoundException, ValidationException
from app.core.rate_limit import limiter
from app.models.user import User
from app.modules.coupons.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["coupons"])
logger = logging.getLogger(__name__)


@router.post("/validate", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")  # Rate limiting to prevent coupon fishing
async def validate_coupon(
    request: Request,
    coupon_code: str,
    event_id: int,
    tier_id: int | None = None,
    amount: float = 0.0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Validate a coupon code and calculate discount.

    This endpoint is PUBLIC (requires authentication but any user can call).
    Used by frontend to validate coupons before payment.

    SECURITY:
    - Rate limited to prevent coupon code enumeration attacks
    - Server-side validation only
    - Row-level locking not used here (non-destructive operation)

    Args:
        coupon_code: Coupon code to validate
        event_id: Event ID for registration
        tier_id: Optional tier ID
        amount: Purchase amount

    Returns:
        Validation result with discount details
    """
    try:
        service = CouponService(db)

        # Validate and calculate discount
        coupon, discount_amount = service.validate_and_calculate_discount(
            coupon_code=coupon_code,
            user_id=current_user.id,
            event_id=event_id,
            tier_id=tier_id,
            amount=Decimal(str(amount)),
        )

        final_amount = max(Decimal(str(amount)) - discount_amount, Decimal("0"))

        return {
            "valid": True,
            "coupon": {
                "code": coupon.code,
                "description": coupon.description,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
            },
            "discount_amount": float(discount_amount),
            "original_amount": float(amount),
            "final_amount": float(final_amount),
            "redemptions_remaining": coupon.redemptions_remaining,
            "message": f"Coupon applied! You save ₹{discount_amount}",
        }

    except ValidationException as e:
        # Return validation errors with details
        return {
            "valid": False,
            "error": str(e),
            "error_code": e.error_code if hasattr(e, "error_code") else "validation_error",
        }
    except NotFoundException:
        return {"valid": False, "error": "Invalid coupon code", "error_code": "coupon_not_found"}
    except Exception as e:
        logger.error(f"Coupon validation error: {str(e)}", exc_info=True)
        return {
            "valid": False,
            "error": "An error occurred while validating the coupon",
            "error_code": "internal_error",
        }


@router.get("/check-eligibility", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def check_coupon_eligibility(
    request: Request,
    coupon_code: str,
    event_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Quick eligibility check for a coupon (without full validation).

    Useful for displaying coupon info to user before they enter payment flow.

    Args:
        coupon_code: Coupon code to check
        event_id: Optional event ID for restriction check

    Returns:
        Eligibility status and coupon details
    """
    service = CouponService(db)
    result = service.check_coupon_eligibility(
        coupon_code=coupon_code, user_id=current_user.id, event_id=event_id
    )
    return result


@router.get("/my-usage", status_code=status.HTTP_200_OK)
async def get_my_coupon_usage(
    coupon_code: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's coupon usage history.

    Args:
        coupon_code: Optional filter by specific coupon

    Returns:
        List of coupon usage records
    """
    service = CouponService(db)
    usage_records = service.get_user_coupon_usage(user_id=current_user.id, coupon_code=coupon_code)

    return {
        "usage_count": len(usage_records),
        "coupons_used": [
            {
                "id": record.id,
                "coupon_code": record.coupon.code,
                "discount_applied": float(record.discount_applied),
                "original_amount": float(record.original_amount),
                "final_amount": float(record.final_amount),
                "used_at": record.used_at.isoformat(),
                "registration_id": record.registration_id,
            }
            for record in usage_records
        ],
    }


# ADMIN-ONLY ENDPOINTS BELOW
# These require admin/organizer permissions


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_coupon(
    request: Request,
    code: str,
    discount_type: str,
    discount_value: float,
    description: str | None = None,
    max_discount_amount: float | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    max_redemptions: int | None = None,
    max_redemptions_per_user: int = 1,
    event_ids: list | None = None,
    tier_ids: list | None = None,
    min_purchase_amount: float | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new coupon (ADMIN ONLY).

    Args:
        code: Unique coupon code
        discount_type: 'fixed' or 'percentage'
        discount_value: Discount amount or percentage
        ... (other fields)

    Returns:
        Created coupon details
    """
    # TODO: Add admin permission check
    # if current_user.role not in ['admin', 'super_admin']:
    #     raise PermissionDeniedException("Only admins can create coupons")

    from datetime import datetime

    from app.modules.coupons.domain.coupon import Coupon

    # Create coupon
    coupon = Coupon(
        code=code.upper().strip(),
        description=description,
        discount_type=discount_type,
        discount_value=Decimal(str(discount_value)),
        max_discount_amount=Decimal(str(max_discount_amount)) if max_discount_amount else None,
        valid_from=datetime.fromisoformat(valid_from) if valid_from else datetime.utcnow(),
        valid_until=datetime.fromisoformat(valid_until) if valid_until else None,
        max_redemptions=max_redemptions,
        max_redemptions_per_user=max_redemptions_per_user,
        event_restrictions={"event_ids": event_ids} if event_ids else None,
        tier_restrictions={"tier_ids": tier_ids} if tier_ids else None,
        min_purchase_amount=Decimal(str(min_purchase_amount)) if min_purchase_amount else None,
        is_active=True,
        created_by=current_user.id,
    )

    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    logger.info(f"Coupon {coupon.code} created by user {current_user.id}")

    return {
        "id": coupon.id,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": float(coupon.discount_value),
        "is_active": coupon.is_active,
        "created_at": coupon.created_at.isoformat(),
    }


@router.get("/admin/list", status_code=status.HTTP_200_OK)
async def list_coupons_admin(
    is_active: bool | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all coupons (ADMIN ONLY).

    Args:
        is_active: Optional filter by active status

    Returns:
        List of coupons with usage statistics
    """
    # TODO: Add admin permission check

    from app.modules.coupons.domain.coupon import Coupon

    query = db.query(Coupon)

    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)

    coupons = query.order_by(Coupon.created_at.desc()).all()

    return {
        "total": len(coupons),
        "coupons": [
            {
                "id": coupon.id,
                "code": coupon.code,
                "description": coupon.description,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
                "is_active": coupon.is_active,
                "is_valid": coupon.is_valid,
                "is_expired": coupon.is_expired,
                "current_redemptions": coupon.current_redemptions,
                "max_redemptions": coupon.max_redemptions,
                "redemptions_remaining": coupon.redemptions_remaining,
                "valid_from": coupon.valid_from.isoformat(),
                "valid_until": coupon.valid_until.isoformat() if coupon.valid_until else None,
                "created_at": coupon.created_at.isoformat(),
            }
            for coupon in coupons
        ],
    }


@router.patch("/{coupon_id}", status_code=status.HTTP_200_OK)
async def update_coupon(
    coupon_id: int,
    is_active: bool | None = None,
    description: str | None = None,
    valid_until: str | None = None,
    max_redemptions: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a coupon (ADMIN ONLY).

    Limited fields can be updated to prevent breaking existing usage.

    Args:
        coupon_id: Coupon ID
        is_active: Toggle active status
        description: Update description
        valid_until: Update expiry date
        max_redemptions: Update max redemptions

    Returns:
        Updated coupon details
    """
    # TODO: Add admin permission check

    service = CouponService(db)
    coupon = service.get_coupon_by_id(coupon_id)

    if not coupon:
        raise NotFoundException("Coupon", coupon_id)

    # Update allowed fields
    if is_active is not None:
        coupon.is_active = is_active
    if description is not None:
        coupon.description = description
    if valid_until is not None:
        from datetime import datetime

        coupon.valid_until = datetime.fromisoformat(valid_until)
    if max_redemptions is not None:
        # Prevent reducing below current redemptions
        if max_redemptions < coupon.current_redemptions:
            raise ValidationException(
                f"Cannot set max_redemptions to {max_redemptions} "
                f"(already {coupon.current_redemptions} redemptions)"
            )
        coupon.max_redemptions = max_redemptions

    db.commit()
    db.refresh(coupon)

    logger.info(f"Coupon {coupon.code} updated by user {current_user.id}")

    return {
        "id": coupon.id,
        "code": coupon.code,
        "is_active": coupon.is_active,
        "message": "Coupon updated successfully",
    }


@router.delete("/{coupon_id}", status_code=status.HTTP_200_OK)
async def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate a coupon (ADMIN ONLY).

    Does not delete from database (for audit trail), just deactivates.

    Args:
        coupon_id: Coupon ID

    Returns:
        Success message
    """
    # TODO: Add admin permission check

    service = CouponService(db)
    coupon = service.get_coupon_by_id(coupon_id)

    if not coupon:
        raise NotFoundException("Coupon", coupon_id)

    # Deactivate instead of deleting (preserve audit trail)
    coupon.is_active = False
    db.commit()

    logger.info(f"Coupon {coupon.code} deactivated by user {current_user.id}")

    return {"success": True, "message": f"Coupon {coupon.code} has been deactivated"}
