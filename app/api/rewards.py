"""
Rewards API Endpoints
Handles reward tracking, claiming, shipping, and delivery
Version: 2.0 - Fixed enum value handling
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
import uuid
import uuid as uuid_pkg

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.models.event import Event
from app.models.user_reward import UserReward, RewardStatus, RewardType
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.schemas.reward import (
    UserRewardResponse,
    UserRewardListResponse,
    ClaimRewardRequest,
    UpdateShippingDetailsRequest,
    ShipRewardRequest,
    ChallengeRewardsResponse,
    RewardDefinition,
    AdminRewardListResponse,
    AdminRewardResponse,
    RewardStatsResponse,
    TrackingInfo,
)
from app.services.shiprocket_service import ShiprocketService, ShippingAddress
from app.modules.registrations.domain.registration import Registration

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


# ============================================================================
# Helper Functions
# ============================================================================

def _build_admin_goodie_response(reward: UserReward) -> AdminRewardResponse:
    """
    Helper function to convert UserReward to AdminRewardResponse.
    Maps field names from UserReward model to AdminRewardResponse schema.
    """
    reward_dict = reward.to_dict()
    return AdminRewardResponse(
        id=reward_dict["id"],
        user_id=reward_dict["user_id"],
        challenge_id=reward_dict["challenge_id"],  # Already mapped in to_dict()
        reward_id=reward_dict["reward_id"],  # reward_id -> reward_id
        reward_name=reward_dict["reward_name"],  # reward_name -> goodie_name
        reward_description=reward_dict["reward_description"],  # reward_description -> goodie_description
        reward_type=reward_dict["reward_type"],  # reward_type -> goodie_type
        reward_image_url=reward_dict["reward_image_url"],  # reward_image_url -> goodie_image_url
        requires_shipping=reward_dict["requires_shipping"],
        status=reward_dict["status"],
        shipping_details=reward_dict["shipping_details"],
        tracking_info={
            "tracking_number": reward_dict["tracking_number"],
            "courier_partner": reward_dict["courier_partner"],
            "tracking_url": reward_dict["tracking_url"],
            "current_status": reward_dict["status"],
        } if reward_dict["tracking_number"] else None,
        awarded_at=reward.awarded_at,
        claimed_at=reward.claimed_at,
        shipped_at=reward.shipped_at,
        delivered_at=reward.delivered_at,
        created_at=reward.created_at,
        updated_at=reward.updated_at,
        challenge_name=reward.event.name if reward.event else None,
        challenge_banner_image_url=reward.event.banner_image_url if reward.event else None,
        user_email=reward.user.email if reward.user else None,
        user_name=reward.user.full_name if reward.user else None,
        user_phone=reward.user.phone if reward.user else None,
        shiprocket_order_id=int(reward_dict["shiprocket_order_id"]) if reward_dict["shiprocket_order_id"] else None,
        shiprocket_shipment_id=int(reward_dict["shiprocket_shipment_id"]) if reward_dict["shiprocket_shipment_id"] else None,
        admin_notes=reward.admin_notes
    )


# ============================================================================
# User Endpoints - Get and Manage Personal Goodies
# ============================================================================

@router.get("/me", response_model=UserRewardListResponse)
async def get_my_goodies(
    status: Optional[str] = Query(None, description="Filter by status"),
    challenge_id: Optional[int] = Query(None, description="Filter by challenge ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all rewards earned by the current user.

    Query parameters:
    - status: Filter by reward status (pending_details, pending_shipment, shipped, delivered)
    - challenge_id: Filter by specific challenge
    """
    query = db.query(UserReward).filter(UserReward.user_id == current_user.id)

    # Apply filters
    if status:
        try:
            status_enum = RewardStatus(status)
            query = query.filter(UserReward.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    if challenge_id:
        query = query.filter(UserReward.event_id == challenge_id)

    # Eager load relationships
    query = query.options(joinedload(UserReward.event))

    rewards = query.order_by(UserReward.awarded_at.desc()).all()

    # Build response with tracking info
    goodie_responses = []
    shiprocket_service = ShiprocketService()

    for reward in rewards:
        tracking_info = None
        if reward.status == RewardStatus.SHIPPED and reward.tracking_number:
            try:
                tracking_data = await shiprocket_service.track_shipment(reward.tracking_number)
                tracking_info = TrackingInfo(
                    tracking_number=tracking_data.awb,
                    courier_partner=tracking_data.courier_name,
                    current_status=tracking_data.current_status,
                    shipped_date=tracking_data.shipped_date,
                    estimated_delivery_date=tracking_data.estimated_delivery_date,
                    tracking_url=tracking_data.tracking_url
                )
            except Exception:
                # If tracking fails, still return reward without tracking info
                pass

        goodie_responses.append(
            UserRewardResponse(
                **reward.to_dict(),
                challenge_name=reward.event.name if reward.event else None,
                challenge_banner_image_url=reward.event.banner_image_url if reward.event else None,
                tracking_info=tracking_info
            )
        )

    # Count by status
    status_counts = db.query(
        UserReward.status, func.count(UserReward.id)
    ).filter(
        UserReward.user_id == current_user.id
    ).group_by(UserReward.status).all()

    counts = {s.value: 0 for s in RewardStatus}
    for status_val, count in status_counts:
        counts[status_val.value] = count

    return UserRewardListResponse(
        rewards=goodie_responses,
        total=len(rewards),
        pending_details_count=counts.get("pending_details", 0),
        pending_shipment_count=counts.get("pending_shipment", 0),
        shipped_count=counts.get("shipped", 0),
        delivered_count=counts.get("delivered", 0)
    )


@router.get("/me/{reward_id}", response_model=UserRewardResponse)
async def get_my_goodie(
    reward_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific reward owned by the current user"""
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.event)
    ).filter(
        UserReward.id == goodie_uuid,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Get tracking info if shipped
    tracking_info = None
    if reward.status == RewardStatus.SHIPPED and reward.tracking_number:
        try:
            shiprocket_service = ShiprocketService()
            tracking_data = await shiprocket_service.track_shipment(reward.tracking_number)
            tracking_info = TrackingInfo(
                tracking_number=tracking_data.awb,
                courier_partner=tracking_data.courier_name,
                current_status=tracking_data.current_status,
                shipped_date=tracking_data.shipped_date,
                estimated_delivery_date=tracking_data.estimated_delivery_date,
                tracking_url=tracking_data.tracking_url
            )
        except Exception:
            pass

    return UserRewardResponse(
        **reward.to_dict(),
        challenge_name=reward.event.name if reward.event else None,
        challenge_banner_image_url=reward.event.banner_image_url if reward.event else None,
        tracking_info=tracking_info
    )


@router.post("/me/{reward_id}/claim", response_model=UserRewardResponse)
async def claim_goodie(
    reward_id: str,
    request: ClaimRewardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Claim a reward by providing shipping details.
    Only works for rewards in 'pending_details' status.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).filter(
        UserReward.id == goodie_uuid,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status != RewardStatus.PENDING_DETAILS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot claim reward in '{reward.status}' status"
        )

    # Update shipping details and status
    reward.shipping_details = request.shipping_details.dict()
    reward.status = RewardStatus.PENDING_SHIPMENT
    reward.claimed_at = datetime.utcnow()

    db.commit()
    db.refresh(reward)

    return UserRewardResponse(**reward.to_dict())


@router.put("/me/{reward_id}/update-details", response_model=UserRewardResponse)
async def update_shipping_details(
    reward_id: str,
    request: UpdateShippingDetailsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update shipping details for a reward.
    Can only update if not yet shipped.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).filter(
        UserReward.id == goodie_uuid,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status in [RewardStatus.SHIPPED, RewardStatus.DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update shipping details for rewards that are already shipped"
        )

    # Update shipping details
    reward.shipping_details = request.shipping_details.dict()

    db.commit()
    db.refresh(reward)

    return UserRewardResponse(**reward.to_dict())


# ============================================================================
# Challenge Rewards - Get Available Rewards for Challenges
# ============================================================================

@router.get("/challenges/{challenge_id}", response_model=ChallengeRewardsResponse)
async def get_challenge_goodies(
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """Get all rewards available for a specific challenge"""
    challenge = db.query(Event).filter(Event.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    rewards = challenge.rewards or []
    goodie_definitions = [RewardDefinition(**g) for g in rewards]

    return ChallengeRewardsResponse(
        challenge_id=challenge.id,
        challenge_name=challenge.name,
        rewards=goodie_definitions
    )


# ============================================================================
# Admin Endpoints - Manage All Goodies
# ============================================================================

@router.get("/admin/all", response_model=AdminRewardListResponse, dependencies=[Depends(require_admin)])
async def admin_get_all_goodies(
    status: Optional[str] = Query(None, description="Filter by status"),
    challenge_id: Optional[int] = Query(None, description="Filter by challenge"),
    search: Optional[str] = Query(None, description="Search by user name or email"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Admin: Get all rewards with filters.
    Supports pagination and search.
    """
    query = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    )

    # Apply filters
    if status:
        try:
            status_enum = RewardStatus(status)
            query = query.filter(UserReward.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    if challenge_id:
        query = query.filter(UserReward.event_id == challenge_id)

    if search:
        search_term = f"%{search}%"
        query = query.join(UserReward.user).filter(
            or_(
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    rewards = query.order_by(UserReward.awarded_at.desc()).offset(offset).limit(limit).all()

    # Build response
    goodie_responses = []
    for reward in rewards:
        goodie_responses.append(_build_admin_goodie_response(reward))

    # Get status counts
    status_counts = db.query(
        UserReward.status, func.count(UserReward.id)
    ).group_by(UserReward.status).all()

    filters = {s.value: 0 for s in RewardStatus}
    for status_val, count in status_counts:
        filters[status_val.value] = count

    return AdminRewardListResponse(
        rewards=goodie_responses,
        total=total,
        filters=filters
    )


@router.post("/admin/{reward_id}/ship-with-shiprocket", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_ship_with_shiprocket(
    reward_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin: Automatically create Shiprocket order and ship reward.
    Uses shipping address from registration.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    # Fetch reward with all relationships
    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event),
        joinedload(UserReward.registration)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status != RewardStatus.PENDING_SHIPMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot ship reward in '{reward.status}' status. Must be 'pending_shipment'."
        )

    if not reward.registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found for this reward"
        )

    registration = reward.registration

    # Validate shipping address exists
    if not registration.shipping_address_line1 or not registration.shipping_city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipping address not provided in registration. Please update registration or use manual shipping."
        )

    # Build shipping address from registration
    shipping_address = ShippingAddress(
        name=registration.participant_name,
        address_line1=registration.shipping_address_line1,
        address_line2=registration.shipping_address_line2 or "",
        city=registration.shipping_city,
        state=registration.shipping_state,
        postal_code=registration.shipping_postal_code,
        country=registration.shipping_country or "India",
        phone=registration.shipping_phone,
        email=registration.shipping_email or reward.user.email if reward.user else ""
    )

    # Create Shiprocket order
    shiprocket_service = ShiprocketService()
    try:
        await shiprocket_service.authenticate()
        shipment_response = await shiprocket_service.create_order(
            user_id=str(reward.user_id),
            challenge_id=str(reward.event_id),
            reward_name=reward.reward_name,
            shipping_address=shipping_address
        )

        # Update reward with Shiprocket details
        reward.status = RewardStatus.SHIPPED
        reward.tracking_number = shipment_response.awb_code
        reward.courier_partner = shipment_response.courier_name
        reward.shiprocket_order_id = shipment_response.order_id
        reward.shiprocket_shipment_id = shipment_response.shipment_id
        reward.shipped_at = datetime.utcnow()

        db.commit()
        db.refresh(reward)

        return _build_admin_goodie_response(reward)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Shiprocket order: {str(e)}"
        )


@router.post("/admin/{reward_id}/ship", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_ship_goodie(
    reward_id: str,
    request: ShipRewardRequest,
    db: Session = Depends(get_db)
):
    """
    Admin: Mark a reward as shipped with tracking information (Manual entry).
    Use this when shipping via your own courier or entering tracking details manually.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status != RewardStatus.PENDING_SHIPMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot ship reward in '{reward.status}' status. Must be 'pending_shipment'."
        )

    # Update shipping info
    reward.status = RewardStatus.SHIPPED
    reward.tracking_number = request.tracking_number
    reward.courier_partner = request.courier_partner
    reward.estimated_delivery_date = request.estimated_delivery_date
    reward.shiprocket_order_id = request.shiprocket_order_id
    reward.shiprocket_shipment_id = request.shiprocket_shipment_id
    reward.admin_notes = request.admin_notes
    reward.shipped_at = datetime.utcnow()

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.post("/admin/{reward_id}/deliver", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_mark_delivered(
    reward_id: str,
    db: Session = Depends(get_db)
):
    """Admin: Mark a reward as delivered"""
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status != RewardStatus.SHIPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only mark shipped rewards as delivered"
        )

    reward.status = RewardStatus.DELIVERED
    reward.delivered_at = datetime.utcnow()

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.post("/admin/{reward_id}/cancel", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_cancel_goodie(
    reward_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    db: Session = Depends(get_db)
):
    """Admin: Cancel a reward"""
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.status in [RewardStatus.DELIVERED, RewardStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel reward in '{reward.status}' status"
        )

    reward.status = RewardStatus.CANCELLED
    reward.cancelled_at = datetime.utcnow()
    if reason:
        reward.admin_notes = f"Cancelled: {reason}"

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.get("/admin/stats", response_model=RewardStatsResponse, dependencies=[Depends(require_admin)])
async def admin_get_goodie_stats(db: Session = Depends(get_db)):
    """Admin: Get overall reward statistics"""

    # Count by status
    status_counts = db.query(
        UserReward.status, func.count(UserReward.id)
    ).group_by(UserReward.status).all()

    counts = {s.value: 0 for s in RewardStatus}
    for status_val, count in status_counts:
        counts[status_val.value] = count

    # Total rewards
    total = sum(counts.values())

    # Unique users with rewards
    unique_users = db.query(func.count(func.distinct(UserReward.user_id))).scalar()

    return RewardStatsResponse(
        total_goodies=total,
        pending_details=counts.get("pending_details", 0),
        pending_shipment=counts.get("pending_shipment", 0),
        shipped=counts.get("shipped", 0),
        delivered=counts.get("delivered", 0),
        cancelled=counts.get("cancelled", 0),
        total_users_with_goodies=unique_users or 0
    )


@router.post("/admin/{reward_id}/unlock", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_unlock_goodie(
    reward_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Unlock reward section for a user.
    This allows the user to see and claim their reward after completing the challenge.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Unlock the reward
    reward.is_unlocked = 'true'
    reward.unlocked_by_admin_id = current_user.id
    reward.unlocked_at = datetime.utcnow()

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.post("/admin/{reward_id}/verify", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_verify_goodie(
    reward_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Verify reward after user provides shipping details.
    This confirms the shipping information is correct and ready for shipment processing.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    if reward.is_unlocked != 'true':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reward must be unlocked before verification"
        )

    if reward.status != RewardStatus.PENDING_SHIPMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only verify rewards in 'pending_shipment' status. Current status: {reward.status}"
        )

    # Verify the reward
    reward.is_verified = 'true'
    reward.verified_by_admin_id = current_user.id
    reward.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.delete("/admin/{reward_id}/unlock", response_model=AdminRewardResponse, dependencies=[Depends(require_admin)])
async def admin_lock_goodie(
    reward_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin: Remove unlock from a reward (lock it again).
    This hides the reward section from the user.
    """
    try:
        goodie_uuid = uuid.UUID(reward_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reward ID format"
        )

    reward = db.query(UserReward).options(
        joinedload(UserReward.user),
        joinedload(UserReward.event)
    ).filter(UserReward.id == goodie_uuid).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Lock the reward
    reward.is_unlocked = 'false'
    reward.is_verified = 'false'
    reward.unlocked_by_admin_id = None
    reward.verified_by_admin_id = None
    reward.unlocked_at = None
    reward.verified_at = None

    db.commit()
    db.refresh(reward)

    return _build_admin_goodie_response(reward)


@router.get("/registration/{registration_id}", response_model=UserRewardListResponse)
async def get_goodies_by_registration(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all rewards for a specific event registration.
    Only returns unlocked rewards for users, admins can see all.
    """
    from app.models.registration import Registration

    # Check if registration exists and belongs to user (or user is admin)
    registration = db.query(Registration).filter(Registration.id == registration_id).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    is_admin = current_user.role in ['admin', 'super_admin']

    if not is_admin and registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view these rewards"
        )

    # Query rewards for this registration's event
    query = db.query(UserReward).filter(
        UserReward.user_id == registration.user_id,
        UserReward.challenge_id == registration.event_id
    )

    # Non-admins can only see unlocked rewards
    if not is_admin:
        query = query.filter(UserReward.is_unlocked == 'true')

    query = query.options(joinedload(UserReward.event))
    rewards = query.order_by(UserReward.awarded_at.desc()).all()

    # Build response with tracking info
    goodie_responses = []
    shiprocket_service = ShiprocketService()

    for reward in rewards:
        tracking_info = None
        if reward.status == RewardStatus.SHIPPED and reward.tracking_number:
            try:
                tracking_data = await shiprocket_service.track_shipment(reward.tracking_number)
                tracking_info = TrackingInfo(
                    tracking_number=tracking_data.awb,
                    courier_partner=tracking_data.courier_name,
                    current_status=tracking_data.current_status,
                    shipped_date=tracking_data.shipped_date,
                    estimated_delivery_date=tracking_data.estimated_delivery_date,
                    tracking_url=tracking_data.tracking_url
                )
            except Exception:
                pass

        goodie_responses.append(
            UserRewardResponse(
                **reward.to_dict(),
                challenge_name=reward.event.name if reward.event else None,
                challenge_banner_image_url=reward.event.banner_image_url if reward.event else None,
                tracking_info=tracking_info
            )
        )

    # Count by status
    status_counts = {}
    for reward in rewards:
        status_val = reward.status.value
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

    return UserRewardListResponse(
        rewards=goodie_responses,
        total=len(rewards),
        pending_details_count=status_counts.get("pending_details", 0),
        pending_shipment_count=status_counts.get("pending_shipment", 0),
        shipped_count=status_counts.get("shipped", 0),
        delivered_count=status_counts.get("delivered", 0)
    )


# ============================================================================
# Admin Endpoints - Reward Management from Participants Table
# ============================================================================

@router.post("/admin/events/{event_id}/users/{user_id}/create-reward", dependencies=[Depends(require_admin)])
async def admin_create_reward_for_user(
    event_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Create and unlock reward for a user who completed the challenge.
    Called from Participants & Progress table when admin clicks "Unlock Reward".

    This endpoint:
    1. Creates a UserReward record if it doesn't exist
    2. Sets is_unlocked = True
    3. Sets unlocked_by_admin_id and unlocked_at
    4. Returns reward details
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Verify user exists and has registration for this event
    from app.models.registration import Registration
    registration = db.query(Registration).filter(
        Registration.user_id == user_id,
        Registration.event_id == event_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not registered for event {event_id}"
        )

    # Check if user has completed the challenge (100% progress)
    from app.models.activity_progress import ActivityProgress
    progress = db.query(ActivityProgress).filter(
        ActivityProgress.registration_id == registration.id
    ).first()

    if not progress or not progress.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has not completed the challenge yet"
        )

    # Check if reward already exists
    existing_reward = db.query(UserReward).filter(
        UserReward.user_id == user_id,
        UserReward.event_id == event_id
    ).first()

    if existing_reward:
        # Reward exists, just unlock it if not already unlocked
        if not existing_reward.is_unlocked:
            existing_reward.is_unlocked = True
            existing_reward.unlocked_by_admin_id = current_user.id
            existing_reward.unlocked_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_reward)

        return {
            "success": True,
            "message": "Reward unlocked successfully",
            "reward_id": str(existing_reward.id),
            "reward_name": existing_reward.reward_name,
            "status": existing_reward.status.value,
            "is_unlocked": existing_reward.is_unlocked
        }

    # Create new reward
    # Get tier rewards from registration tier
    tier_rewards = []
    if registration.current_tier_id:
        tier = db.query(EventRegistrationTier).filter(
            EventRegistrationTier.id == registration.current_tier_id
        ).first()
        if tier and tier.rewards:
            tier_rewards = tier.rewards

    # Default reward if no tier rewards defined
    reward_name = f"{event.name} - Finisher Medal"
    reward_description = f"Congratulations on completing the {event.name} challenge!"

    # If tier has rewards, use the first one
    if tier_rewards and len(tier_rewards) > 0:
        first_reward = tier_rewards[0] if isinstance(tier_rewards, list) else tier_rewards
        if isinstance(first_reward, dict):
            reward_name = first_reward.get('name', reward_name)
            reward_description = first_reward.get('description', reward_description)
        elif isinstance(first_reward, str):
            reward_name = first_reward

    new_reward = UserReward(
        id=uuid_pkg.uuid4(),
        user_id=user_id,
        event_id=event_id,
        registration_id=registration.id,
        reward_id=f"reward_{event_id}_{user_id}",
        reward_name=reward_name,
        reward_description=reward_description,
        reward_type=str(RewardType.MEDAL.value),  # Explicit string conversion
        requires_shipping=True,
        status=str(RewardStatus.PENDING_SHIPMENT.value),  # Skip claim step, admin ships directly
        is_unlocked=True,
        is_verified=True,  # Admin verified by unlocking
        unlocked_by_admin_id=current_user.id,
        verified_by_admin_id=current_user.id,  # Same admin who unlocked
        unlocked_at=datetime.utcnow(),
        verified_at=datetime.utcnow(),
        awarded_at=datetime.utcnow()
    )

    db.add(new_reward)
    db.commit()
    db.refresh(new_reward)

    return {
        "success": True,
        "message": "Reward created and unlocked successfully",
        "reward_id": str(new_reward.id),
        "reward_name": new_reward.reward_name,
        "status": new_reward.status.value,
        "is_unlocked": new_reward.is_unlocked
    }


@router.get("/admin/events/{event_id}/users/{user_id}/reward-status")
async def get_user_reward_status(
    event_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reward status for a specific user in an event.
    Used by Participants & Progress table to show reward column.

    Returns:
    - exists: bool - whether reward exists
    - is_unlocked: bool - whether user can see/claim it
    - status: str - reward status
    - reward_id: uuid - reward ID if exists
    - can_unlock: bool - whether admin can unlock (user completed challenge)
    """
    # Check if user completed the challenge
    from app.models.registration import Registration
    from app.models.activity_progress import ActivityProgress

    registration = db.query(Registration).filter(
        Registration.user_id == user_id,
        Registration.event_id == event_id
    ).first()

    if not registration:
        return {
            "exists": False,
            "is_unlocked": False,
            "status": None,
            "reward_id": None,
            "can_unlock": False,
            "message": "User not registered"
        }

    progress = db.query(ActivityProgress).filter(
        ActivityProgress.registration_id == registration.id
    ).first()

    can_unlock = progress and progress.is_completed

    # Check if reward exists
    reward = db.query(UserReward).filter(
        UserReward.user_id == user_id,
        UserReward.event_id == event_id
    ).first()

    if not reward:
        return {
            "exists": False,
            "is_unlocked": False,
            "status": None,
            "reward_id": None,
            "can_unlock": can_unlock,
            "message": "No reward created" if can_unlock else "Challenge not completed"
        }

    return {
        "exists": True,
        "is_unlocked": reward.is_unlocked,
        "status": reward.status.value,
        "reward_id": str(reward.id),
        "can_unlock": can_unlock,
        "shipping_details_provided": reward.shipping_details is not None,
        "tracking_number": reward.tracking_number,
        "courier_partner": reward.courier_partner
    }
