"""
Wahoo Fitness API Integration Endpoints
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
from app.models.wahoo_connection import WahooConnection
from app.models.activity_progress import ActivityProgress
from app.models.registration import Registration
from app.models.event import Event
from pydantic import BaseModel


router = APIRouter(prefix="/api/wahoo", tags=["wahoo"])
logger = logging.getLogger(__name__)


# Pydantic Schemas
class WahooAuthResponse(BaseModel):
    authorization_url: str


class WahooCallbackRequest(BaseModel):
    code: str


class WahooConnectionResponse(BaseModel):
    wahoo_user_id: str
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


# Wahoo API Configuration
WAHOO_CLIENT_ID = os.getenv("WAHOO_CLIENT_ID")
WAHOO_CLIENT_SECRET = os.getenv("WAHOO_CLIENT_SECRET")
WAHOO_REDIRECT_URI = os.getenv("WAHOO_REDIRECT_URI", "http://localhost:5173/auth/wahoo/callback")

# Wahoo API endpoints
WAHOO_AUTH_URL = "https://api.wahooligan.com/oauth/authorize"
WAHOO_TOKEN_URL = "https://api.wahooligan.com/oauth/token"
WAHOO_API_BASE = "https://api.wahooligan.com/v1"


async def refresh_wahoo_token(connection: WahooConnection, db: Session) -> str:
    """
    Refresh expired Wahoo access token
    Returns the new access token
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WAHOO_TOKEN_URL,
                data={
                    "client_id": WAHOO_CLIENT_ID,
                    "client_secret": WAHOO_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": connection.refresh_token
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to refresh Wahoo token: {response.text}"
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
            detail=f"Error refreshing Wahoo token: {str(e)}"
        )


@router.get("/authorize", response_model=WahooAuthResponse)
async def get_authorization_url():
    """
    Get Wahoo OAuth authorization URL
    """
    if not WAHOO_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Wahoo integration not configured"
        )

    scope = "workouts_read user_read"
    auth_url = (
        f"{WAHOO_AUTH_URL}"
        f"?client_id={WAHOO_CLIENT_ID}"
        f"&redirect_uri={WAHOO_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
    )

    return WahooAuthResponse(authorization_url=auth_url)


