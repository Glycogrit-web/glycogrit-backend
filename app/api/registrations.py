"""
Registration API Endpoints
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, status, Query, Request, Response
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


@router.get("/events/{event_id}/my-registration", response_model=RegistrationResponse | None)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_my_event_registration(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check if current user has a registration for this event.

    Returns the user's registration for a specific event, if it exists.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        RegistrationResponse if user is registered, None otherwise

    Rate Limit:
        100 requests per minute

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    registration = service.repository.get_by_user_and_event(current_user.id, event_id)

    # Don't return cancelled registrations
    if not registration or registration.status == 'cancelled':
        return None

    return RegistrationResponse.model_validate(registration)


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


@router.get("/events/{event_id}/registrations-with-progress", response_model=List[Dict])
@limiter.limit(RateLimits.READ_LIST)
async def get_event_registrations_with_progress(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Get all registrations for an event with their progress data (Admin only).

    Returns list of all registrations with progress info including proof images.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        current_user: Current authenticated user from JWT token
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session dependency

    Returns:
        List of registration objects with progress data

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        60 requests per minute

    Authorization:
        Only event organizers can view all registrations with progress

    Requires:
        Bearer token in Authorization header
    """
    from app.services.event_service import EventService
    from app.models.strava_connection import UserChallengeProgress
    from sqlalchemy.orm import joinedload
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[PARTICIPANTS_WITH_PROGRESS] Event ID: {event_id}, User ID: {current_user.id}, User Role: {current_user.role}")

    # Verify user is the event organizer or admin
    event_service: EventService = EventService(db)
    event = event_service.get_event_by_id(event_id)
    logger.info(f"[PARTICIPANTS_WITH_PROGRESS] Event found: {event.name}, Organizer ID: {event.organizer_id}")

    event_service.check_admin_or_organizer(event, current_user)
    logger.info(f"[PARTICIPANTS_WITH_PROGRESS] Permission check passed")

    # Get registrations (returns SQLAlchemy models)
    service: RegistrationService = RegistrationService(db)
    registrations = service.get_registrations_by_event(event_id, skip, limit)
    logger.info(f"[PARTICIPANTS_WITH_PROGRESS] Found {len(registrations)} registrations")

    # Build result with progress data for each registration
    result = []
    for reg in registrations:
        # Get progress data for this user
        progress = db.query(UserChallengeProgress).filter(
            UserChallengeProgress.user_id == reg.user_id,
            UserChallengeProgress.challenge_id == event_id
        ).first()

        logger.info(f"[PARTICIPANTS_WITH_PROGRESS] User {reg.user_id}: Progress={'Found' if progress else 'Not Found'}, Proof={'Yes' if progress and progress.proof_image_url else 'No'}")

        # Convert SQLAlchemy model to Pydantic, then to dict
        reg_pydantic = RegistrationResponse.model_validate(reg)
        reg_dict = reg_pydantic.model_dump()

        if progress:
            reg_dict.update({
                'total_distance_km': progress.total_distance_km,
                'goal_distance_km': progress.goal_distance_km,
                'progress_percentage': progress.progress_percentage,
                'proof_image_url': progress.proof_image_url,
                'last_sync_source': progress.last_sync_source,
                'last_sync_at': progress.last_sync_at.isoformat() if progress.last_sync_at else None,
            })
        else:
            # No progress data yet
            reg_dict.update({
                'total_distance_km': 0,
                'goal_distance_km': 0,
                'progress_percentage': 0,
                'proof_image_url': None,
                'last_sync_source': None,
                'last_sync_at': None,
            })

        result.append(reg_dict)

    logger.info(f"[PARTICIPANTS_WITH_PROGRESS] Returning {len(result)} participants with progress data")
    return result
