"""
Registrations API Endpoints
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.user_reward import UserReward
from app.modules.registrations.schemas.registration import (
    RegistrationCreate,
    RegistrationResponse,
    RegistrationUpdate,
)
from app.modules.registrations.services.registration_service import RegistrationService


router = APIRouter(prefix="/registrations", tags=["registrations"])


def resolve_event_identifier(event_identifier: str, db: Session) -> int:
    """
    Resolve event slug or numeric ID to numeric event_id.

    Matches the pattern used in events endpoint for consistent slug support.

    Args:
        event_identifier: Event slug (e.g., 'june') or numeric ID (e.g., '31')
        db: Database session

    Returns:
        int: Numeric event ID

    Raises:
        HTTPException 404: If event not found
    """
    from app.modules.events.services.event_service import EventService

    service = EventService(db)

    # Try slug lookup first (preferred for clean URLs)
    if not event_identifier.isdigit():
        event = service.get_event_by_slug(event_identifier)
        if event:
            return event.id

    # Try numeric ID lookup (backward compatibility)
    if event_identifier.isdigit():
        event = service.get_event_by_id(int(event_identifier))
        if event:
            return event.id

    # Not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Event not found: {event_identifier}"
    )


def enrich_registration_with_tier_details(registration, db: Session) -> dict:
    """
    Enrich registration with tier details including rewards, benefits, and upgrade options.

    Args:
        registration: Registration domain object
        db: Database session

    Returns:
        Dict with registration data plus tier details
    """
    from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier

    # Start with base registration data
    reg_dict = {
        "id": registration.id,
        "user_id": registration.user_id,
        "event_id": registration.event_id,
        "event_activity_id": registration.event_activity_id,
        "registration_number": registration.registration_number,
        "bib_number": registration.bib_number,
        "status": registration.status,
        "participant_name": registration.participant_name,
        "age": registration.age,
        "gender": registration.gender,
        "t_shirt_size": registration.t_shirt_size,
        "registered_at": registration.registered_at,
        "confirmed_at": registration.confirmed_at,
        "current_tier_id": registration.current_tier_id,
        "total_amount_paid": registration.total_amount_paid,
    }

    # Add tier details if registration uses tier system
    # Use preloaded relationship instead of querying again
    if registration.current_tier_id and hasattr(registration, 'current_tier') and registration.current_tier:
        current_tier = registration.current_tier
        if current_tier:
            reg_dict["tier_name"] = current_tier.tier_name
            reg_dict["tier_price"] = float(current_tier.price)
            reg_dict["tier_rewards"] = current_tier.rewards or []
            reg_dict["tier_description"] = current_tier.description
            reg_dict["tier_order"] = current_tier.tier_order

            # Get available upgrade tiers (higher tiers in same event)
            # Use preloaded event.registration_tiers if available, otherwise query
            if hasattr(registration, 'event') and registration.event and hasattr(registration.event, 'registration_tiers'):
                # Filter preloaded tiers
                available_upgrades = [
                    tier for tier in registration.event.registration_tiers
                    if tier.tier_order > current_tier.tier_order and tier.is_active
                ]
                available_upgrades.sort(key=lambda t: t.tier_order)
            else:
                # Fallback to query if not preloaded
                available_upgrades = db.query(EventRegistrationTier).filter(
                    EventRegistrationTier.event_id == registration.event_id,
                    EventRegistrationTier.tier_order > current_tier.tier_order,
                    EventRegistrationTier.is_active == True
                ).order_by(EventRegistrationTier.tier_order).all()

            if available_upgrades:
                reg_dict["can_upgrade"] = True
                reg_dict["available_upgrades"] = [
                    {
                        "tier_id": tier.id,
                        "tier_name": tier.tier_name,
                        "tier_price": float(tier.price),
                        "tier_rewards": tier.rewards or [],
                        "tier_description": tier.description,
                        "upgrade_price": float(tier.price - current_tier.price),
                        "capacity_remaining": tier.max_registrations - tier.current_registrations if tier.max_registrations else None,
                        "is_sold_out": tier.max_registrations is not None and tier.current_registrations >= tier.max_registrations
                    }
                    for tier in available_upgrades
                ]
            else:
                reg_dict["can_upgrade"] = False
                reg_dict["available_upgrades"] = []
    else:
        # No tier system or legacy registration
        reg_dict["tier_name"] = None
        reg_dict["tier_price"] = None
        reg_dict["tier_rewards"] = None
        reg_dict["tier_description"] = None
        reg_dict["tier_order"] = None
        reg_dict["can_upgrade"] = False
        reg_dict["available_upgrades"] = []

    # Add activity progress if available
    if hasattr(registration, 'activity_progress') and registration.activity_progress:
        progress = registration.activity_progress[0] if isinstance(registration.activity_progress, list) else registration.activity_progress
        reg_dict["total_distance_km"] = float(progress.distance_completed) if progress.distance_completed else None
        reg_dict["goal_distance_km"] = float(progress.target_distance) if progress.target_distance else None
        reg_dict["progress_percentage"] = progress.progress_percentage
        reg_dict["last_sync_source"] = progress.sync_source
        reg_dict["last_sync_at"] = progress.last_sync_at
        reg_dict["proof_image_url"] = progress.proof_image_url
        reg_dict["proof_image_viewed_by_admin"] = progress.proof_image_viewed_by_admin
    else:
        reg_dict["total_distance_km"] = None
        reg_dict["goal_distance_km"] = None
        reg_dict["progress_percentage"] = None
        reg_dict["last_sync_source"] = None
        reg_dict["last_sync_at"] = None
        reg_dict["proof_image_url"] = None
        reg_dict["proof_image_viewed_by_admin"] = None

    reg_dict["reward_status"] = None  # TODO: Add reward status logic

    return reg_dict


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_registration(
    registration_data: RegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register for an event

    Business Rules:
    1. User can only register once per event
    2. Event must be accepting registrations
    3. Generates unique registration number
    4. Creates payment order if required

    Returns:
    - Registration details
    - Payment order (if applicable)
    """
    # Note: This endpoint needs full implementation based on old API logic
    # For now, creating minimal structure
    from app.core.exceptions import ValidationException

    raise ValidationException("Registration API under migration - use old endpoint")


