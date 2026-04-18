"""
Registration API Endpoints
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
from app.schemas.registration import RegistrationUpdate, RegistrationResponse
from app.models.user import User
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/v1/registrations", tags=["Registrations"])


@router.get("/{registration_id}", response_model=RegistrationResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_registration(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> RegistrationResponse:
    """
    Get registration details by ID.

    Returns detailed information about a specific registration.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        RegistrationResponse: Registration details

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner

    Rate Limit:
        100 requests per minute

    Authorization:
        Users can only view their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    registration: RegistrationResponse = service.get_registration_by_id(registration_id)

    # Check ownership
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_registration_owner(registration, current_user.id)

    return registration


@router.put("/{registration_id}", response_model=RegistrationResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_registration(
    request: Request,
    response: Response,
    registration_id: int,
    registration_data: RegistrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> RegistrationResponse:
    """
    Update registration details.

    Updates an existing registration. Users can only update their own registrations.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID to update
        registration_data: Updated registration data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        RegistrationResponse: Updated registration details

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner

    Rate Limit:
        30 requests per minute

    Authorization:
        Users can only update their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    update_dict: Dict = registration_data.model_dump(exclude_unset=True)
    registration: RegistrationResponse = service.update_registration(registration_id, update_dict, current_user.id)
    return registration


@router.get("/users/{user_id}/registrations", response_model=List[RegistrationResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_user_registrations(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> List[RegistrationResponse]:
    """
    Get all registrations for a user.

    Returns list of all registrations for a specific user.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: User ID
        current_user: Current authenticated user from JWT token
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session dependency

    Returns:
        List of RegistrationResponse objects

    Raises:
        PermissionDeniedException: If user tries to view another user's registrations

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view their own registrations

    Requires:
        Bearer token in Authorization header
    """
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(user_id, current_user.id, "registrations")

    service: RegistrationService = RegistrationService(db)
    registrations: List[RegistrationResponse] = service.get_registrations_by_user(user_id, skip, limit)
    return registrations


@router.get("/events/{event_id}/registrations", response_model=List[RegistrationResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_event_registrations(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> List[RegistrationResponse]:
    """
    Get all registrations for an event.

    Returns list of all registrations for a specific event. Only event organizers can access.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        current_user: Current authenticated user from JWT token
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session dependency

    Returns:
        List of RegistrationResponse objects

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        60 requests per minute

    Authorization:
        Only event organizers can view all registrations

    Requires:
        Bearer token in Authorization header
    """
    # Verify user is the event organizer
    from app.services.event_service import EventService
    event_service: EventService = EventService(db)
    event = event_service.get_event_by_id(event_id)
    event_service.check_event_organizer(event, current_user.id)

    service: RegistrationService = RegistrationService(db)
    registrations: List[RegistrationResponse] = service.get_registrations_by_event(event_id, skip, limit)
    return registrations
