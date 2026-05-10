"""
Fitness Tracker API Endpoints
Handles connecting and managing fitness tracker integrations
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection
from app.models.fitbit_connection import FitbitConnection
from app.services.fitness_trackers import FitnessTrackerFactory
from app.services.activity_sync_service import ActivitySyncService
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fitness", tags=["Fitness Trackers"])


# Request/Response Models
class ConnectTrackerRequest(BaseModel):
    provider: str  # google_fit, apple_health, nike_run_club
    auth_code: Optional[str] = None  # OAuth code or device token


class TrackerConnectionResponse(BaseModel):
    id: int
    provider: str
    is_active: bool
    last_sync_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class SyncRequest(BaseModel):
    challenge_id: Optional[int] = None
    force: bool = False


@router.get("/supported", response_model=List[dict])
async def get_supported_providers():
    """
    Get list of supported fitness tracker providers

    Returns:
        List of provider info with auth types and features
    """
    return FitnessTrackerFactory.get_supported_providers()


@router.get("/connections")
async def get_user_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all fitness tracker providers with connection status

    Returns:
        List of all supported providers with connection status and primary sync source
    """
    # Get supported providers
    supported_providers = FitnessTrackerFactory.get_supported_providers()

    # Get user's connections
    user_connections = {}

    # Get Strava connection
    strava = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id,
        StravaConnection.is_active == True
    ).first()

    if strava:
        user_connections['strava'] = {
            'id': strava.id,
            'last_sync_at': strava.last_sync_at.isoformat() if strava.last_sync_at else None
        }

    # Get Fitbit connection
    fitbit = db.query(FitbitConnection).filter(
        FitbitConnection.user_id == current_user.id,
        FitbitConnection.is_active == True
    ).first()

    if fitbit:
        user_connections['fitbit'] = {
            'id': fitbit.id,
            'last_sync_at': fitbit.last_sync_at.isoformat() if fitbit.last_sync_at else None
        }

    # Get other tracker connections
    fitness_trackers = db.query(FitnessTrackerConnection).filter(
        FitnessTrackerConnection.user_id == current_user.id,
        FitnessTrackerConnection.is_active == True
    ).all()

    for tracker in fitness_trackers:
        user_connections[tracker.provider] = {
            'id': tracker.id,
            'last_sync_at': tracker.last_sync_at.isoformat() if tracker.last_sync_at else None
        }

    # Build response with all providers
    result = []
    for provider in supported_providers:
        provider_name = provider['name']
        connection = user_connections.get(provider_name)

        # Check if user logged in with this provider's Google account
        logged_in_with_google = (
            provider_name == 'google_fit' and
            current_user.oauth_provider == 'google' and
            current_user.oauth_id is not None
        )

        result.append({
            'provider': provider_name,
            'display_name': provider['display_name'],
            'connected': connection is not None,
            'connection_id': connection['id'] if connection else None,
            'last_sync_at': connection['last_sync_at'] if connection else None,
            'last_sync_status': 'success' if connection else None,
            'requires_file_upload': provider['auth_type'] == 'manual',
            'supports_oauth': provider['auth_type'] == 'oauth2',
            'is_primary': current_user.primary_sync_source == provider_name,
            'same_account_as_login': logged_in_with_google  # New field
        })

    return result


