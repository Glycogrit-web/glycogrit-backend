"""
Google Fit API Integration Endpoints
Handles OAuth authentication, activity syncing, and progress tracking
Similar structure to Strava integration for consistency
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
import httpx
import os
import json
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.activity_progress import ActivityProgress
from app.models.event import Event
from pydantic import BaseModel

router = APIRouter(prefix="/api/google-fit", tags=["google-fit"])


# Pydantic Schemas
class GoogleFitAuthResponse(BaseModel):
    authorization_url: str


class GoogleFitCallbackRequest(BaseModel):
    code: str


class GoogleFitConnectionResponse(BaseModel):
    user_id: str
    is_active: bool
    last_sync_at: Optional[datetime]
    user_email: Optional[str]


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


# Google Fit API Configuration
GOOGLE_FIT_CLIENT_ID = os.getenv("GOOGLE_FIT_CLIENT_ID")
GOOGLE_FIT_CLIENT_SECRET = os.getenv("GOOGLE_FIT_CLIENT_SECRET")
GOOGLE_FIT_REDIRECT_URI = os.getenv("GOOGLE_FIT_REDIRECT_URI", "http://localhost:5173/auth/google-fit/callback")


async def refresh_google_fit_token(connection: FitnessTrackerConnection, db: Session) -> str:
    """
    Refresh expired Google Fit access token
    Returns the new access token
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_FIT_CLIENT_ID,
                    "client_secret": GOOGLE_FIT_CLIENT_SECRET,
                    "refresh_token": connection.refresh_token,
                    "grant_type": "refresh_token"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to refresh Google Fit token: {response.text}"
            )

        token_data = response.json()

        # Update connection with new tokens
        connection.access_token = token_data['access_token']
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600))
        connection.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(connection)

        return connection.access_token

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing Google Fit token: {str(e)}"
        )


@router.get("/authorize", response_model=GoogleFitAuthResponse)
async def get_authorization_url():
    """
    Get Google Fit OAuth authorization URL
    """
    if not GOOGLE_FIT_CLIENT_ID:
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
        f"?client_id={GOOGLE_FIT_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_FIT_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"  # Gets refresh token
        f"&prompt=consent"  # Force consent to get refresh token
    )

    return GoogleFitAuthResponse(authorization_url=auth_url)


@router.post("/callback", response_model=GoogleFitConnectionResponse)
async def handle_oauth_callback(
    request: GoogleFitCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and exchange code for tokens
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_FIT_CLIENT_ID,
                    "client_secret": GOOGLE_FIT_CLIENT_SECRET,
                    "code": request.code,
                    "redirect_uri": GOOGLE_FIT_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange authorization code: {response.text}"
            )

        token_data = response.json()

        if 'refresh_token' not in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token received. Please revoke access and reconnect."
            )

        # Get user info
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_info = user_info_response.json()

        user_email = user_info.get('email')
        google_user_id = user_info.get('id')
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600))

        # Verify this is the same Google account user logged in with (if applicable)
        if current_user.oauth_provider == 'google' and current_user.oauth_id:
            if current_user.oauth_id != google_user_id:
                logger.warning(
                    f"User {current_user.id} logged in with Google account {current_user.oauth_id} "
                    f"but trying to connect Google Fit with different account {google_user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please connect Google Fit using the same Google account you used to login. "
                           f"You logged in as {current_user.email}, but selected a different Google account."
                )
            else:
                logger.info(f"User {current_user.id} connecting Google Fit with same Google account used for login ✓")

        # Check if connection already exists
        existing = db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == current_user.id,
                FitnessTrackerConnection.provider == 'google_fit'
            )
        ).first()

        if existing:
            # Update existing connection
            existing.access_token = token_data['access_token']
            existing.refresh_token = token_data['refresh_token']
            existing.token_expires_at = expires_at
            existing.scope = token_data.get('scope')
            existing.provider_user_id = google_user_id
            existing.provider_data = json.dumps({'email': user_email, 'user_info': user_info})
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            connection = existing
        else:
            # Create new connection
            connection = FitnessTrackerConnection(
                user_id=current_user.id,
                provider='google_fit',
                provider_user_id=google_user_id,
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_expires_at=expires_at,
                scope=token_data.get('scope'),
                provider_data=json.dumps({'email': user_email, 'user_info': user_info}),
                is_active=True
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)

        return GoogleFitConnectionResponse(
            user_id=google_user_id,
            is_active=connection.is_active,
            last_sync_at=connection.last_sync_at,
            user_email=user_email
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Google: {str(e)}"
        )


@router.get("/connection", response_model=Optional[GoogleFitConnectionResponse])
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Google Fit connection status
    """
    connection = db.query(FitnessTrackerConnection).filter(
        and_(
            FitnessTrackerConnection.user_id == current_user.id,
            FitnessTrackerConnection.provider == 'google_fit'
        )
    ).first()

    if not connection:
        return None

    provider_data = json.loads(connection.provider_data) if connection.provider_data else {}
    user_email = provider_data.get('email')

    return GoogleFitConnectionResponse(
        user_id=connection.provider_user_id or "unknown",
        is_active=connection.is_active,
        last_sync_at=connection.last_sync_at,
        user_email=user_email
    )


@router.delete("/connection")
async def disconnect_google_fit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Google Fit account
    """
    connection = db.query(FitnessTrackerConnection).filter(
        and_(
            FitnessTrackerConnection.user_id == current_user.id,
            FitnessTrackerConnection.provider == 'google_fit'
        )
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Google Fit connection found"
        )

    # Revoke token with Google
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://oauth2.googleapis.com/revoke",
                params={"token": connection.access_token}
            )
    except Exception:
        pass  # Continue even if revocation fails

    db.delete(connection)
    db.commit()

    return {"message": "Google Fit disconnected successfully"}


