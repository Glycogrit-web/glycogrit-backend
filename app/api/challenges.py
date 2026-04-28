"""
Challenge API Endpoints
Handles challenge progress tracking and evaluation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.event import Event
from app.models.strava_connection import UserChallengeProgress
from app.services.challenge_evaluation_service import ChallengeEvaluationService
from app.services.challenge_scheduler import ChallengeSchedulerService
from app.services.activity_sync_service import ActivitySyncService
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/challenges", tags=["Challenges"])


# Request/Response Models
class ChallengeProgressResponse(BaseModel):
    challenge_id: int
    challenge_name: str
    total_distance_km: int
    goal_distance_km: int
    progress_percentage: int
    total_activities: int
    current_streak_days: int
    completion_status: Optional[str] = None
    badge_earned: Optional[str] = None
    last_activity_date: Optional[str] = None
    proof_image_url: Optional[str] = None
    last_sync_source: Optional[str] = None
    last_sync_at: Optional[str] = None


class JoinChallengeRequest(BaseModel):
    challenge_id: int


@router.get("/{challenge_id}/progress", response_model=ChallengeProgressResponse)
async def get_challenge_progress(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's progress in a challenge
    """
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    progress = db.query(UserChallengeProgress).filter(
        UserChallengeProgress.user_id == current_user.id,
        UserChallengeProgress.challenge_id == challenge_id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not registered for this challenge"
        )

    return {
        "challenge_id": challenge_id,
        "challenge_name": challenge.name,
        "total_distance_km": progress.total_distance_km,
        "goal_distance_km": progress.goal_distance_km,
        "progress_percentage": progress.progress_percentage,
        "total_activities": progress.total_activities,
        "current_streak_days": progress.current_streak_days,
        "completion_status": progress.completion_status,
        "badge_earned": progress.badge_earned,
        "last_activity_date": progress.last_activity_date.isoformat() if progress.last_activity_date else None,
        "proof_image_url": progress.proof_image_url,
        "last_sync_source": progress.last_sync_source,
        "last_sync_at": progress.last_sync_at.isoformat() if progress.last_sync_at else None
    }


@router.post("/join")
async def join_challenge(
    request: JoinChallengeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Join a challenge and initialize progress tracking
    """
    challenge = db.query(Event).filter(Event.id == request.challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    # Check if already joined
    existing = db.query(UserChallengeProgress).filter(
        UserChallengeProgress.user_id == current_user.id,
        UserChallengeProgress.challenge_id == request.challenge_id
    ).first()

    if existing:
        return {
            "message": "Already joined this challenge",
            "progress_id": existing.id
        }

    # Initialize progress tracking
    scheduler_service = ChallengeSchedulerService(db)
    progress = scheduler_service.initialize_user_progress(current_user.id, request.challenge_id)

    # If challenge should have started, sync activities immediately
    if scheduler_service.check_should_auto_start_now(request.challenge_id):
        sync_service = ActivitySyncService(db)
        try:
            await sync_service.sync_user_activities(
                user_id=current_user.id,
                challenge_id=request.challenge_id
            )
        except Exception as e:
            logger.error(f"Error syncing activities after joining: {e}")

    return {
        "message": "Successfully joined challenge",
        "progress_id": progress.id,
        "challenge_id": request.challenge_id
    }


@router.get("/{challenge_id}/leaderboard")
async def get_leaderboard(
    challenge_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for a challenge
    """
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    evaluation_service = ChallengeEvaluationService(db)
    leaderboard = evaluation_service.get_leaderboard(challenge_id, limit)

    return {
        "challenge_id": challenge_id,
        "challenge_name": challenge.name,
        "leaderboard": leaderboard
    }


@router.get("/{challenge_id}/statistics")
async def get_challenge_statistics(
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """
    Get completion statistics for a challenge
    """
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    evaluation_service = ChallengeEvaluationService(db)
    stats = evaluation_service.get_completion_statistics(challenge_id)

    return {
        "challenge_id": challenge_id,
        "challenge_name": challenge.name,
        "statistics": stats
    }


@router.post("/{challenge_id}/evaluate")
async def evaluate_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger evaluation for a challenge (admin only in production)

    For POC: any user can trigger
    """
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    evaluation_service = ChallengeEvaluationService(db)

    try:
        results = evaluation_service.evaluate_challenge(challenge_id)
        return {
            "message": "Evaluation completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error evaluating challenge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/my-challenges")
async def get_my_challenges(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by challenge status: ongoing, upcoming, completed"),
    db: Session = Depends(get_db)
):
    """
    Get all challenges current user is participating in with optional status filter
    """
    from datetime import datetime, timezone

    progress_records = db.query(UserChallengeProgress).filter(
        UserChallengeProgress.user_id == current_user.id
    ).all()

    results = {
        "ongoing": [],
        "upcoming": [],
        "completed": []
    }

    now = datetime.now(timezone.utc).date()

    for progress in progress_records:
        challenge = db.query(Event).filter(Event.id == progress.challenge_id).first()
        if not challenge:
            continue

        # Determine challenge status based on dates
        challenge_status = "completed"
        if challenge.end_date and challenge.end_date < now:
            challenge_status = "completed"
        elif challenge.start_date and challenge.start_date > now:
            challenge_status = "upcoming"
        elif challenge.start_date and challenge.end_date and challenge.start_date <= now <= challenge.end_date:
            challenge_status = "ongoing"

        challenge_data = {
            "challenge_id": challenge.id,
            "challenge_name": challenge.name,
            "challenge_status": challenge_status,
            "start_date": challenge.start_date.isoformat() if challenge.start_date else None,
            "end_date": challenge.end_date.isoformat() if challenge.end_date else None,
            "banner_image_url": challenge.banner_image_url,
            "total_distance_km": progress.total_distance_km,
            "goal_distance_km": progress.goal_distance_km,
            "progress_percentage": progress.progress_percentage,
            "total_activities": progress.total_activities,
            "current_streak_days": progress.current_streak_days,
            "completion_status": progress.completion_status,
            "badge_earned": progress.badge_earned,
            "last_activity_date": progress.last_activity_date.isoformat() if progress.last_activity_date else None,
            "proof_image_url": progress.proof_image_url,
            "last_sync_source": progress.last_sync_source,
            "last_sync_at": progress.last_sync_at.isoformat() if progress.last_sync_at else None
        }

        results[challenge_status].append(challenge_data)

    # If status filter is provided, return only that category
    if status:
        return {
            "challenges": results.get(status, []),
            "filter": status
        }

    # Otherwise return all categories
    return results


@router.post("/{challenge_id}/activities/sync")
async def sync_challenge_activities(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities for current user in specific challenge
    """
    challenge = db.query(Event).filter(Event.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )

    sync_service = ActivitySyncService(db)

    try:
        results = await sync_service.sync_user_activities(
            user_id=current_user.id,
            challenge_id=challenge_id,
            force=True
        )

        return {
            "message": "Activities synced successfully",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error syncing challenge activities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync activities"
        )