@router.get("/auth/{provider}/authorize")
async def get_oauth_authorize_url(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get OAuth authorization URL for a provider

    Args:
        provider: Provider name (google_fit, strava, etc.)

    Returns:
        Dictionary with authorization_url
    """
    import os

    if provider == "google_fit":
        # Build Google Fit OAuth URL
        client_id = os.getenv("GOOGLE_FIT_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_FIT_REDIRECT_URI", "http://localhost:5173/auth/google-fit/callback")

        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Fit integration not configured"
            )

        scope = " ".join([
            "https://www.googleapis.com/auth/fitness.activity.read",
            "https://www.googleapis.com/auth/fitness.location.read",
            "https://www.googleapis.com/auth/userinfo.email"
        ])

        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&prompt=consent"
        )

        return {"authorization_url": auth_url}

    elif provider == "strava":
        # Build Strava OAuth URL
        client_id = os.getenv("STRAVA_CLIENT_ID")
        redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:5173/auth/strava/callback")

        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Strava integration not configured"
            )

        auth_url = (
            f"https://www.strava.com/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=activity:read_all,profile:read_all"
            f"&approval_prompt=force"
        )

        return {"authorization_url": auth_url}

    elif provider == "fitbit":
        # Build Fitbit OAuth URL
        client_id = os.getenv("FITBIT_CLIENT_ID")
        redirect_uri = os.getenv("FITBIT_REDIRECT_URI", "http://localhost:5173/auth/fitbit/callback")

        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Fitbit integration not configured"
            )

        auth_url = (
            f"https://www.fitbit.com/oauth2/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=activity profile"
        )

        return {"authorization_url": auth_url}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth not supported for provider: {provider}"
        )


@router.post("/auth/{provider}/callback")
async def handle_oauth_callback(
    provider: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback for a provider

    Args:
        provider: Provider name (google_fit, strava)
        request: Request body with 'code' field

    Returns:
        Connection details
    """
    import os
    import httpx
    from datetime import timedelta, timezone as tz
    import json

    auth_code = request.get('code')
    if not auth_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code"
        )

    if provider == "google_fit":
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        client_id = os.getenv("GOOGLE_FIT_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_FIT_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_FIT_REDIRECT_URI")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "code": auth_code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code: {response.text}"
                )

            token_data = response.json()

            if not token_data.get("refresh_token"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No refresh token received. User may need to revoke access and reconnect."
                )

        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_info = response.json()

        # Calculate token expiration
        from datetime import datetime
        expires_at = datetime.now(tz.utc) + timedelta(seconds=token_data.get("expires_in", 3600))

        # Check if this Google account is already connected to a different user
        google_user_id = user_info.get("id", "")
        if google_user_id:
            existing_google_connection = db.query(FitnessTrackerConnection).filter(
                FitnessTrackerConnection.provider == "google_fit",
                FitnessTrackerConnection.provider_user_id == google_user_id
            ).first()

            if existing_google_connection and existing_google_connection.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This Google account is already connected to another user"
                )

        # Store or update connection
        connection = db.query(FitnessTrackerConnection).filter(
            FitnessTrackerConnection.user_id == current_user.id,
            FitnessTrackerConnection.provider == "google_fit"
        ).first()

        if connection:
            connection.access_token = token_data["access_token"]
            connection.refresh_token = token_data["refresh_token"]
            connection.token_expires_at = expires_at
            connection.scope = token_data.get("scope")
            connection.provider_data = json.dumps(user_info)
            connection.provider_user_id = user_info.get("id", "")
            connection.is_active = True
            connection.updated_at = datetime.now(tz.utc)
        else:
            connection = FitnessTrackerConnection(
                user_id=current_user.id,
                provider="google_fit",
                provider_user_id=user_info.get("id", ""),
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_expires_at=expires_at,
                scope=token_data.get("scope"),
                provider_data=json.dumps(user_info),
                is_active=True
            )
            db.add(connection)

        db.commit()
        db.refresh(connection)

        # Auto-set as primary if user has no primary sync source
        if not current_user.primary_sync_source:
            current_user.primary_sync_source = "google_fit"
            db.commit()
            logger.info(f"Auto-set google_fit as primary sync source for user {current_user.id}")

        return {
            "provider": "google_fit",
            "connected": True,
            "connection_id": connection.id,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "user_email": user_info.get("email"),
            "is_primary": current_user.primary_sync_source == "google_fit"
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback not supported for provider: {provider}"
        )