@router.post("/sync/{challenge_id}", response_model=ChallengeProgressResponse)
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Google Fit for a specific challenge
    """
    # Get Google Fit connection
    connection = db.query(FitnessTrackerConnection).filter(
        and_(
            FitnessTrackerConnection.user_id == current_user.id,
            FitnessTrackerConnection.provider == 'google_fit',
            FitnessTrackerConnection.is_active == True
        )
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Fit connection found. Please connect your Google Fit account first."
        )

    # Get challenge details
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    # Check if token needs refresh
    if datetime.now(timezone.utc) >= connection.token_expires_at:
        await refresh_google_fit_token(connection, db)

    try:
        # Fetch activities from Google Fit within event window
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Format dates properly for Google Fit API (RFC3339 format)
            # Ensure datetime has timezone info
            if challenge.event_date:
                if challenge.event_date.tzinfo is None:
                    start_dt = challenge.event_date.replace(tzinfo=timezone.utc)
                else:
                    start_dt = challenge.event_date
            else:
                start_dt = datetime.now(timezone.utc)

            if challenge.event_end_date:
                if challenge.event_end_date.tzinfo is None:
                    end_dt = challenge.event_end_date.replace(tzinfo=timezone.utc)
                else:
                    end_dt = challenge.event_end_date
            else:
                end_dt = datetime.now(timezone.utc)

            # Format to RFC3339 with 'Z' suffix for UTC
            start_time = start_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            end_time = end_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            response = await client.get(
                "https://www.googleapis.com/fitness/v1/users/me/sessions",
                headers={"Authorization": f"Bearer {connection.access_token}"},
                params={
                    "startTime": start_time,
                    "endTime": end_time,
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch activities from Google Fit: {response.text}"
            )

        sessions = response.json()

        # Calculate totals directly from Google Fit API response
        # No need to store individual activities - just aggregate progress
        total_distance_m = 0
        activity_count = 0
        total_duration_sec = 0

        # Process all sessions and aggregate totals
        for session in sessions.get('session', []):
            try:
                # Parse session data
                start_time_ms = int(session.get('startTimeMillis', 0))
                end_time_ms = int(session.get('endTimeMillis', 0))
                activity_date = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)

                # Double-check activity is within event window
                if challenge.event_date and activity_date < challenge.event_date:
                    continue
                if challenge.event_end_date and activity_date > challenge.event_end_date:
                    continue

                # Calculate duration
                duration_seconds = (end_time_ms - start_time_ms) // 1000

                # Fetch distance from datasets API
                distance_meters = 0
                try:
                    dataset_response = await client.post(
                        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                        headers={"Authorization": f"Bearer {connection.access_token}"},
                        json={
                            "aggregateBy": [{
                                "dataTypeName": "com.google.distance.delta",
                                "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta"
                            }],
                            "bucketByTime": {"durationMillis": end_time_ms - start_time_ms},
                            "startTimeMillis": start_time_ms,
                            "endTimeMillis": end_time_ms
                        }
                    )

                    if dataset_response.status_code == 200:
                        dataset_data = dataset_response.json()
                        for bucket in dataset_data.get("bucket", []):
                            for dataset in bucket.get("dataset", []):
                                for point in dataset.get("point", []):
                                    for value in point.get("value", []):
                                        if "fpVal" in value:
                                            distance_meters += value["fpVal"]
                except Exception as dist_error:
                    logger.warning(f"Failed to fetch distance for session: {dist_error}")

                # Aggregate totals
                total_distance_m += distance_meters
                total_duration_sec += duration_seconds
                activity_count += 1

            except Exception as e:
                import logging
                logging.error(f"Error processing Google Fit session: {e}")
                continue

        # Convert aggregated totals
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
                source='google_fit',
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
            # No activity progress found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registration found for this event. Please register first."
            )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with Google Fit: {str(e)}"
        )


def _map_google_fit_activity_type(activity_code: int) -> str:
    """Map Google Fit activity type codes to readable names"""
    activity_map = {
        1: "Biking",
        8: "Running",
        7: "Walking",
        79: "Hiking",
        82: "Swimming",
        9: "Aerobics",
        93: "Yoga",
        10: "Basketball",
        11: "Volleyball"
    }
    return activity_map.get(activity_code, "Workout")


@router.get("/progress/{challenge_id}", response_model=ChallengeProgressResponse)
async def get_challenge_progress(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's progress for a specific challenge (Google Fit sourced)
    """
    activity_progress = db.query(ActivityProgress).filter(
        and_(
            ActivityProgress.user_id == current_user.id,
            ActivityProgress.event_id == challenge_id
        )
    ).first()

    if not activity_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress found for this challenge"
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
        last_sync_source=activity_progress.highest_distance_source,
        last_sync_at=activity_progress.highest_distance_set_at
    )


@router.post("/sync-all")
async def sync_all_challenges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Google Fit for all user's active challenges
    This is useful for automatic background syncing
    """
    from app.services.background_sync_service import trigger_manual_sync

    result = await trigger_manual_sync(db, user_id=current_user.id, provider='google_fit')

    return {
        "message": "Sync triggered for all challenges",
        "result": result
    }
