"""
Unified Fitness Trackers API

Consolidates Strava, Garmin, Fitbit, Wahoo, Google Fit, and Polar APIs
into a single unified interface using the DDD pattern.

Replaces:
- app/api/strava.py
- app/api/garmin.py
- app/api/fitbit.py
- app/api/wahoo.py
- app/api/google_fit.py
- app/api/fitness_trackers.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    ValidationException,
)
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.modules.fitness_trackers.domain.value_objects import ProviderType
from app.modules.fitness_trackers.schemas.connection import *
from app.modules.fitness_trackers.services.commands import *
from app.modules.fitness_trackers.services.fitness_tracker_service import FitnessTrackerService
from app.modules.fitness_trackers.services.queries import *

router = APIRouter(
    prefix="/fitness",
    tags=["Fitness Trackers"],
)


@router.get("/providers", response_model=ProvidersListResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_available_providers(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    """
    Get list of configured fitness tracker providers.

    Returns all providers that have valid OAuth configuration.
    """
    service = FitnessTrackerService(db)
    query = GetAvailableProvidersQuery()

    providers = service.handle_get_available_providers(query)

    return ProvidersListResponse(providers=providers)


@router.get("/{provider}/auth", response_model=AuthorizationUrlResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_authorization_url(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    state: str = Query(None, description="Optional state parameter for CSRF protection"),
    db: Session = Depends(get_db),
):
    """
    Get OAuth authorization URL for provider.

    User should be redirected to this URL to authorize the connection.
    """
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    query = GetAuthorizationUrlQuery(provider=provider_type, state=state)

    try:
        auth_url = service.handle_get_authorization_url(query)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return AuthorizationUrlResponse(authorization_url=auth_url, provider=provider.value)


@router.post(
    "/{provider}/connect", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(RateLimits.DEFAULT)
async def connect_provider(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    connect_data: ConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Connect fitness tracker provider using authorization code.

    Business Rules:
    - One connection per user per provider
    - Authorization code must be valid
    - Athlete ID must not be connected to another user
    """
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    command = ConnectProviderCommand(
        user_id=current_user.id, provider=provider_type, authorization_code=connect_data.code
    )

    try:
        connection = await service.handle_connect_provider(command)
        return ConnectionResponse.model_validate(connection)
    except AlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{provider}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.DEFAULT)
async def disconnect_provider(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disconnect fitness tracker provider.

    Business Rules:
    - Only owner can disconnect
    - Connection is deactivated (soft delete)
    """
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    command = DisconnectProviderCommand(user_id=current_user.id, provider=provider_type)

    try:
        await service.handle_disconnect_provider(command)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{provider}/status", response_model=ConnectionStatusResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_connection_status(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get connection status for provider.

    Returns connection health, sync status, and error information.
    """
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    query = GetConnectionStatusQuery(user_id=current_user.id, provider=provider_type)

    status_data = service.handle_get_connection_status(query)

    return ConnectionStatusResponse(**status_data)


@router.get("/connections", response_model=list[ConnectionResponse])
@limiter.limit(RateLimits.DEFAULT)
async def get_my_connections(
    request: Request,
    response: Response,
    active_only: bool = Query(True, description="Only return active connections"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all fitness tracker connections for current user.
    """
    service = FitnessTrackerService(db)

    query = GetUserConnectionsQuery(user_id=current_user.id, active_only=active_only)

    connections = service.handle_get_user_connections(query)

    return [ConnectionResponse.model_validate(c) for c in connections]


@router.post("/{provider}/sync", response_model=SyncResponse)
@limiter.limit(RateLimits.DEFAULT)
async def sync_activities(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    force: bool = Query(False, description="Force sync even if recently synced"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually trigger activity sync from provider.

    Business Rules:
    - Connection must be active and have valid token
    - Skips if recently synced (unless force=True)
    - Syncs activities and updates progress
    """
    service = FitnessTrackerService(db)

    # Get connection
    provider_type = ProviderType(provider.value)
    connection_query = GetUserConnectionQuery(user_id=current_user.id, provider=provider_type)

    connection = service.handle_get_user_connection(connection_query)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No {provider.value} connection found"
        )

    # Sync activities
    command = SyncActivitiesCommand(connection_id=connection.id, force=force)

    try:
        sync_status = await service.handle_sync_activities(command)

        return SyncResponse(
            success=sync_status.is_success,
            activities_synced=sync_status.activities_synced.value,
            error_message=sync_status.error_message,
            provider=provider.value,
        )
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{provider}/sync/enable", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.DEFAULT)
async def enable_sync(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable automatic syncing for provider."""
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    command = EnableSyncCommand(user_id=current_user.id, provider=provider_type)

    try:
        service.handle_enable_sync(command)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{provider}/sync/disable", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.DEFAULT)
async def disable_sync(
    request: Request,
    response: Response,
    provider: ProviderEnum,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable automatic syncing for provider."""
    service = FitnessTrackerService(db)

    provider_type = ProviderType(provider.value)
    command = DisableSyncCommand(user_id=current_user.id, provider=provider_type)

    try:
        service.handle_disable_sync(command)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/strava/progress/{event_id}", response_model=ChallengeProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_strava_progress(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user's progress for specific event (backwards compatibility endpoint).

    This endpoint returns the user's progress data for the specified event,
    regardless of whether they have an active Strava connection.
    It's named for backwards compatibility with the frontend.

    Returns 404 if:
    - User has no registration for this event
    - No progress record exists for the registration
    """
    service = FitnessTrackerService(db)
    query = GetStravaProgressQuery(user_id=current_user.id, event_id=event_id)
    progress = service.handle_get_strava_progress(query)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No progress found for event {event_id}"
        )

    # Transform ProgressResponse to ChallengeProgressResponse for frontend compatibility
    return ChallengeProgressResponse(
        challenge_id=progress.event_id,
        total_distance_km=float(progress.distance_completed),
        total_activities=progress.get_total_activities(),
        progress_percentage=progress.progress_percentage,
        goal_distance_km=float(progress.target_distance) if progress.target_distance else None,
        last_activity_date=progress.last_sync_at.isoformat() if progress.last_sync_at else None,
        current_streak_days=0,  # TODO: Implement streak tracking
        proof_image_url=progress.proof_image_url,
        last_sync_source=progress.highest_distance_source,
        last_sync_at=progress.last_sync_at.isoformat() if progress.last_sync_at else None,
    )