@router.post("/connect")
async def connect_tracker(
    request: ConnectTrackerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect a fitness tracker

    For OAuth providers (Google Fit): provide auth_code from OAuth flow
    For native providers (Apple Health): provide device token
    For manual providers (Nike Run Club): no auth_code needed
    """
    try:
        # Check if already connected
        existing = db.query(FitnessTrackerConnection).filter(
            FitnessTrackerConnection.user_id == current_user.id,
            FitnessTrackerConnection.provider == request.provider
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already connected to {request.provider}"
            )

        # Create tracker instance
        connection_data = {
            "client_id": "",  # Would come from config
            "client_secret": "",
            "redirect_uri": ""
        }

        tracker = FitnessTrackerFactory.create_tracker(request.provider, connection_data)

        # Authenticate
        if request.auth_code:
            auth_result = await tracker.authenticate(request.auth_code)
        else:
            auth_result = {
                "access_token": None,
                "refresh_token": None,
                "expires_at": None
            }

        # Create connection record
        connection = FitnessTrackerConnection(
            user_id=current_user.id,
            provider=request.provider,
            provider_user_id=None,
            access_token=auth_result.get("access_token"),
            refresh_token=auth_result.get("refresh_token"),
            token_expires_at=auth_result.get("expires_at"),
            scope=auth_result.get("scope"),
            provider_data=None,
            is_active=True
        )

        db.add(connection)
        db.commit()
        db.refresh(connection)

        return {
            "message": f"Successfully connected to {request.provider}",
            "connection_id": connection.id,
            "provider": connection.provider
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error connecting tracker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect fitness tracker"
        )


@router.post("/primary-source")
async def set_primary_sync_source(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set the primary sync source for automatic background syncing

    Args:
        request: {"provider": "strava" | "google_fit" | null}

    Returns:
        Success message with updated primary source
    """
    provider = request.get('provider')

    # Validate provider if not null
    if provider is not None:
        # Check if user has this connection
        if provider == 'strava':
            connection = db.query(StravaConnection).filter(
                StravaConnection.user_id == current_user.id,
                StravaConnection.is_active == True
            ).first()
        else:
            connection = db.query(FitnessTrackerConnection).filter(
                FitnessTrackerConnection.user_id == current_user.id,
                FitnessTrackerConnection.provider == provider,
                FitnessTrackerConnection.is_active == True
            ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active connection found for {provider}. Please connect first."
            )

    # Update user's primary sync source
    current_user.primary_sync_source = provider
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Primary sync source updated successfully",
        "primary_sync_source": provider
    }


@router.delete("/connections/{connection_id}")
async def disconnect_tracker(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a fitness tracker
    """
    connection = db.query(FitnessTrackerConnection).filter(
        FitnessTrackerConnection.id == connection_id,
        FitnessTrackerConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    # If this was the primary sync source, clear it
    if current_user.primary_sync_source == connection.provider:
        current_user.primary_sync_source = None
        logger.info(f"Cleared primary sync source for user {current_user.id} as {connection.provider} was disconnected")

    # Revoke access if possible
    try:
        connection_data = {
            "access_token": connection.access_token,
            "refresh_token": connection.refresh_token
        }
        tracker = FitnessTrackerFactory.create_tracker(connection.provider, connection_data)
        await tracker.revoke_access()
    except Exception as e:
        logger.warning(f"Could not revoke access: {e}")

    # Delete connection
    db.delete(connection)
    db.commit()

    return {"message": "Tracker disconnected successfully"}


@router.post("/sync/{provider}")
async def sync_provider_activities(
    provider: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from a specific fitness provider for an event

    Args:
        provider: Provider name (google_fit, strava, etc.)
        request: Request body with event_id and optional force_refresh

    Returns:
        Sync results with activity counts and distance updates
    """
    from sqlalchemy import and_

    event_id = request.get('event_id')
    force_refresh = request.get('force_refresh', False)

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id is required"
        )

    # Check connection based on provider
    if provider == "strava":
        # Strava uses separate strava_connection table
        strava_connection = db.query(StravaConnection).filter(
            and_(
                StravaConnection.user_id == current_user.id,
                StravaConnection.is_active == True
            )
        ).first()
        
        if not strava_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Strava connection found. Please connect your account first."
            )
        
        # Import and call Strava sync
        from app.api.strava import sync_challenge_activities as strava_sync
        return await strava_sync(event_id, current_user, db)
        
    else:
        # Other providers use fitness_tracker_connections table
        connection = db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == current_user.id,
                FitnessTrackerConnection.provider == provider,
                FitnessTrackerConnection.is_active == True
            )
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active {provider} connection found. Please connect your account first."
            )

        # Delegate to provider-specific sync logic
        if provider == "google_fit":
            from app.api.google_fit import sync_challenge_activities as google_fit_sync
            return await google_fit_sync(event_id, current_user, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync not supported for provider: {provider}"
            )


