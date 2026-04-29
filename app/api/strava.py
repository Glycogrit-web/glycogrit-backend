"""
Strava API Integration Endpoints
Handles OAuth authentication, activity syncing, and progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
import httpx
import os
import json
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.strava_connection import StravaConnection, ChallengeActivity, UserChallengeProgress
from app.models.event import Event
from pydantic import BaseModel


router = APIRouter(prefix="/api/strava", tags=["strava"])


# Pydantic Schemas
class StravaAuthResponse(BaseModel):
    authorization_url: str


class StravaCallbackRequest(BaseModel):
    code: str


class StravaConnectionResponse(BaseModel):
    athlete_id: int
    is_active: bool
    last_sync_at: Optional[datetime]
    athlete_name: Optional[str]


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


# Strava API Configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:5173/auth/strava/callback")


async def refresh_strava_token(connection: StravaConnection, db: Session) -> str:
    """
    Refresh expired Strava access token
    Returns the new access token
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": STRAVA_CLIENT_ID,
                    "client_secret": STRAVA_CLIENT_SECRET,
                    "refresh_token": connection.refresh_token,
                    "grant_type": "refresh_token"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to refresh Strava token: {response.text}"
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
            detail=f"Error refreshing Strava token: {str(e)}"
        )


@router.get("/authorize", response_model=StravaAuthResponse)
async def get_authorization_url():
    """
    Get Strava OAuth authorization URL
    """
    if not STRAVA_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strava integration not configured"
        )

    scope = "activity:read_all,profile:read_all"
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&approval_prompt=auto"
    )

    return StravaAuthResponse(authorization_url=auth_url)


@router.post("/callback", response_model=StravaConnectionResponse)
async def handle_oauth_callback(
    request: StravaCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and exchange code for tokens
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": STRAVA_CLIENT_ID,
                    "client_secret": STRAVA_CLIENT_SECRET,
                    "code": request.code,
                    "grant_type": "authorization_code"
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
        athlete_id = token_data['athlete']['id']

        # Check if this athlete_id is already connected to a different user
        existing_athlete_connection = db.query(StravaConnection).filter(
            StravaConnection.athlete_id == athlete_id
        ).first()

        if existing_athlete_connection and existing_athlete_connection.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Strava account is already connected to another user"
            )

        # Check if connection already exists for this user
        existing_connection = db.query(StravaConnection).filter(
            StravaConnection.user_id == current_user.id
        ).first()

        if existing_connection:
            # Update existing connection
            existing_connection.access_token = token_data['access_token']
            existing_connection.refresh_token = token_data['refresh_token']
            existing_connection.expires_at = expires_at
            existing_connection.athlete_id = athlete_id
            existing_connection.scope = token_data.get('scope')
            existing_connection.athlete_data = json.dumps(token_data['athlete'])
            existing_connection.is_active = True
            existing_connection.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_connection)
            connection = existing_connection
        else:
            # Create new connection
            connection = StravaConnection(
                user_id=current_user.id,
                athlete_id=athlete_id,
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                expires_at=expires_at,
                scope=token_data.get('scope'),
                athlete_data=json.dumps(token_data['athlete']),
                is_active=True
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)

        athlete = token_data['athlete']
        athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

        return StravaConnectionResponse(
            athlete_id=connection.athlete_id,
            is_active=connection.is_active,
            last_sync_at=connection.last_sync_at,
            athlete_name=athlete_name or None
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Strava: {str(e)}"
        )


@router.get("/connection", response_model=Optional[StravaConnectionResponse])
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Strava connection status
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()

    if not connection:
        return None

    athlete_data = json.loads(connection.athlete_data) if connection.athlete_data else {}
    athlete_name = f"{athlete_data.get('firstname', '')} {athlete_data.get('lastname', '')}".strip()

    return StravaConnectionResponse(
        athlete_id=connection.athlete_id,
        is_active=connection.is_active,
        last_sync_at=connection.last_sync_at,
        athlete_name=athlete_name or None
    )


@router.delete("/connection")
async def disconnect_strava(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Strava account
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava connection found"
        )

    db.delete(connection)
    db.commit()

    return {"message": "Strava disconnected successfully"}