@router.post("/callback", response_model=WahooConnectionResponse)
async def handle_oauth_callback(
    request: WahooCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and exchange code for tokens
    """
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WAHOO_TOKEN_URL,
                data={
                    "client_id": WAHOO_CLIENT_ID,
                    "client_secret": WAHOO_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "redirect_uri": WAHOO_REDIRECT_URI
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for token: {response.text}"
            )

        token_data = response.json()

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600))

        # Get user profile
        async with httpx.AsyncClient() as client:
            profile_response = await client.get(
                f"{WAHOO_API_BASE}/user",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )

        if profile_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch Wahoo user profile: {profile_response.text}"
            )

        user_profile = profile_response.json()
        wahoo_user_id = str(user_profile.get('id'))

        # Check if this wahoo_user_id is already connected to a different user
        existing_user_connection = db.query(WahooConnection).filter(
            WahooConnection.wahoo_user_id == wahoo_user_id
        ).first()

        if existing_user_connection and existing_user_connection.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Wahoo account is already connected to another user"
            )

        # Check if connection already exists for this user
        existing_connection = db.query(WahooConnection).filter(
            WahooConnection.user_id == current_user.id
        ).first()

        if existing_connection:
            # Update existing connection
            existing_connection.access_token = token_data['access_token']
            existing_connection.refresh_token = token_data['refresh_token']
            existing_connection.expires_at = expires_at
            existing_connection.wahoo_user_id = wahoo_user_id
            existing_connection.scope = token_data.get('scope')
            existing_connection.user_data = json.dumps(user_profile)
            existing_connection.is_active = True
            existing_connection.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_connection)
            connection = existing_connection
        else:
            # Create new connection
            connection = WahooConnection(
                user_id=current_user.id,
                wahoo_user_id=wahoo_user_id,
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                expires_at=expires_at,
                scope=token_data.get('scope'),
                user_data=json.dumps(user_profile),
                is_active=True
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)

        # Auto-set as primary if user has no primary sync source
        if not current_user.primary_sync_source:
            current_user.primary_sync_source = "wahoo"
            db.commit()
            logger.info(f"Auto-set wahoo as primary sync source for user {current_user.id}")

        # Get user name from profile
        user_name = f"{user_profile.get('first', '')} {user_profile.get('last', '')}".strip()

        return WahooConnectionResponse(
            wahoo_user_id=connection.wahoo_user_id,
            is_active=connection.is_active,
            last_sync_at=connection.last_sync_at,
            user_name=user_name
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Wahoo: {str(e)}"
        )


@router.get("/connection", response_model=Optional[WahooConnectionResponse])
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Wahoo connection status
    """
    connection = db.query(WahooConnection).filter(
        WahooConnection.user_id == current_user.id
    ).first()

    if not connection:
        return None

    user_data = json.loads(connection.user_data) if connection.user_data else {}
    user_name = f"{user_data.get('first', '')} {user_data.get('last', '')}".strip()

    return WahooConnectionResponse(
        wahoo_user_id=connection.wahoo_user_id,
        is_active=connection.is_active,
        last_sync_at=connection.last_sync_at,
        user_name=user_name
    )


@router.delete("/connection")
async def disconnect_wahoo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Wahoo account
    """
    connection = db.query(WahooConnection).filter(
        WahooConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Wahoo connection found"
        )

    # If this was the primary sync source, clear it
    if current_user.primary_sync_source == "wahoo":
        current_user.primary_sync_source = None
        logger.info(f"Cleared primary sync source for user {current_user.id} as Wahoo was disconnected")

    db.delete(connection)
    db.commit()

    return {"message": "Wahoo disconnected successfully"}


@router.post("/sync/{challenge_id}", response_model=ChallengeProgressResponse)
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Wahoo for a specific challenge
    """
    # Get Wahoo connection
    connection = db.query(WahooConnection).filter(
        and_(
            WahooConnection.user_id == current_user.id,
            WahooConnection.is_active == True
        )
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Wahoo connection found. Please connect your Wahoo account first."
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
        await refresh_wahoo_token(connection, db)

    try:
        # Fetch workouts from Wahoo within event window
        start_date = challenge.event_date.strftime('%Y-%m-%d') if challenge.event_date else None
        end_date = challenge.event_end_date.strftime('%Y-%m-%d') if challenge.event_end_date else None

        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge must have start and end dates"
            )

        # Get workouts list for the date range
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{WAHOO_API_BASE}/workouts",
                headers={"Authorization": f"Bearer {connection.access_token}"},
                params={
                    "starts_after": start_date,
                    "starts_before": end_date,
                    "per_page": 100
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch workouts from Wahoo: {response.text}"
            )

        data = response.json()
        workouts = data.get('workouts', [])

        # Calculate totals directly from Wahoo API response
        total_distance_m = 0
        activity_count = 0
        total_duration_sec = 0

        event_start = challenge.event_date
        event_end = challenge.event_end_date

        for workout in workouts:
            # Parse workout date
            workout_date_str = workout.get('starts')
            if not workout_date_str:
                continue

            workout_date = datetime.fromisoformat(workout_date_str.replace('Z', '+00:00'))

            # Filter workouts within event window
            if event_start and workout_date < event_start:
                continue
            if event_end and workout_date > event_end:
                continue

            # Aggregate totals (distance is in meters)
            distance = float(workout.get('distance_meters', 0))
            total_distance_m += distance
            total_duration_sec += int(workout.get('duration_seconds', 0))
            activity_count += 1

        total_distance_km = total_distance_m / 1000
        total_duration_min = total_duration_sec // 60

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
                source='wahoo',
                metadata={
                    'activity_count': activity_count,
                    'total_distance_meters': total_distance_m,
                    'total_duration_minutes': total_duration_min,
                    'sync_timestamp': sync_time.isoformat()
                }
            )

            # Always update activity count, duration, and last sync time
            activity_progress.total_activities = activity_count
            activity_progress.total_duration_minutes = total_duration_min
            activity_progress.last_sync_at = sync_time

            db.commit()
            db.refresh(activity_progress)

            # Update last sync time on connection
            connection.last_sync_at = datetime.now(timezone.utc)
            db.commit()

            return ChallengeProgressResponse(
                challenge_id=challenge_id,
                total_distance_km=float(activity_progress.distance_completed),
                total_activities=activity_progress.total_activities,
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
            detail=f"Error communicating with Wahoo: {str(e)}"
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
        total_activities=activity_progress.total_activities,
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
            total_activities=progress.total_activities,
            rank=rank
        ))

    return leaderboard
