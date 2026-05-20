"""
Reward Service

Business logic for physical reward fulfillment via Shiprocket.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modules.certificates.domain.certificate import UserReward, RewardType
from app.modules.rewards.domain.value_objects import (
    ShippingAddress,
    ShipmentStatus,
    ShiprocketOrderId,
    TrackingNumber,
)
from app.modules.registrations.domain.registration import Registration
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
)
import logging

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
            raise NotFoundException("Registration", "id", str(registration_id))

        # Check if reward already exists
        existing = self.db.query(UserReward).filter(
            and_(
                UserReward.registration_id == registration_id,
                UserReward.reward_type == RewardType.PHYSICAL_REWARD
            )
        ).first()

        if existing:
            raise AlreadyExistsException("Reward", "registration_id", str(registration_id))

        # Create reward record
        reward = UserReward(
            user_id=registration.user_id,
            registration_id=registration_id,
            event_id=registration.event_id,
            reward_type=RewardType.PHYSICAL_REWARD,
            reward_name=reward_name,
            delivery_status=ShipmentStatus.PENDING.value,
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
        status: ShipmentStatus,
        tracking_number: Optional[str] = None,
        shiprocket_order_id: Optional[str] = None
    ) -> UserReward:
        """Update shipment status"""
        reward = self.get_or_404(
            self.db.query(UserReward),
            reward_id,
            "Reward"
        )

        reward.delivery_status = status.value

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
    ) -> List[UserReward]:
        """Get all physical rewards for user"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.user_id == user_id,
                UserReward.reward_type == RewardType.PHYSICAL_REWARD
            )
        ).order_by(UserReward.created_at.desc()).all()

    def get_pending_rewards(self) -> List[UserReward]:
        """Get all pending reward orders"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.reward_type == RewardType.PHYSICAL_REWARD,
                UserReward.delivery_status == ShipmentStatus.PENDING.value
            )
        ).all()
