"""
Admin Rewards API Endpoints
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.modules.rewards.schemas.reward import RewardResponse
from app.modules.rewards.services.reward_service import RewardService

router = APIRouter(prefix="/admin/rewards", tags=["admin-rewards"])


@router.post(
    "/events/{event_id}/users/{user_id}/registrations/{registration_id}/unlock",
    response_model=RewardResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_unlock_reward(
    event_id: int,
    user_id: int,
    registration_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin unlocks a physical reward for a user.

    This creates a UserReward record in 'pending_details' status,
    allowing the user to claim it and provide shipping details.

    Business Rules:
    1. Admin only endpoint
    2. Registration must exist and match event_id/user_id
    3. One reward per registration
    4. Reward created in 'pending_details' status (user must provide shipping address)

    Process:
    - Creates UserReward record with status='pending_details'
    - User can then claim and provide shipping details
    - After shipping details provided, status changes to 'pending_shipment'
    """
    service = RewardService(db)

    reward = service.admin_unlock_reward(
        event_id=event_id,
        user_id=user_id,
        registration_id=registration_id,
    )

    return RewardResponse.model_validate(reward)
