"""
Reward Service

Business logic for physical reward fulfillment via Shiprocket.
"""

import logging

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.enums import RewardStatus
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
)
from app.models.user_reward import RewardType, UserReward
from app.modules.registrations.domain.registration import Registration
from app.modules.rewards.domain.value_objects import (
    ShippingAddress,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class RewardService(BaseService):
    """Service for physical reward operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def create_reward_order(
        self,
        registration_id: int,
        reward_name: str,
        shipping_address: ShippingAddress
    ) -> UserReward:
        """
        Create reward order.

        Business Rules:
        1. Registration must exist
        2. One reward per registration
        3. Shipping address must be valid

        Args:
            registration_id: Registration ID
            reward_name: Name of reward
            shipping_address: Shipping address

        Returns:
            Created UserReward

        Raises:
            NotFoundException: If registration not found
            AlreadyExistsException: If reward already exists
        """
        # Get registration
        registration = self.db.query(Registration).filter(
            Registration.id == registration_id
        ).first()

        if not registration:
            raise NotFoundException("Registration", str(registration_id))

        # Check if reward already exists
        existing = self.db.query(UserReward).filter(
            and_(
                UserReward.registration_id == registration_id,
                UserReward.reward_type == RewardType.MEDAL
            )
        ).first()

        if existing:
            raise AlreadyExistsException("Reward", "registration_id", str(registration_id))

        # Create reward record
        reward = UserReward(
            user_id=registration.user_id,
            registration_id=registration_id,
            event_id=registration.event_id,
            reward_id=f"medal-{registration_id}",
            reward_type=RewardType.MEDAL,
            reward_name=reward_name,
            status=RewardStatus.PENDING_DETAILS.value,
        )

        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)

        # TODO: Create Shiprocket order via external service
        # shiprocket_service.create_order(reward, shipping_address)

        return reward

    def update_shipment_status(
        self,
        reward_id: int,
        status: str,
        tracking_number: str | None = None,
        shiprocket_order_id: str | None = None
    ) -> UserReward:
        """Update shipment status. `status` should be a RewardStatus value string."""
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            raise NotFoundException("Reward", str(reward_id))

        reward.status = status

        if tracking_number:
            reward.tracking_number = tracking_number

        if shiprocket_order_id:
            reward.shiprocket_order_id = shiprocket_order_id

        self.db.commit()
        self.db.refresh(reward)

        return reward

    def get_user_rewards(
        self,
        user_id: int
    ) -> list[UserReward]:
        """Get all physical rewards for user"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.user_id == user_id,
                UserReward.reward_type == RewardType.MEDAL
            )
        ).order_by(UserReward.created_at.desc()).all()

    def get_pending_rewards(self) -> list[UserReward]:
        """Get all pending reward orders"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.reward_type == RewardType.MEDAL,
                UserReward.status == RewardStatus.PENDING_DETAILS.value
            )
        ).all()
