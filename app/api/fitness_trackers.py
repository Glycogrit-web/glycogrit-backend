"""
Fitness Tracker API Endpoints
Handles connecting and managing fitness tracker integrations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection
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
        List of all supported providers with connection status
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

        result.append({
            'provider': provider_name,
            'display_name': provider['display_name'],
            'connected': connection is not None,
            'connection_id': connection['id'] if connection else None,
            'last_sync_at': connection['last_sync_at'] if connection else None,
            'last_sync_status': 'success' if connection else None,
            'requires_file_upload': provider['auth_type'] == 'manual',
            'supports_oauth': provider['auth_type'] == 'oauth2'
        })

    return result


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
