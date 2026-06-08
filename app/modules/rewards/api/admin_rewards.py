"""
Admin Rewards API Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.modules.rewards.schemas.reward import (
    ManualShipmentDetails,
    RewardResponse,
    RewardWithDetails,
    ShippingPreviewResponse,
    ShiprocketShipmentResponse,
)
from app.modules.rewards.services.reward_service import RewardService

router = APIRouter(prefix="/admin/rewards", tags=["admin-rewards"])


@router.post(
    "/events/{event_id}/users/{user_id}/registrations/{registration_id}/unlock",
    response_model=RewardResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_unlock_reward(
    event_id: int,
    user_id: int,
    registration_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin unlocks a physical reward for a user.

    This creates a UserReward record in 'pending_details' status,
    allowing the user to claim it and provide shipping details.

    Business Rules:
    1. Admin only endpoint
    2. Registration must exist and match event_id/user_id
    3. One reward per registration
    4. Reward created in 'pending_details' status (user must provide shipping address)

    Process:
    - Creates UserReward record with status='pending_details'
    - User can then claim and provide shipping details
    - After shipping details provided, status changes to 'pending_shipment'
    """
    service = RewardService(db)

    reward = service.admin_unlock_reward(
        event_id=event_id,
        user_id=user_id,
        registration_id=registration_id,
    )

    return RewardResponse.model_validate(reward)


@router.get("/all", response_model=list[RewardWithDetails])
def get_all_rewards(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get all rewards for admin dashboard with filtering.

    Query parameters:
    - status_filter: Filter by reward status (pending_details, pending_shipment, shipped, delivered)
    - search: Search by user name, email, or tracking number

    Returns:
    - List of rewards with full details (user, event, registration, shipping, progress)
    """
    service = RewardService(db)
    rewards = service.get_all_rewards_with_details(
        status_filter=status_filter,
        search=search,
    )
    return rewards


@router.get("/{reward_id}/shipping-preview", response_model=ShippingPreviewResponse)
async def get_shipping_preview(
    reward_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get shipping preview with estimated costs before creating order.

    Shows:
    - Package dimensions and weight
    - Shipping address and phone
    - Pickup location
    - Available couriers with rates and ETD
    - Serviceability status

    This allows admin to review all details before confirming shipment.
    """
    service = RewardService(db)
    preview = await service.get_shipping_preview(reward_id=reward_id)
    return preview


@router.post("/{reward_id}/ship-with-shiprocket", response_model=ShiprocketShipmentResponse)
async def ship_reward_with_shiprocket(
    reward_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Automatically create Shiprocket order and ship reward.

    Process:
    1. Validates reward exists and has shipping address
    2. Gets ShiprocketFulfillmentService
    3. Creates Shiprocket order with default dimensions (15x10x5, 0.5kg)
    4. Assigns AWB tracking number
    5. Generates shipping label PDF
    6. Schedules pickup with cheapest courier
    7. Updates reward status to 'shipped'

    Returns:
    - Tracking details, label URL, courier info
    """
    service = RewardService(db)
    result = await service.ship_reward_with_shiprocket(reward_id=reward_id)
    return result


@router.post("/{reward_id}/ship", response_model=RewardResponse)
def ship_reward_manually(
    reward_id: int,
    shipment_details: ManualShipmentDetails,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Mark reward as shipped with manually entered tracking details.

    Used when admin ships via external courier (not Shiprocket).

    Body:
    - tracking_number: Tracking/AWB number
    - courier_partner: Name of courier company
    - shipped_at: Optional timestamp (defaults to now)

    Returns:
    - Updated reward details
    """
    service = RewardService(db)
    reward = service.ship_reward_manually(
        reward_id=reward_id,
        tracking_number=shipment_details.tracking_number,
        courier_partner=shipment_details.courier_partner,
        shipped_at=shipment_details.shipped_at,
    )
    return RewardResponse.model_validate(reward)


@router.post("/{reward_id}/mark-delivered", response_model=RewardResponse)
def mark_reward_delivered(
    reward_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Manually mark reward as delivered.

    Used for manual confirmation when Shiprocket webhook doesn't update
    or for non-Shiprocket shipments.

    Returns:
    - Updated reward details with delivered status
    """
    service = RewardService(db)
    reward = service.mark_reward_delivered(reward_id=reward_id)
    return RewardResponse.model_validate(reward)
