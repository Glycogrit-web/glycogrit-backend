"""
Fitbit API Integration Endpoints
Handles OAuth authentication, activity syncing, and progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
import httpx
import os
import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.fitbit_connection import FitbitConnection
from app.models.activity_progress import ActivityProgress
from app.models.registration import Registration
from app.models.event import Event
from pydantic import BaseModel


router = APIRouter(prefix="/api/fitbit", tags=["fitbit"])
logger = logging.getLogger(__name__)


# Pydantic Schemas
class FitbitAuthResponse(BaseModel):
    authorization_url: str


class FitbitCallbackRequest(BaseModel):
    code: str


class FitbitConnectionResponse(BaseModel):
    fitbit_user_id: str
    is_active: bool
    last_sync_at: Optional[datetime]
    user_name: Optional[str]


class ChallengeProgressResponse(BaseModel):
    challenge_id: int
    total_distance_km: float
    total_activities: int
    progress_percentage: float
    goal_distance_km: Optional[float]
    last_activity_date: Optional[datetime]
    current_streak_days: int
    proof_image_url: Optional[str] = None
    last_sync_source: Optional[str] = None
    last_sync_at: Optional[datetime] = None


class LeaderboardEntry(BaseModel):
    user_id: int
    user_name: str
    total_distance_km: float
    total_activities: int
    rank: int


# Fitbit API Configuration
FITBIT_CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
FITBIT_CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
FITBIT_REDIRECT_URI = os.getenv("FITBIT_REDIRECT_URI", "http://localhost:5173/auth/fitbit/callback")


async def refresh_fitbit_token(connection: FitbitConnection, db: Session) -> str:
    """
    Refresh expired Fitbit access token (via Google OAuth)
    Returns the new access token
    """
    try:
        # Use Google OAuth for token refresh (Fitbit now uses Google Health API)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "client_id": FITBIT_CLIENT_ID,
                    "client_secret": FITBIT_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": connection.refresh_token
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to refresh Fitbit token: {response.text}"
            )

        token_data = response.json()

        # Update connection with new tokens
        connection.access_token = token_data['access_token']
        connection.refresh_token = token_data.get('refresh_token', connection.refresh_token)
        connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
        connection.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(connection)

        return connection.access_token

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing Fitbit token: {str(e)}"
        )


@router.get("/authorize", response_model=FitbitAuthResponse)
async def get_authorization_url():
    """
    Get Fitbit OAuth authorization URL (via Google Health API)
    Fitbit now uses Google OAuth since migration to Google Health API
    """
    if not FITBIT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fitbit integration not configured"
        )

    # Use Google OAuth scopes for Fitbit data access via Google Fitness API
    scope = "https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.location.read https://www.googleapis.com/auth/userinfo.profile"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={FITBIT_CLIENT_ID}"
        f"&redirect_uri={FITBIT_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return FitbitAuthResponse(authorization_url=auth_url)


@router.post("/callback", response_model=FitbitConnectionResponse)
async def handle_oauth_callback(
    request: FitbitCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and exchange code for tokens (Google OAuth for Fitbit)
    """
    try:
        # Use Google OAuth token exchange (Fitbit now uses Google Health API)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "client_id": FITBIT_CLIENT_ID,
                    "client_secret": FITBIT_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "redirect_uri": FITBIT_REDIRECT_URI
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for token: {response.text}"
            )

        token_data = response.json()

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
        # For Google OAuth, use sub (subject) as the user ID
        fitbit_user_id = token_data.get('sub', token_data.get('id', 'unknown'))

        # Check if this fitbit_user_id is already connected to a different user
        existing_user_connection = db.query(FitbitConnection).filter(
            FitbitConnection.fitbit_user_id == fitbit_user_id
        ).first()

        if existing_user_connection and existing_user_connection.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Fitbit account is already connected to another user"
            )

        # Check if connection already exists for this user
        existing_connection = db.query(FitbitConnection).filter(
            FitbitConnection.user_id == current_user.id
        ).first()

        if existing_connection:
            # Update existing connection
            existing_connection.access_token = token_data['access_token']
            existing_connection.refresh_token = token_data['refresh_token']
            existing_connection.expires_at = expires_at
            existing_connection.fitbit_user_id = fitbit_user_id
            existing_connection.scope = token_data.get('scope')
            existing_connection.user_data = json.dumps(token_data)
            existing_connection.is_active = True
            existing_connection.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_connection)
            connection = existing_connection
        else:
            # Create new connection
            connection = FitbitConnection(
                user_id=current_user.id,
                fitbit_user_id=fitbit_user_id,
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                expires_at=expires_at,
                scope=token_data.get('scope'),
                user_data=json.dumps(token_data),
                is_active=True
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)

        # Auto-set as primary if user has no primary sync source
        if not current_user.primary_sync_source:
            current_user.primary_sync_source = "fitbit"
            db.commit()
            logger.info(f"Auto-set fitbit as primary sync source for user {current_user.id}")

        # Get user profile for display name from Google UserInfo API
        user_name = None
        try:
            async with httpx.AsyncClient() as client:
                profile_response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
                    headers={"Authorization": f"Bearer {connection.access_token}"}
                )
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_name = profile_data.get('name') or profile_data.get('given_name', '')
        except Exception as e:
            logger.warning(f"Failed to fetch Google profile: {str(e)}")

        return FitbitConnectionResponse(
            fitbit_user_id=connection.fitbit_user_id,
            is_active=connection.is_active,
            last_sync_at=connection.last_sync_at,
            user_name=user_name
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Fitbit: {str(e)}"
        )