@router.get("/my", response_model=list[RegistrationResponse])
def get_my_registrations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's registrations with full tier details.

    Returns all events the user has registered for including:
    - Current tier information (name, price, rewards, benefits)
    - Available upgrade options (if can upgrade to higher tier)
    - Activity progress details
    """
    service = RegistrationService(db)
    registrations = service.get_registrations_by_user(
        user_id=current_user.id, skip=skip, limit=limit
    )

    # Enrich each registration with tier details
    enriched_registrations = [
        RegistrationResponse.model_validate(enrich_registration_with_tier_details(reg, db))
        for reg in registrations
    ]

    return enriched_registrations


@router.get("/{registration_id}", response_model=RegistrationResponse)
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get registration details with full tier information.

    Returns:
    - Registration status
    - Event details
    - Payment status
    - Current tier (name, price, rewards, benefits)
    - Available upgrade options (if can upgrade to higher tier)
    - Activity progress
    """
    service = RegistrationService(db)
    registration = service.get_registration_by_id(registration_id)

    # TODO: Add permission check (user must own registration or be admin)

    # Enrich with tier details
    enriched_reg = enrich_registration_with_tier_details(registration, db)

    return RegistrationResponse.model_validate(enriched_reg)


@router.patch("/{registration_id}", response_model=RegistrationResponse)
def update_registration(
    registration_id: int,
    registration_data: RegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update registration details

    Allows updating:
    - Participant details (name, emergency contact, etc.)
    - T-shirt size
    - BIB number (admin only)
    """
    from app.core.exceptions import ValidationException

    raise ValidationException("Registration update API under migration - use old endpoint")


@router.delete("/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel registration

    Business Rules:
    1. Must be registration owner
    2. Cannot cancel if event already started
    3. Initiates refund if payment was made
    4. Preserves data for historical records
    """
    service = RegistrationService(db)
    service.cancel_registration(registration_id=registration_id, current_user_id=current_user.id)
    return None


@router.post("/{registration_id}/confirm", response_model=RegistrationResponse)
def confirm_registration(
    registration_id: int,
    upgrade_tier_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm registration after payment

    Called after successful payment to:
    1. Update registration status
    2. Apply selected tier
    3. Send confirmation email
    4. Generate BIB number
    """
    service = RegistrationService(db)
    service.confirm_registration(
        registration_id=registration_id, upgrade_to_tier_id=upgrade_tier_id
    )

    registration = service.get_registration_by_id(registration_id)
    return RegistrationResponse.model_validate(registration)


@router.get("/event/{event_identifier}", response_model=list[RegistrationResponse])
def get_event_registrations(
    event_identifier: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all registrations for an event (Admin/Organizer only)

    Returns participant list with:
    - Registration details
    - Payment status
    - Activity progress
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    # TODO: Add admin/organizer permission check

    service = RegistrationService(db)
    registrations = service.get_registrations_by_event(event_id=event_id, skip=skip, limit=limit)
    return [RegistrationResponse.model_validate(reg) for reg in registrations]


@router.get("/{registration_id}/tiers")
def get_registration_tiers(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available tiers for registration

    Returns:
    - All tiers for the event
    - Current tier
    - Upgrade options
    - Pricing
    """
    service = RegistrationService(db)
    tiers = service.get_user_tiers(registration_id=registration_id, user_id=current_user.id)
    return tiers


@router.get("/{registration_id}/rewards")
def get_registration_rewards(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get effective rewards for registration

    Returns rewards based on:
    - Selected tier
    - Upgrade history
    - Merged benefits
    """
    service = RegistrationService(db)
    rewards = service.get_effective_rewards(
        registration_id=registration_id, user_id=current_user.id
    )
    return rewards


@router.get("/events/{event_identifier}/my-registrations", response_model=list[RegistrationResponse])
def get_my_event_registrations(
    event_identifier: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get ALL registrations for current user in a specific event.

    NEW ENDPOINT: Returns list of registrations (one per tier).

    After refactoring to support multiple registrations per event, users can now
    register for multiple tiers in the same event. This endpoint returns all of them.

    Returns:
    - List of Registration details (one per tier)
    - Empty list if user is not registered for this event
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = RegistrationService(db)
    registrations = service.repository.get_by_user_and_event(
        user_id=current_user.id, event_id=event_id
    )

    return [RegistrationResponse.model_validate(reg) for reg in registrations]


@router.get("/events/{event_identifier}/my-registration", response_model=Optional[RegistrationResponse])
def get_my_event_registration(
    event_identifier: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    LEGACY ENDPOINT: Get user's registration for a specific event.

    DEPRECATED: This endpoint is maintained for backward compatibility with frontend.
    Returns the HIGHEST tier registration among confirmed/paid registrations.

    Filters to only confirmed or payment_completed statuses to exclude pending
    and cancelled registrations.

    Frontend should migrate to /events/{event_identifier}/my-registrations which returns
    all registrations as a list.

    Returns:
    - Registration details for highest tier if user has valid registration
    - None if user is not registered or has no confirmed/paid registrations
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = RegistrationService(db)
    registrations = service.repository.get_by_user_and_event(
        user_id=current_user.id, event_id=event_id
    )

    if not registrations:
        return None

    # Filter to only confirmed or paid registrations
    # Exclude pending and cancelled registrations
    valid_statuses = ['confirmed', 'payment_completed']
    valid_registrations = [r for r in registrations if r.status in valid_statuses]

    # If no valid registrations, return None (user needs to complete payment/confirmation)
    if not valid_registrations:
        return None

    # Return highest tier registration among valid registrations for backward compatibility
    # Sort by tier_order (higher is better) descending
    highest_tier_registration = sorted(
        valid_registrations,
        key=lambda r: r.current_tier.tier_order if r.current_tier else 0,
        reverse=True
    )[0]

    return RegistrationResponse.model_validate(highest_tier_registration)


@router.get(
    "/events/{event_identifier}/registrations-with-progress", response_model=list[RegistrationResponse]
)
def get_event_registrations_with_progress(
    event_identifier: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all registrations for an event WITH their activity progress data.

    This endpoint joins registrations with their activity progress for efficient
    display in participant lists, leaderboards, and progress tracking dashboards.

    Used by:
    - Admin pages showing participant lists with progress bars
    - Leaderboard displays
    - Progress tracking dashboards
    - Event statistics pages

    Returns:
    - List of registrations with embedded activity_progress relationship

    Note: Should have admin/organizer permission check in production
    TODO: Add admin/organizer permission check
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    # TODO: Add admin/organizer permission check
    # For now, allowing any authenticated user to view this data

    from app.modules.registrations.domain.registration import Registration

    service = RegistrationService(db)

    # Query registrations with all related data eagerly loaded using joinedload
    # This prevents N+1 query problem by loading all data in a single query
    registrations = (
        db.query(Registration)
        .filter(
            Registration.event_id == event_id,
            Registration.payment_successful == True  # Only show registrations with successful payment
        )
        .options(
            joinedload(Registration.activity_progress),
            joinedload(Registration.user),
            joinedload(Registration.current_tier),
            joinedload(Registration.activity),  # Note: relationship is named 'activity' not 'event_activity'
            joinedload(Registration.event),  # Load event relationship for event.name access
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Enrich registration data with computed fields
    result = []
    for reg in registrations:
        reg_dict = {
            "id": reg.id,
            "user_id": reg.user_id,
            "event_id": reg.event_id,
            "event_activity_id": reg.event_activity_id,
            "registration_number": reg.registration_number,
            "bib_number": reg.bib_number,
            "status": reg.status,
            "participant_name": reg.participant_name,
            "age": reg.age,
            "gender": reg.gender,
            "t_shirt_size": reg.t_shirt_size,
            "registered_at": reg.registered_at,
            "confirmed_at": reg.confirmed_at,
            "current_tier_id": reg.current_tier_id,
            "total_amount_paid": float(reg.total_amount_paid) if reg.total_amount_paid else 0.0,
        }

        # Add tier information
        if reg.current_tier:
            reg_dict["tier_name"] = reg.current_tier.tier_name
        else:
            reg_dict["tier_name"] = None

        # Add activity progress information
        if reg.activity_progress:
            progress = reg.activity_progress
            reg_dict["total_distance_km"] = float(progress.distance_completed) if progress.distance_completed else 0.0
            reg_dict["goal_distance_km"] = float(progress.target_distance) if progress.target_distance else 0.0

            # Calculate progress percentage
            if progress.target_distance and progress.target_distance > 0:
                reg_dict["progress_percentage"] = int((float(progress.distance_completed or 0) / float(progress.target_distance)) * 100)
            else:
                reg_dict["progress_percentage"] = 0

            reg_dict["last_sync_source"] = progress.sync_source
            reg_dict["last_sync_at"] = progress.last_sync_at
            reg_dict["proof_image_url"] = progress.proof_image_url
            reg_dict["proof_image_viewed_by_admin"] = progress.proof_image_viewed_by_admin
        else:
            # Get goal distance from activity if no progress exists yet
            if reg.activity:  # Note: relationship is named 'activity' not 'event_activity'
                reg_dict["goal_distance_km"] = float(reg.activity.distance) if reg.activity.distance else 0.0
            else:
                reg_dict["goal_distance_km"] = 0.0

            reg_dict["total_distance_km"] = 0.0
            reg_dict["progress_percentage"] = 0
            reg_dict["last_sync_source"] = None
            reg_dict["last_sync_at"] = None
            reg_dict["proof_image_url"] = None
            reg_dict["proof_image_viewed_by_admin"] = None

        # Query reward for this registration
        reward = db.execute(
            select(UserReward)
            .where(UserReward.registration_id == reg.id)
        ).scalar_one_or_none()

        # Determine if challenge is completed based on activity progress
        is_completed = False
        if reg.activity_progress:
            is_completed = (
                reg.activity_progress.is_completed
                if hasattr(reg.activity_progress, 'is_completed')
                else (
                    reg.activity_progress.distance_completed >= reg.activity_progress.target_distance
                    if reg.activity_progress.target_distance and reg.activity_progress.distance_completed
                    else False
                )
            )

        # Build reward status object
        if reward:
            reward_status = {
                "exists": True,
                "reward_id": str(reward.id),
                "is_unlocked": reward.is_unlocked,
                "is_verified": reward.is_verified,
                "status": reward.status,
                "can_unlock": is_completed,
                "shipping_details_provided": bool(
                    reg.shipping_name
                    and reg.shipping_address
                    and reg.shipping_phone
                ),
                "tracking_number": reward.tracking_number,
                "courier_partner": reward.courier_partner,
                "shipped_at": reward.shipped_at.isoformat() if reward.shipped_at else None,
                "delivered_at": reward.delivered_at.isoformat() if reward.delivered_at else None,
            }
        else:
            # No reward exists yet for this registration
            reward_status = {
                "exists": False,
                "reward_id": None,
                "is_unlocked": False,
                "is_verified": False,
                "status": None,
                "can_unlock": is_completed,
                "shipping_details_provided": bool(
                    reg.shipping_name
                    and reg.shipping_address
                    and reg.shipping_phone
                ),
                "tracking_number": None,
                "courier_partner": None,
                "shipped_at": None,
                "delivered_at": None,
            }

        reg_dict["reward_status"] = reward_status

        result.append(RegistrationResponse.model_validate(reg_dict))

    return result
