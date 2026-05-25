"""
Rewards API Endpoints
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.rewards.services.reward_service import RewardService
from app.modules.rewards.domain.value_objects import ShippingAddress
from app.modules.rewards.schemas.reward import (
    RewardOrderCreate,
    RewardResponse,
    RewardStatusUpdate,
)

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.post("", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
def create_reward_order(
    reward_data: RewardOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a physical reward order

    Business Rules:
    1. Registration must exist and belong to user
    2. One reward per registration
    3. Valid shipping address required

    Process:
    - Creates UserReward record
    - Initiates Shiprocket order (future)
    - Sends confirmation email
    """
    service = RewardService(db)

    # Convert Pydantic model to value object
    shipping_address = ShippingAddress(
        name=reward_data.shipping_address.name,
        address_line1=reward_data.shipping_address.address_line1,
        address_line2=reward_data.shipping_address.address_line2,
        city=reward_data.shipping_address.city,
        state=reward_data.shipping_address.state,
        pincode=reward_data.shipping_address.pincode,
        phone=reward_data.shipping_address.phone,
    )

    reward = service.create_reward_order(
        registration_id=reward_data.registration_id,
        reward_name=reward_data.reward_name,
        shipping_address=shipping_address
    )

    return RewardResponse.model_validate(reward)


@router.get("/my", response_model=List[RewardResponse])
def get_my_rewards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all physical rewards for current user

    Returns list of reward orders with delivery status
    """
    service = RewardService(db)
    rewards = service.get_user_rewards(user_id=current_user.id)
    return [RewardResponse.model_validate(reward) for reward in rewards]


@router.get("/{reward_id}", response_model=RewardResponse)
def get_reward(
    reward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific reward details

    Includes:
    - Delivery status
    - Tracking number
    - Shiprocket order ID
    """
    from app.models.user_reward import UserReward
    from app.core.exceptions import NotFoundException, PermissionDeniedException

    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise NotFoundException("Reward", str(reward_id))

    if reward.user_id != current_user.id:
        raise PermissionDeniedException("You can only view your own rewards")

    return RewardResponse.model_validate(reward)


@router.patch("/{reward_id}/status", response_model=RewardResponse)
def update_reward_status(
    reward_id: int,
    status_data: RewardStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update reward delivery status (Admin only)

    Updates:
    - Delivery status
    - Tracking number
    - Shiprocket order ID
    """
    # TODO: Add admin permission check
    service = RewardService(db)

    reward = service.update_shipment_status(
        reward_id=reward_id,
        status=status_data.status,
        tracking_number=status_data.tracking_number,
        shiprocket_order_id=status_data.shiprocket_order_id
    )

    return RewardResponse.model_validate(reward)


@router.get("/pending/all", response_model=List[RewardResponse])
def get_pending_rewards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending reward orders (Admin only)

    Returns rewards that need processing/shipment
    """
    # TODO: Add admin permission check
    service = RewardService(db)
    rewards = service.get_pending_rewards()
    return [RewardResponse.model_validate(reward) for reward in rewards]
