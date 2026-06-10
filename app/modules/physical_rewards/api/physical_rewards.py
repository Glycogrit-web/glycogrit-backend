"""
User Physical Reward Endpoints
For viewing rewards and tracking orders
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.enums import RewardStatus
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.models.user_reward import UserReward
from app.modules.physical_rewards.schemas.physical_reward_schemas import (
    PhysicalRewardResponse,
    UserTrackingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/physical-rewards",
    tags=["Physical Rewards"],
)


@router.get("/my-rewards")
@limiter.limit(RateLimits.DEFAULT)
async def get_my_physical_rewards(
    request: Request,
    response: Response,
    event_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get my physical rewards

    Returns list of user's physical rewards with status and tracking info.

    Args:
        event_id: Optional filter by event
        status_filter: Optional filter by status
        current_user: Authenticated user
        db: Database session

    Returns:
        List of physical rewards
    """
    # Build query
    query = db.query(UserReward).filter(
        UserReward.user_id == current_user.id,
        UserReward.requires_shipping == True
    )

    if event_id:
        query = query.filter(UserReward.event_id == event_id)

    if status_filter:
        try:
            reward_status = RewardStatus(status_filter)
            query = query.filter(UserReward.status == reward_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}"
            )

    rewards = query.order_by(UserReward.created_at.desc()).all()

    # Build response
    rewards_data = []
    for reward in rewards:
        rewards_data.append({
            "id": str(reward.id),
            "user_id": reward.user_id,
            "event_id": reward.event_id,
            "event_name": reward.event.name if reward.event else None,
            "reward_name": reward.reward_name,
            "reward_type": reward.reward_type.value,
            "reward_description": reward.reward_description,
            "reward_image_url": reward.reward_image_url,
            "status": reward.status.value,
            "is_unlocked": reward.is_unlocked,
            "tracking_visible_to_user": reward.tracking_visible_to_user,
            # Only show tracking if visible
            "has_tracking": reward.manual_tracking_id is not None and reward.tracking_visible_to_user,
            "unlocked_at": reward.unlocked_at.isoformat() if reward.unlocked_at else None,
            "created_at": reward.created_at.isoformat(),
            "updated_at": reward.updated_at.isoformat(),
        })

    return {
        "rewards": rewards_data,
        "total": len(rewards_data)
    }


@router.get("/{reward_id}")
@limiter.limit(RateLimits.DEFAULT)
async def get_reward_details(
    request: Request,
    response: Response,
    reward_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get reward details

    Returns detailed information about a specific reward.
    Shows tracking info only if tracking_visible_to_user = True.

    Args:
        reward_id: Reward ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Reward details
    """
    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Check ownership (or admin)
    if reward.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this reward"
        )

    # Build response
    response_data = {
        "id": str(reward.id),
        "user_id": reward.user_id,
        "event_id": reward.event_id,
        "event_name": reward.event.name if reward.event else None,
        "reward_name": reward.reward_name,
        "reward_type": reward.reward_type.value,
        "reward_description": reward.reward_description,
        "reward_image_url": reward.reward_image_url,
        "status": reward.status.value,
        "is_unlocked": reward.is_unlocked,
        "tracking_visible_to_user": reward.tracking_visible_to_user,
        "unlocked_at": reward.unlocked_at.isoformat() if reward.unlocked_at else None,
        "created_at": reward.created_at.isoformat(),
        "updated_at": reward.updated_at.isoformat(),
    }

    # Include tracking info only if visible
    if reward.tracking_visible_to_user and reward.manual_tracking_id:
        response_data["tracking"] = {
            "tracking_id": reward.manual_tracking_id,
            "tracking_url": reward.manual_tracking_url,
            "courier_name": reward.manual_courier_name,
            "order_reference": reward.manual_order_reference,
        }

    return response_data


@router.get("/{reward_id}/track", response_model=UserTrackingResponse)
@limiter.limit(RateLimits.DEFAULT)
async def track_reward(
    request: Request,
    response: Response,
    reward_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Track reward shipment

    Returns tracking information for user to track their physical reward.

    Validation:
    - User must own reward or be admin
    - Reward status must be TRACKING_ORDER
    - tracking_visible_to_user must be True
    - Tracking data must exist

    Args:
        reward_id: Reward ID
        current_user: Authenticated user
        db: Database session

    Returns:
        UserTrackingResponse with tracking details

    Raises:
        404: Reward not found or doesn't belong to user
        400: Tracking not yet available
        403: Tracking hidden by admin
    """
    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Check ownership (or admin)
    if reward.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to track this reward"
        )

    # Check if tracking is available
    if not reward.manual_tracking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracking information not yet available. Please check back later."
        )

    # Check if tracking is visible (unless admin)
    if not reward.tracking_visible_to_user and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tracking information is currently hidden. Please contact support."
        )

    # Check status
    if reward.status not in [RewardStatus.TRACKING_ORDER, RewardStatus.DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reward is not yet shipped. Current status: {reward.status.value}"
        )

    logger.info(f"📍 User {current_user.id} tracking reward {reward_id}")

    return UserTrackingResponse(
        reward_id=reward.id,
        reward_name=reward.reward_name,
        reward_type=reward.reward_type.value,
        status=reward.status.value,
        tracking_id=reward.manual_tracking_id,
        tracking_url=reward.manual_tracking_url,
        courier_name=reward.manual_courier_name,
        estimated_delivery_date=reward.estimated_delivery_date,
        current_location=reward.current_location,
        last_updated=reward.tracking_imported_at
    )