@router.post("/sync")
async def sync_activities(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger activity sync for current user

    Optional:
    - challenge_id: Sync for specific challenge (or all if not provided)
    - force: Force resync even if recently synced
    """
    try:
        sync_service = ActivitySyncService(db)
        results = await sync_service.sync_user_activities(
            user_id=current_user.id,
            challenge_id=request.challenge_id,
            force=request.force
        )

        return {
            "message": "Sync completed",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error syncing activities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync activities"
        )


@router.post("/upload-activity")
async def upload_activity_file(
    file: UploadFile = File(...),
    event_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload activity file (GPX, TCX, FIT) and update progress

    Supports manual upload from Nike Run Club, Garmin, Polar, Apple Watch, etc.
    File is processed in memory and NOT saved to disk.

    Args:
        file: Activity file (.gpx, .tcx, or .fit)
        event_id: Optional event ID to update progress for

    Returns:
        Parsed activity data and updated progress
    """
    from app.services.activity_file_parser import ActivityFileParser
    from app.models.activity_progress import ActivityProgress
    from app.models.event import Event
    from sqlalchemy import and_
    from datetime import datetime, timezone

    # Validate file type
    allowed_extensions = ['.gpx', '.tcx', '.fit']
    file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file content (process in memory, don't save)
        file_content = await file.read()

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 10MB."
            )

        # Parse activity file
        activity_data = ActivityFileParser.parse_activity_file(file_content, file.filename)

        logger.info(f"Parsed activity file for user {current_user.id}: {activity_data}")

        # Determine which event to update
        if event_id:
            # Specific event provided
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found"
                )
            events_to_update = [event]
        else:
            # Find all active events user is registered for
            from app.models.registration import Registration

            now = datetime.now(timezone.utc).date()
            registrations = db.query(Registration).join(Event).filter(
                and_(
                    Registration.user_id == current_user.id,
                    Event.event_date <= now,
                    Event.event_end_date >= now,
                    Event.status.in_(['ongoing', 'upcoming'])
                )
            ).all()

            events_to_update = [reg.event for reg in registrations]

        if not events_to_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active events found. Please specify an event_id or register for an event."
            )

        # Update progress for each event
        updated_events = []
        for event in events_to_update:
            # Get or create activity progress
            activity_progress = db.query(ActivityProgress).filter(
                and_(
                    ActivityProgress.user_id == current_user.id,
                    ActivityProgress.event_id == event.id
                )
            ).first()

            if not activity_progress:
                # Create new progress record
                activity_progress = ActivityProgress(
                    user_id=current_user.id,
                    event_id=event.id,
                    target_distance=event.distance_km if hasattr(event, 'distance_km') else 0,
                    distance_completed=0,
                    progress_percentage=0
                )
                db.add(activity_progress)
                db.flush()

            # Update progress using highest-wins logic
            from app.services.progress_validation_service import ProgressValidationService

            result = ProgressValidationService.validate_and_update_progress(
                progress=activity_progress,
                new_distance_km=activity_data['distance_km'],
                source='manual_upload',
                metadata={
                    'file_format': activity_data['file_format'],
                    'activity_type': activity_data['activity_type'],
                    'activity_date': activity_data['activity_date'].isoformat(),
                    'duration_minutes': activity_data['duration_minutes']
                }
            )

            # Update activity count and duration
            activity_progress.total_activities += 1
            activity_progress.total_duration_minutes += activity_data['duration_minutes']
            activity_progress.last_sync_at = datetime.now(timezone.utc)

            updated_events.append({
                'event_id': event.id,
                'event_name': event.name,
                'distance_added': activity_data['distance_km'],
                'new_total': float(activity_progress.distance_completed),
                'message': result['message']
            })

        db.commit()

        return {
            "success": True,
            "message": "Activity file processed successfully",
            "activity_data": {
                "distance_km": activity_data['distance_km'],
                "duration_minutes": activity_data['duration_minutes'],
                "activity_type": activity_data['activity_type'],
                "activity_date": activity_data['activity_date'].isoformat(),
                "file_format": activity_data['file_format']
            },
            "updated_events": updated_events
        }

    except ValueError as e:
        # File parsing error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing activity file upload: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process activity file: {str(e)}"
        )