@router.post("/sync/{challenge_id}", response_model=ChallengeProgressResponse)
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Strava for a specific challenge
    """
    # Get Strava connection
    connection = db.query(StravaConnection).filter(
        and_(
            StravaConnection.user_id == current_user.id,
            StravaConnection.is_active == True
        )
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Strava connection found. Please connect your Strava account first."
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
        await refresh_strava_token(connection, db)

    try:
        # Fetch activities from Strava within event window
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {connection.access_token}"},
                params={
                    "after": int(challenge.event_date.timestamp()) if challenge.event_date else None,
                    "before": int(challenge.event_end_date.timestamp()) if challenge.event_end_date else None,
                    "per_page": 200
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch activities from Strava: {response.text}"
            )

        activities = response.json()

        # Clear existing activities - "last sync wins" approach
        # This ensures Strava data replaces any previous data (Apple Health, admin, etc.)
        db.query(ChallengeActivity).filter(
            and_(
                ChallengeActivity.challenge_id == challenge_id,
                ChallengeActivity.user_id == current_user.id
            )
        ).delete()

        # Add all activities from current sync
        for activity in activities:
            activity_date = datetime.fromisoformat(activity['start_date'].replace('Z', '+00:00'))

            # Double-check activity is within event window
            if challenge.event_date and activity_date < challenge.event_date:
                continue
            if challenge.event_end_date and activity_date > challenge.event_end_date:
                continue

            challenge_activity = ChallengeActivity(
                challenge_id=challenge_id,
                user_id=current_user.id,
                strava_connection_id=connection.id,
                source_provider='strava',
                external_activity_id=str(activity['id']),
                strava_activity_id=activity['id'],
                activity_type=activity['type'],
                activity_name=activity['name'],
                distance_meters=int(activity.get('distance', 0)),
                duration_seconds=int(activity.get('moving_time', 0)),
                elevation_gain_meters=int(activity.get('total_elevation_gain', 0)),
                average_speed=int(activity.get('average_speed', 0)),
                max_speed=int(activity.get('max_speed', 0)),
                activity_date=activity_date
            )
            db.add(challenge_activity)

        # Calculate total progress from ALL activities for this challenge
        # After sync, all activities are from the current source (last sync wins)
        all_challenge_activities = db.query(ChallengeActivity).filter(
            and_(
                ChallengeActivity.challenge_id == challenge_id,
                ChallengeActivity.user_id == current_user.id
            )
        ).all()

        # Sum up all distances (in meters) and count activities
        total_distance_m = sum(activity.distance_meters for activity in all_challenge_activities)
        activity_count = len(all_challenge_activities)

        # Update progress
        progress = db.query(UserChallengeProgress).filter(
            and_(
                UserChallengeProgress.user_id == current_user.id,
                UserChallengeProgress.challenge_id == challenge_id
            )
        ).first()

        total_distance_km = total_distance_m / 1000
        goal_distance = float(challenge.total_distance) if challenge.total_distance else 0
        progress_pct = (total_distance_km / goal_distance * 100) if goal_distance > 0 else 0

        sync_time = datetime.now(timezone.utc)

        if progress:
            progress.total_distance_km = int(total_distance_km)
            progress.total_activities = activity_count
            progress.progress_percentage = int(min(progress_pct, 100))
            progress.last_activity_date = sync_time
            progress.last_sync_source = 'strava'  # Track sync source
            progress.last_sync_at = sync_time  # Track sync time
            progress.last_synced_by_user_id = current_user.id  # Track who synced
            progress.updated_at = sync_time
        else:
            progress = UserChallengeProgress(
                user_id=current_user.id,
                challenge_id=challenge_id,
                total_distance_km=int(total_distance_km),
                total_activities=activity_count,
                goal_distance_km=goal_distance,
                progress_percentage=int(min(progress_pct, 100)),
                last_activity_date=sync_time,
                last_sync_source='strava',  # Track sync source
                last_sync_at=sync_time,  # Track sync time
                last_synced_by_user_id=current_user.id  # Track who synced
            )
            db.add(progress)

        # Update last sync time
        connection.last_sync_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(progress)

        return ChallengeProgressResponse(
            challenge_id=challenge_id,
            total_distance_km=float(progress.total_distance_km),
            total_activities=progress.total_activities,
            progress_percentage=float(progress.progress_percentage),
            goal_distance_km=float(progress.goal_distance_km) if progress.goal_distance_km else None,
            last_activity_date=progress.last_activity_date,
            current_streak_days=progress.current_streak_days,
            proof_image_url=progress.proof_image_url,
            last_sync_source=progress.last_sync_source,
            last_sync_at=progress.last_sync_at
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Strava: {str(e)}"
        )


@router.get("/progress/{challenge_id}", response_model=ChallengeProgressResponse)
async def get_challenge_progress(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's progress for a specific challenge
    """
    progress = db.query(UserChallengeProgress).filter(
        and_(
            UserChallengeProgress.user_id == current_user.id,
            UserChallengeProgress.challenge_id == challenge_id
        )
    ).first()

    if not progress:
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
        total_distance_km=float(progress.total_distance_km),
        total_activities=progress.total_activities,
        progress_percentage=float(progress.progress_percentage),
        goal_distance_km=float(progress.goal_distance_km) if progress.goal_distance_km else None,
        last_activity_date=progress.last_activity_date,
        current_streak_days=progress.current_streak_days,
        proof_image_url=progress.proof_image_url,
        last_sync_source=progress.last_sync_source,
        last_sync_at=progress.last_sync_at
    )


@router.get("/leaderboard/{challenge_id}", response_model=List[LeaderboardEntry])
async def get_challenge_leaderboard(
    challenge_id: int,
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for a specific challenge
    """
    # Fetch top performers
    progress_entries = db.query(UserChallengeProgress, User).join(
        User, UserChallengeProgress.user_id == User.id
    ).filter(
        UserChallengeProgress.challenge_id == challenge_id
    ).order_by(
        desc(UserChallengeProgress.total_distance_km)
    ).limit(limit).all()

    leaderboard = []
    for rank, (progress, user) in enumerate(progress_entries, start=1):
        leaderboard.append(LeaderboardEntry(
            user_id=user.id,
            user_name=f"{user.first_name} {user.last_name}",
            total_distance_km=float(progress.total_distance_km),
            total_activities=progress.total_activities,
            rank=rank
        ))

    return leaderboard
