"""
Registrations API Endpoints
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.modules.registrations.schemas.registration import (
    RegistrationCreate,
    RegistrationResponse,
    RegistrationUpdate,
)
from app.modules.registrations.services.registration_service import RegistrationService


class UpgradeTierRequest(BaseModel):
    tier_id: int  # public-facing name; maps to service param new_tier_id
    activity_id: int | None = None
    participant_name: str | None = None
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_registration(
    registration_data: RegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's registrations

    Returns all events the user has registered for
    """
    service = RegistrationService(db)
    registrations = service.get_registrations_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return [RegistrationResponse.model_validate(reg) for reg in registrations]


@router.get("/{registration_id}", response_model=RegistrationResponse)
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get registration details

    Returns:
    - Registration status
    - Event details
    - Payment status
    - Selected tier
    - Activity progress
    """
    service = RegistrationService(db)
    registration = service.get_registration_by_id(registration_id)

    # TODO: Add permission check (user must own registration or be admin)

    return RegistrationResponse.model_validate(registration)


@router.patch("/{registration_id}", response_model=RegistrationResponse)
def update_registration(
    registration_id: int,
    registration_data: RegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    service.cancel_registration(
        registration_id=registration_id,
        current_user_id=current_user.id
    )
    return None


@router.post("/{registration_id}/confirm", response_model=RegistrationResponse)
def confirm_registration(
    registration_id: int,
    upgrade_tier_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        registration_id=registration_id,
        upgrade_to_tier_id=upgrade_tier_id
    )

    registration = service.get_registration_by_id(registration_id)
    return RegistrationResponse.model_validate(registration)


@router.get("/event/{event_id}", response_model=list[RegistrationResponse])
def get_event_registrations(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all registrations for an event (Admin/Organizer only)

    Returns participant list with:
    - Registration details
    - Payment status
    - Activity progress
    """
    # TODO: Add admin/organizer permission check

    service = RegistrationService(db)
    registrations = service.get_registrations_by_event(
        event_id=event_id,
        skip=skip,
        limit=limit
    )
    return [RegistrationResponse.model_validate(reg) for reg in registrations]


@router.get("/{registration_id}/tiers")
def get_registration_tiers(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    tiers = service.get_user_tiers(
        registration_id=registration_id,
        user_id=current_user.id
    )
    return tiers


@router.get("/{registration_id}/rewards")
def get_registration_rewards(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        registration_id=registration_id,
        user_id=current_user.id
    )
    return rewards


@router.post("/{registration_id}/upgrade-tier")
def upgrade_registration_tier(
    registration_id: int,
    request: UpgradeTierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Upgrade registration to a higher tier.

    Returns upgrade details and payment order if payment is required.
    """
    service = RegistrationService(db)
    return service.upgrade_tier(
        registration_id=registration_id,
        new_tier_id=request.tier_id,
        user_id=current_user.id,
        activity_id=request.activity_id,
        participant_name=request.participant_name,
        age=request.age,
        gender=request.gender,
        t_shirt_size=request.t_shirt_size,
    )


@router.get("/events/{event_id}/my-registration", response_model=Optional[RegistrationResponse])
def get_my_event_registration(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if current user is registered for a specific event.

    This endpoint is used by the frontend to:
    - Determine whether to show "Register" or "Already Registered" button
    - Display existing registration details on event pages
    - Prevent duplicate registrations

    Returns:
    - Registration details if user is registered for this event
    - 404 if user is not registered (this is expected behavior, not an error)

    Note: Uses the existing repository method get_by_user_and_event
    """
    service = RegistrationService(db)
    registration = service.repository.get_by_user_and_event(
        user_id=current_user.id,
        event_id=event_id
    )

    if not registration:
        raise NotFoundException("Registration", f"for user {current_user.id} in event {event_id}")

    return RegistrationResponse.model_validate(registration)


@router.get("/events/{event_id}/registrations-with-progress", response_model=list[RegistrationResponse])
def get_event_registrations_with_progress(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    # TODO: Add admin/organizer permission check
    # For now, allowing any authenticated user to view this data

    service = RegistrationService(db)

    # Query registrations with progress data eagerly loaded using joinedload
    # This prevents N+1 query problem by loading all data in a single query
    registrations = db.query(service.repository.model).filter(
        service.repository.model.event_id == event_id
    ).options(
        joinedload(service.repository.model.activity_progress),
        joinedload(service.repository.model.user)
    ).offset(skip).limit(limit).all()

    return [RegistrationResponse.model_validate(reg) for reg in registrations]
