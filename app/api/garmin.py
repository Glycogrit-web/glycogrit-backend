"""
Garmin Connect API Integration Routes
Handles OAuth authentication and activity syncing
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.garmin_connection import GarminConnection
from app.models.activity_progress import ActivityProgress
from app.models.event import Event
from app.services.garmin_service import GarminService, get_garmin_service
from app.services.progress_validation_service import ProgressValidationService

router = APIRouter(prefix="/garmin", tags=["Garmin"])


@router.get("/authorize")
async def get_authorization_url(
    garmin_service: GarminService = Depends(get_garmin_service)
):
    """
    Step 1: Get Garmin OAuth authorization URL
    Returns URL to redirect user to Garmin for authorization
    """
    try:
        auth_data = garmin_service.get_authorization_url()
        return {
            "authorization_url": auth_data["authorization_url"],
            "oauth_token": auth_data["oauth_token"],
            "oauth_token_secret": auth_data["oauth_token_secret"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get authorization URL: {str(e)}"
        )


@router.post("/callback")
async def handle_callback(
    oauth_token: str = Query(...),
    oauth_token_secret: str = Query(...),
    oauth_verifier: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    garmin_service: GarminService = Depends(get_garmin_service)
):
    """
    Step 2: Handle OAuth callback
    Exchange temporary token for access token and create connection
    """
    try:
        # Exchange tokens
        token_data = garmin_service.exchange_token(
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            oauth_verifier=oauth_verifier
        )

        access_token = token_data["access_token"]
        access_token_secret = token_data["access_token_secret"]

        # Get user profile from Garmin
        user_profile = garmin_service.get_user_profile(access_token, access_token_secret)
        garmin_user_id = str(user_profile.get("userId"))

        # Check if this Garmin account is already connected to another user
        existing_connection = db.query(GarminConnection).filter(
            GarminConnection.user_id_garmin == garmin_user_id,
            GarminConnection.user_id != current_user.id
        ).first()

        if existing_connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Garmin account is already connected to another user"
            )

        # Create or update connection
        connection = db.query(GarminConnection).filter(
            GarminConnection.user_id == current_user.id
        ).first()

        if connection:
            # Update existing connection
            connection.access_token = access_token
            connection.access_token_secret = access_token_secret
            connection.user_id_garmin = garmin_user_id
            connection.user_data = user_profile
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            # Create new connection
            connection = GarminConnection(
                user_id=current_user.id,
                access_token=access_token,
                access_token_secret=access_token_secret,
                user_id_garmin=garmin_user_id,
                user_data=user_profile,
                is_active=True
            )
            db.add(connection)

        # Set as primary sync source if user doesn't have one
        if not current_user.primary_sync_source:
            current_user.primary_sync_source = "garmin"

        db.commit()
        db.refresh(connection)

        return {
            "message": "Garmin connected successfully",
            "connection": {
                "user_id_garmin": connection.user_id_garmin,
                "user_name": user_profile.get("displayName", "Garmin User"),
                "is_active": connection.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Garmin: {str(e)}"
        )


@router.get("/connection")
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Garmin connection status
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == current_user.id
    ).first()

    if not connection:
        return {
            "connected": False,
            "message": "No Garmin connection found"
        }

    user_name = connection.user_data.get("displayName", "Garmin User") if connection.user_data else "Garmin User"

    return {
        "connected": True,
        "is_active": connection.is_active,
        "user_name": user_name,
        "last_sync_at": connection.last_sync_at,
        "is_primary_source": current_user.primary_sync_source == "garmin"
    }


@router.delete("/connection")
async def disconnect_garmin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Garmin account
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Garmin connection found"
        )

    # Clear primary sync source if Garmin was primary
    if current_user.primary_sync_source == "garmin":
        current_user.primary_sync_source = None

    db.delete(connection)
    db.commit()

    return {"message": "Garmin disconnected successfully"}


@router.post("/sync/{challenge_id}")
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    garmin_service: GarminService = Depends(get_garmin_service)
):
    """
    Manually sync activities for a specific challenge from Garmin
    """
    # Get Garmin connection
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == current_user.id,
        GarminConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Garmin connection found"
        )

    # Get challenge/event
    event = db.query(Event).filter(Event.id == challenge_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    try:
        # Fetch activities from Garmin
        activities = garmin_service.get_activities(
            access_token=connection.access_token,
            access_token_secret=connection.access_token_secret,
            start_date=event.start_date,
            end_date=event.end_date
        )

        # Calculate totals
        total_distance_meters = sum(activity.get("distance_meters", 0) for activity in activities)
        total_distance_km = total_distance_meters / 1000
        total_duration_seconds = sum(activity.get("duration_seconds", 0) for activity in activities)
        total_duration_minutes = total_duration_seconds / 60
        activity_count = len(activities)

        # Get or create activity progress
        progress = db.query(ActivityProgress).filter(
            ActivityProgress.user_id == current_user.id,
            ActivityProgress.event_id == challenge_id
        ).first()

        if progress:
            # Use ProgressValidationService for highest-wins logic
            validation_service = ProgressValidationService(db)
            progress = validation_service.update_progress_with_highest_wins(
                progress=progress,
                new_distance=total_distance_km,
                source="garmin"
            )
            # DEPRECATED: progress.get_total_activities() = activity_count
            # DEPRECATED: progress.total_duration_minutes = total_duration_minutes
        else:
            # Create new progress record
            progress = ActivityProgress(
                user_id=current_user.id,
                event_id=challenge_id,
                distance_completed=total_distance_km,
                target_distance=event.distance_km,
                sync_source="garmin",
                highest_distance_source="garmin",
                highest_distance_set_at=datetime.utcnow(),
                distance_by_source={"garmin": total_distance_km},
                total_activities=activity_count,
                total_duration_minutes=total_duration_minutes,
                last_sync_at=datetime.utcnow()
            )
            db.add(progress)

        # Update connection sync time
        connection.last_sync_at = datetime.utcnow()

        db.commit()
        db.refresh(progress)

        return {
            "message": "Activities synced successfully",
            "activities_synced": activity_count,
            "total_distance_km": round(total_distance_km, 2),
            "progress": {
                "distance_completed": progress.distance_completed,
                "target_distance": progress.target_distance,
                "percentage": round((progress.distance_completed / progress.target_distance * 100), 2) if progress.target_distance > 0 else 0
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync activities: {str(e)}"
        )


@router.get("/progress/{challenge_id}")
async def get_challenge_progress(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's progress for a specific challenge
    """
    progress = db.query(ActivityProgress).filter(
        ActivityProgress.user_id == current_user.id,
        ActivityProgress.event_id == challenge_id
    ).first()

    if not progress:
        return {
            "distance_completed": 0,
            "target_distance": 0,
            "percentage": 0,
            "activity_count": 0
        }

    return {
        "distance_completed": progress.distance_completed,
        "target_distance": progress.target_distance,
        "percentage": round((progress.distance_completed / progress.target_distance * 100), 2) if progress.target_distance > 0 else 0,
        "activity_count": progress.get_total_activities() or 0,
        "last_sync_at": progress.last_sync_at,
        "sync_source": progress.sync_source
    }