@router.get("/connection", response_model=Optional[FitbitConnectionResponse])
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Fitbit connection status
    """
    connection = db.query(FitbitConnection).filter(
        FitbitConnection.user_id == current_user.id
    ).first()

    if not connection:
        return None

    user_data = json.loads(connection.user_data) if connection.user_data else {}
    user_name = user_data.get('fullName') or user_data.get('displayName')

    return FitbitConnectionResponse(
        fitbit_user_id=connection.fitbit_user_id,
        is_active=connection.is_active,
        last_sync_at=connection.last_sync_at,
        user_name=user_name
    )


@router.delete("/connection")
async def disconnect_fitbit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Fitbit account
    """
    connection = db.query(FitbitConnection).filter(
        FitbitConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Fitbit connection found"
        )

    # If this was the primary sync source, clear it
    if current_user.primary_sync_source == "fitbit":
        current_user.primary_sync_source = None
        logger.info(f"Cleared primary sync source for user {current_user.id} as Fitbit was disconnected")

    db.delete(connection)
    db.commit()

    return {"message": "Fitbit disconnected successfully"}


@router.post("/sync/{challenge_id}", response_model=ChallengeProgressResponse)
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Fitbit for a specific challenge
    """
    # Get Fitbit connection
    connection = db.query(FitbitConnection).filter(
        and_(
            FitbitConnection.user_id == current_user.id,
            FitbitConnection.is_active == True
        )
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Fitbit connection found. Please connect your Fitbit account first."
        )

    # Get challenge details
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    # Check if token needs refresh
    if datetime.now(timezone.utc) >= connection.expires_at:
        await refresh_fitbit_token(connection, db)

    try:
        # Fetch activities from Google Fitness API (Fitbit data flows through Google)
        # Convert dates to nanoseconds timestamp for Google Fitness API
        event_start = challenge.event_date
        event_end = challenge.event_end_date

        if not event_start or not event_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge must have start and end dates"
            )

        # Google Fitness API uses nanoseconds since epoch
        start_time_nanos = int(event_start.timestamp() * 1_000_000_000)
        end_time_nanos = int(event_end.timestamp() * 1_000_000_000)

        # Aggregate distance data from Google Fitness API
        async with httpx.AsyncClient() as client:
            # Request aggregated distance data
            aggregate_response = await client.post(
                "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "aggregateBy": [
                        {
                            "dataTypeName": "com.google.distance.delta",
                            "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta"
                        }
                    ],
                    "bucketByTime": {"durationMillis": int((event_end - event_start).total_seconds() * 1000)},
                    "startTimeMillis": start_time_nanos // 1_000_000,
                    "endTimeMillis": end_time_nanos // 1_000_000
                }
            )

        if aggregate_response.status_code != 200:
            logger.error(f"Failed to fetch fitness data: {aggregate_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch activities from Google Fitness API: {aggregate_response.text}"
            )

        data = aggregate_response.json()

        # Calculate totals from Google Fitness API response
        total_distance_m = 0
        activity_count = 0

        # Extract distance from buckets
        buckets = data.get('bucket', [])
        for bucket in buckets:
            datasets = bucket.get('dataset', [])
            for dataset in datasets:
                points = dataset.get('point', [])
                for point in points:
                    values = point.get('value', [])
                    for value in values:
                        # Distance is in meters
                        distance_m = value.get('fpVal', 0.0)
                        total_distance_m += distance_m
                        if distance_m > 0:
                            activity_count += 1

        total_distance_km = total_distance_m / 1000

        # For duration, we'll use a separate API call to get activity segments
        total_duration_min = 0
        try:
            activity_response = await client.post(
                "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "aggregateBy": [
                        {
                            "dataTypeName": "com.google.activity.segment",
                            "dataSourceId": "derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments"
                        }
                    ],
                    "bucketByTime": {"durationMillis": int((event_end - event_start).total_seconds() * 1000)},
                    "startTimeMillis": start_time_nanos // 1_000_000,
                    "endTimeMillis": end_time_nanos // 1_000_000
                }
            )

            if activity_response.status_code == 200:
                activity_data = activity_response.json()
                buckets = activity_data.get('bucket', [])
                for bucket in buckets:
                    datasets = bucket.get('dataset', [])
                    for dataset in datasets:
                        points = dataset.get('point', [])
                        for point in points:
                            start_time = int(point.get('startTimeNanos', 0))
                            end_time = int(point.get('endTimeNanos', 0))
                            duration_nanos = end_time - start_time
                            duration_minutes = duration_nanos / 1_000_000_000 / 60
                            total_duration_min += int(duration_minutes)
        except Exception as e:
            logger.warning(f"Failed to fetch activity duration: {str(e)}")
            # Duration is optional, continue without it

        # Find user's ActivityProgress for this event
        activity_progress = db.query(ActivityProgress).filter(
            and_(
                ActivityProgress.user_id == current_user.id,
                ActivityProgress.event_id == challenge_id
            )
        ).first()

        sync_time = datetime.now(timezone.utc)

        if activity_progress:
            # Use highest-wins logic
            from app.services.progress_validation_service import ProgressValidationService

            result = ProgressValidationService.validate_and_update_progress(
                progress=activity_progress,
                new_distance_km=total_distance_km,
                source='fitbit',
                metadata={
                    'activity_count': activity_count,
                    'total_distance_meters': total_distance_m,
                    'total_duration_minutes': total_duration_min,
                    'sync_timestamp': sync_time.isoformat()
                }
            )

            # Always update activity count, duration, and last sync time
            # DEPRECATED: activity_progress.get_total_activities() = activity_count
            # DEPRECATED: activity_progress.total_duration_minutes = total_duration_min
            activity_progress.last_sync_at = sync_time

            db.commit()
            db.refresh(activity_progress)

            # Update last sync time on connection
            connection.last_sync_at = datetime.now(timezone.utc)
            db.commit()

            return ChallengeProgressResponse(
                challenge_id=challenge_id,
                total_distance_km=float(activity_progress.distance_completed),
                total_activities=activity_progress.get_total_activities(),
                progress_percentage=float(activity_progress.progress_percentage),
                goal_distance_km=float(activity_progress.target_distance),
                last_activity_date=sync_time,
                current_streak_days=0,
                proof_image_url=activity_progress.proof_image_url,
                last_sync_source=activity_progress.highest_distance_source,
                last_sync_at=activity_progress.highest_distance_set_at
            )
        else:
            # No activity progress found - user hasn't registered for this event yet
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registration found for this event. Please register first."
            )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Fitbit: {str(e)}"
        )


@router.get("/progress/{challenge_id}", response_model=ChallengeProgressResponse)
async def get_challenge_progress(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's progress for a specific challenge (using ActivityProgress)
    """
    activity_progress = db.query(ActivityProgress).filter(
        and_(
            ActivityProgress.user_id == current_user.id,
            ActivityProgress.event_id == challenge_id
        )
    ).first()

    if not activity_progress:
        # Return empty progress
        return ChallengeProgressResponse(
            challenge_id=challenge_id,
            total_distance_km=0.0,
            total_activities=0,
            progress_percentage=0.0,
            goal_distance_km=None,
            last_activity_date=None,
            current_streak_days=0
        )

    return ChallengeProgressResponse(
        challenge_id=challenge_id,
        total_distance_km=float(activity_progress.distance_completed),
        total_activities=activity_progress.get_total_activities(),
        progress_percentage=float(activity_progress.progress_percentage),
        goal_distance_km=float(activity_progress.target_distance),
        last_activity_date=activity_progress.last_sync_at,
        current_streak_days=0,
        proof_image_url=activity_progress.proof_image_url,
        last_sync_source=activity_progress.sync_source,
        last_sync_at=activity_progress.last_sync_at
    )


@router.get("/leaderboard/{challenge_id}", response_model=List[LeaderboardEntry])
async def get_challenge_leaderboard(
    challenge_id: int,
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for a specific challenge (using ActivityProgress)
    """
    # Fetch top performers from ActivityProgress
    progress_entries = db.query(ActivityProgress, User).join(
        User, ActivityProgress.user_id == User.id
    ).filter(
        ActivityProgress.event_id == challenge_id
    ).order_by(
        desc(ActivityProgress.distance_completed)
    ).limit(limit).all()

    leaderboard = []
    for rank, (progress, user) in enumerate(progress_entries, start=1):
        leaderboard.append(LeaderboardEntry(
            user_id=user.id,
            user_name=f"{user.first_name} {user.last_name}",
            total_distance_km=float(progress.distance_completed),
            total_activities=progress.get_total_activities(),
            rank=rank
        ))

    return leaderboard
