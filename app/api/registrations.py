"""
Registration API Endpoints
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.registration import RegistrationUpdate, RegistrationResponse
from app.models.user import User
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/v1/registrations", tags=["Registrations"])


@router.get("/{registration_id}", response_model=RegistrationResponse)
async def get_registration(
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get registration details by ID

    Requires authentication. Users can only view their own registrations.

    - **registration_id**: Registration ID
    """
    service = RegistrationService(db)
    registration = service.get_registration_by_id(registration_id)

    # Check ownership
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_registration_owner(registration, current_user.id)

    return registration


@router.put("/{registration_id}", response_model=RegistrationResponse)
async def update_registration(
    registration_id: int,
    registration_data: RegistrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update registration details

    Users can only update their own registrations.

    - **registration_id**: Registration ID to update
    - **participant_name**: Participant name
    - **age**: Age
    - **gender**: Gender
    - **t_shirt_size**: T-shirt size
    - **bib_number**: Bib number

    Requires: Bearer token in Authorization header
    """
    service = RegistrationService(db)
    update_dict = registration_data.model_dump(exclude_unset=True)
    registration = service.update_registration(registration_id, update_dict, current_user.id)
    return registration


@router.get("/users/{user_id}/registrations", response_model=list[RegistrationResponse])
async def get_user_registrations(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get all registrations for a user

    Requires authentication. Users can only view their own registrations.

    - **user_id**: User ID
    - **skip**: Number of records to skip (offset)
    - **limit**: Maximum number of records to return
    """
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(user_id, current_user.id, "registrations")

    service = RegistrationService(db)
    registrations = service.get_registrations_by_user(user_id, skip, limit)
    return registrations


@router.get("/events/{event_id}/registrations", response_model=list[RegistrationResponse])
async def get_event_registrations(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get all registrations for an event

    Requires authentication. Only event organizers can view all registrations.

    - **event_id**: Event ID
    - **skip**: Number of records to skip (offset)
    - **limit**: Maximum number of records to return
    """
    # Verify user is the event organizer
    from app.services.event_service import EventService
    event_service = EventService(db)
    event = event_service.get_event_by_id(event_id)
    event_service.check_event_organizer(event, current_user.id)

    service = RegistrationService(db)
    registrations = service.get_registrations_by_event(event_id, skip, limit)
    return registrations
