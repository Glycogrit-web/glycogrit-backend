"""
Challenges API Endpoints
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.challenges.services.challenge_service import ChallengeService
from app.modules.challenges.schemas.challenge import (
    ChallengeProgressResponse,
    ChallengeJoinRequest,
    ChallengeJoinResponse,
)

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get("/{event_id}/progress", response_model=ChallengeProgressResponse)
def get_challenge_progress(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's progress in a challenge

    Returns:
    - Current distance vs target
    - Progress percentage
    - Activity count
    - Streak days
    """
    service = ChallengeService(db)
    progress = service.get_challenge_progress(
        user_id=current_user.id,
        event_id=event_id
    )
    return ChallengeProgressResponse(**progress)


@router.post("/{event_id}/join", response_model=ChallengeJoinResponse, status_code=status.HTTP_201_CREATED)
def join_challenge(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Join a challenge

    Business Rules:
    1. User can only join once
    2. Challenge must be active
    3. Creates registration record

    Returns:
    - Registration details
    """
    service = ChallengeService(db)
    registration = service.join_challenge(
        user_id=current_user.id,
        event_id=event_id
    )

    return ChallengeJoinResponse(
        registration_id=registration.id,
        event_id=registration.event_id,
        user_id=registration.user_id,
        status=registration.status,
        message="Successfully joined the challenge!"
    )


@router.get("/my", response_model=List[ChallengeProgressResponse])
def get_my_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all challenges the current user is participating in

    Returns list of challenge progress for all joined challenges
    """
    from app.modules.registrations.domain.registration import Registration
    from sqlalchemy import and_

    # Get all registrations for user where event is a challenge type
    registrations = db.query(Registration).filter(
        Registration.user_id == current_user.id
    ).all()

    service = ChallengeService(db)
    challenges = []

    for reg in registrations:
        try:
            progress = service.get_challenge_progress(
                user_id=current_user.id,
                event_id=reg.event_id
            )
            challenges.append(ChallengeProgressResponse(**progress))
        except Exception:
            # Skip if not a challenge or error occurred
            continue

    return challenges


@router.delete("/{event_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_challenge(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Leave a challenge (cancel registration)

    Note: This will cancel the registration but preserve historical data
    """
    from app.modules.registrations.domain.registration import Registration
    from app.core.enums import RegistrationStatus
    from app.core.exceptions import NotFoundException

    registration = db.query(Registration).filter(
        and_(
            Registration.user_id == current_user.id,
            Registration.event_id == event_id
        )
    ).first()

    if not registration:
        raise NotFoundException("Registration", "user_id/event_id", f"{current_user.id}/{event_id}")

    registration.status = RegistrationStatus.CANCELLED.value
    db.commit()

    return None
