"""
Event Registration Tier API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException, Request, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_optional_current_user
from app.core.rate_limit import limiter, RateLimits
from app.schemas.tier import (
    TierCreate, TierUpdate, TierResponse,
    RegistrationTierCreate, TierUpgradeRequest, TierUpgradeResponse,
    RegistrationTierResponse, EffectiveRewardsResponse
)
from app.models.user import User
from app.models.event import Event
from app.models.event_registration_tier import EventRegistrationTier
from app.models.registration import Registration
from app.services.tier_service import TierService
from app.services.registration_service import RegistrationService
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/v1", tags=["Event Tiers"])


# ===== ADMIN TIER MANAGEMENT ENDPOINTS =====

@router.post("/events/{event_id}/tiers", response_model=TierResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_event_tier(
    request: Request,
    response: Response,
    event_id: int,
    tier_data: TierCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TierResponse:
    """
    Create a new registration tier for an event.

    **Admin/Organizer Only**

    Creates a new pricing tier with rewards, capacity limits, and payment requirements.

    Args:
        event_id: Event ID
        tier_data: Tier creation data (name, price, rewards, etc.)

    Returns:
        TierResponse: Created tier details

    Raises:
        403: If user is not event organizer
        404: If event not found
        400: If validation fails (duplicate slug, invalid price, etc.)
    """
    tier_service = TierService(db)

    try:
        tier = tier_service.create_tier(event_id, tier_data, current_user.id)
        return TierResponse.from_orm_with_computed(tier)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate tier slug or order for this event")


@router.get("/events/{event_id}/tiers", response_model=List[TierResponse])
@limiter.limit(RateLimits.READ_LIST)
async def list_event_tiers(
    request: Request,
    response: Response,
    event_id: int,
    include_inactive: bool = False,
    current_user: User = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> List[TierResponse]:
    """
    Get all registration tiers for an event.

    **Public Endpoint** - Returns only active tiers for non-admins

    Args:
        event_id: Event ID
        include_inactive: Include inactive tiers (admin only)

    Returns:
        List[TierResponse]: List of tiers ordered by tier_order

    Raises:
        404: If event not found
    """
    tier_service = TierService(db)

    # Check if user is admin/organizer to show inactive tiers
    is_admin = current_user and (current_user.role in ['admin', 'super_admin'])
    show_inactive = include_inactive and is_admin

    tiers = tier_service.get_event_tiers(event_id, include_inactive=show_inactive)
    return [TierResponse.from_orm_with_computed(tier) for tier in tiers]


@router.get("/tiers/{tier_id}", response_model=TierResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_tier(
    request: Request,
    response: Response,
    tier_id: int,
    current_user: User = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> TierResponse:
    """
    Get details of a specific tier.

    **Public Endpoint**

    Args:
        tier_id: Tier ID

    Returns:
        TierResponse: Tier details

    Raises:
        404: If tier not found
    """
    tier_service = TierService(db)

    tier = tier_service.get_tier_by_id(tier_id)
    if not tier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tier not found")

    return TierResponse.from_orm_with_computed(tier)


@router.put("/tiers/{tier_id}", response_model=TierResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_tier(
    request: Request,
    response: Response,
    tier_id: int,
    tier_data: TierUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TierResponse:
    """
    Update a registration tier.

    **Admin/Organizer Only**

    Updates tier details. Cannot change tier_id or tier_slug if registrations exist.

    Args:
        tier_id: Tier ID
        tier_data: Updated tier data

    Returns:
        TierResponse: Updated tier details

    Raises:
        403: If user is not event organizer
        404: If tier not found
        400: If update violates constraints
    """
    tier_service = TierService(db)

    try:
        tier = tier_service.update_tier(tier_id, tier_data, current_user.id)
        return TierResponse.from_orm_with_computed(tier)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_tier(
    request: Request,
    response: Response,
    tier_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a registration tier.

    **Admin/Organizer Only**

    Cannot delete tier if registrations exist for it.

    Args:
        tier_id: Tier ID

    Raises:
        403: If user is not event organizer
        404: If tier not found
        400: If tier has registrations
    """
    tier_service = TierService(db)

    try:
        tier_service.delete_tier(tier_id, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ===== USER REGISTRATION ENDPOINTS =====

@router.post("/events/{event_id}/register-tier", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def register_for_event_tier(
    request: Request,
    response: Response,
    event_id: int,
    registration_data: RegistrationTierCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Register for a specific event tier.

    **Authenticated Users Only**

    Creates a tier-based registration. If tier is free or zero-price, auto-confirms.
    If tier requires payment, returns payment order details.

    Args:
        event_id: Event ID
        registration_data: Registration details with tier selection

    Returns:
        dict: Registration details and payment order (if required)

    Raises:
        400: If tier is sold out, inactive, or validation fails
        404: If event or tier not found
    """
    registration_service = RegistrationService(db)

    try:
        result = registration_service.register_for_event_tier(
            event_id=event_id,
            tier_id=registration_data.tier_id,
            user_id=current_user.id,
            participant_name=registration_data.participant_name,
            age=registration_data.age,
            gender=registration_data.gender,
            t_shirt_size=registration_data.t_shirt_size
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/registrations/{registration_id}/upgrade-tier", response_model=TierUpgradeResponse)
@limiter.limit(RateLimits.WRITE_CREATE)
async def upgrade_registration_tier(
    request: Request,
    response: Response,
    registration_id: int,
    upgrade_data: TierUpgradeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TierUpgradeResponse:
    """
    Upgrade registration to a higher tier.

    **Authenticated Users Only** (must own the registration)

    Calculates upgrade price (new_tier_price - current_tier_price) and handles payment.
    If upgrade price is 0, auto-confirms. Otherwise, returns payment order.

    Args:
        registration_id: Registration ID
        upgrade_data: New tier selection

    Returns:
        TierUpgradeResponse: Upgrade details and payment order (if required)

    Raises:
        403: If user doesn't own the registration
        400: If upgrade is invalid (not higher tier, sold out, etc.)
        404: If registration or tier not found
    """
    registration_service = RegistrationService(db)

    try:
        result = registration_service.upgrade_tier(
            registration_id=registration_id,
            new_tier_id=upgrade_data.new_tier_id,
            user_id=current_user.id
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/registrations/{registration_id}/tiers", response_model=List[RegistrationTierResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_registration_tiers(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[RegistrationTierResponse]:
    """
    Get tier history for a registration.

    **Authenticated Users Only** (must own the registration)

    Returns all tiers the user has registered for, including upgrades.

    Args:
        registration_id: Registration ID

    Returns:
        List[RegistrationTierResponse]: List of tiers with timestamps

    Raises:
        403: If user doesn't own the registration
        404: If registration not found
    """
    registration_service = RegistrationService(db)

    try:
        tier_history = registration_service.get_user_tiers(registration_id, current_user.id)

        # Convert to response format
        response_data = []
        for tier_entry in tier_history:
            response_data.append(RegistrationTierResponse(
                id=tier_entry.id,
                registration_id=tier_entry.registration_id,
                tier_id=tier_entry.tier_id,
                tier_name=tier_entry.get_tier_name(),
                tier_price=tier_entry.get_tier_price(),
                registered_at=tier_entry.registered_at,
                is_upgrade=tier_entry.is_upgrade,
                upgraded_from_tier_id=tier_entry.upgraded_from_tier_id,
                upgrade_payment_id=tier_entry.upgrade_payment_id
            ))

        return response_data
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/registrations/{registration_id}/rewards", response_model=EffectiveRewardsResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_effective_rewards(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EffectiveRewardsResponse:
    """
    Get effective rewards for a registration (additive from all tiers).

    **Authenticated Users Only** (must own the registration)

    Returns combined rewards from all tiers the user has access to.
    Higher tiers automatically include rewards from lower tiers.

    Args:
        registration_id: Registration ID

    Returns:
        EffectiveRewardsResponse: All rewards user is entitled to

    Raises:
        403: If user doesn't own the registration
        404: If registration not found
    """
    registration_service = RegistrationService(db)

    try:
        rewards_data = registration_service.get_effective_rewards(registration_id, current_user.id)
        return EffectiveRewardsResponse(**rewards_data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
