"""
Reward Service

Business logic for physical reward fulfillment via Shiprocket.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.core.enums import RewardStatus
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
)
from app.models.user import User
from app.models.user_reward import RewardType, UserReward
from app.modules.events.domain.event import Event
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
        self, registration_id: int, reward_name: str, shipping_address: ShippingAddress
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
        registration = (
            self.db.query(Registration).filter(Registration.id == registration_id).first()
        )

        if not registration:
            raise NotFoundException("Registration", str(registration_id))

        # Check if reward already exists
        existing = (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.registration_id == registration_id,
                    UserReward.reward_type == RewardType.MEDAL,
                )
            )
            .first()
        )

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
        shiprocket_order_id: str | None = None,
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

    def get_user_rewards(self, user_id: int) -> list[UserReward]:
        """Get all physical rewards for user"""
        return (
            self.db.query(UserReward)
            .filter(and_(UserReward.user_id == user_id, UserReward.reward_type == RewardType.MEDAL))
            .order_by(UserReward.created_at.desc())
            .all()
        )

    def get_pending_rewards(self) -> list[UserReward]:
        """Get all pending reward orders"""
        return (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.reward_type == RewardType.MEDAL,
                    UserReward.status == RewardStatus.PENDING_DETAILS.value,
                )
            )
            .all()
        )

    def admin_unlock_reward(self, event_id: int, user_id: int, registration_id: int) -> UserReward:
        """
        Admin unlocks a reward for a user (creates UserReward record).

        Business Rules:
        1. Registration must exist and match event_id/user_id
        2. One reward per registration
        3. If shipping details exist in registration:
           - Reward status: 'pending_shipment' (ready to ship)
           - shipping_details populated from registration
        4. If shipping details missing:
           - Reward status: 'pending_details' (user needs to provide address)

        Args:
            event_id: Event ID
            user_id: User ID
            registration_id: Registration ID

        Returns:
            Created UserReward

        Raises:
            NotFoundException: If registration not found
            AlreadyExistsException: If reward already exists
        """
        # Get registration and validate it belongs to user/event
        registration = (
            self.db.query(Registration)
            .filter(
                and_(
                    Registration.id == registration_id,
                    Registration.user_id == user_id,
                    Registration.event_id == event_id,
                )
            )
            .first()
        )

        if not registration:
            raise NotFoundException("Registration", f"id={registration_id}, user_id={user_id}, event_id={event_id}")

        # Check if reward already exists
        existing = (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.registration_id == registration_id,
                    UserReward.reward_type == RewardType.MEDAL,
                )
            )
            .first()
        )

        if existing:
            raise AlreadyExistsException("Reward", "registration_id", str(registration_id))

        # Check if registration has complete shipping details
        has_shipping = bool(
            registration.shipping_address_line1
            and registration.shipping_city
            and registration.shipping_state
            and registration.shipping_postal_code
            and registration.shipping_phone
        )

        # If shipping details exist, populate them immediately and set status to pending_shipment
        shipping_details = None
        reward_status = RewardStatus.PENDING_DETAILS.value  # Default: waiting for user

        if has_shipping:
            # Populate shipping_details JSONB immediately (admin verified)
            shipping_details = {
                "name": registration.participant_name or "Unknown",
                "phone": registration.shipping_phone,
                "address_line1": registration.shipping_address_line1,
                "address_line2": registration.shipping_address_line2 or "",
                "city": registration.shipping_city,
                "state": registration.shipping_state,
                "pincode": registration.shipping_postal_code,
                "country": registration.shipping_country or "India",
                "email": registration.shipping_email or registration.user.email if registration.user else "",
            }
            reward_status = RewardStatus.PENDING_SHIPMENT.value  # Ready to ship

        # Create reward record in unlocked state
        reward = UserReward(
            user_id=user_id,
            registration_id=registration_id,
            event_id=event_id,
            reward_id=f"medal-{registration_id}",
            reward_type=RewardType.MEDAL,
            reward_name=f"{registration.tier.name} Medal" if registration.tier else "Event Medal",
            status=reward_status,
            shipping_details=shipping_details,
        )

        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)

        logger.info(f"Admin unlocked reward for user_id={user_id}, event_id={event_id}, registration_id={registration_id}")

        return reward

    def get_all_rewards_with_details(
        self,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """
        Get all rewards with full details for admin dashboard.

        Args:
            status_filter: Filter by reward status
            search: Search by user name, email, or tracking number

        Returns:
            List of reward dicts with all details
        """
        # Build query with joins
        query = (
            self.db.query(UserReward)
            .join(User, UserReward.user_id == User.id)
            .join(Registration, UserReward.registration_id == Registration.id)
            .join(Event, UserReward.event_id == Event.id)
            .options(
                joinedload(UserReward.user),
                joinedload(UserReward.registration).joinedload(Registration.tier),
                joinedload(UserReward.event),
            )
        )

        # Apply status filter
        if status_filter:
            query = query.filter(UserReward.status == status_filter)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term),
                    UserReward.tracking_number.ilike(search_term),
                )
            )

        rewards = query.order_by(UserReward.created_at.desc()).all()

        # Transform to dict with all details
        results = []
        for reward in rewards:
            results.append({
                # Reward fields
                "id": reward.id,
                "reward_id": reward.reward_id,
                "reward_name": reward.reward_name,
                "reward_type": reward.reward_type.value if hasattr(reward.reward_type, 'value') else reward.reward_type,
                "status": reward.status,
                # User details
                "user_id": reward.user.id,
                "user_name": reward.user.name,
                "user_email": reward.user.email,
                "user_phone": reward.user.phone if hasattr(reward.user, 'phone') else None,
                # Event details
                "event_id": reward.event.id,
                "event_name": reward.event.name,
                # Registration details
                "registration_id": reward.registration.id,
                "registration_number": reward.registration.registration_number,
                "tier_name": reward.registration.tier.name if reward.registration.tier else None,
                # Shipping details
                "shipping_address": reward.shipping_details if hasattr(reward, 'shipping_details') else None,
                "tracking_number": reward.tracking_number,
                "courier_partner": reward.courier_partner,
                "shiprocket_order_id": reward.shiprocket_order_id,
                "shiprocket_shipment_id": reward.shiprocket_shipment_id,
                # Timestamps
                "created_at": reward.created_at,
                "shipped_at": reward.shipped_at,
                "delivered_at": reward.delivered_at,
                "estimated_delivery": reward.estimated_delivery_date if hasattr(reward, 'estimated_delivery_date') else None,
                # Progress (from registration)
                "total_distance_km": reward.registration.total_distance_km if hasattr(reward.registration, 'total_distance_km') else None,
                "goal_distance_km": reward.registration.tier.goal_distance_km if reward.registration.tier and hasattr(reward.registration.tier, 'goal_distance_km') else None,
                "progress_percentage": (
                    int((reward.registration.total_distance_km / reward.registration.tier.goal_distance_km) * 100)
                    if reward.registration.tier
                    and hasattr(reward.registration, 'total_distance_km')
                    and hasattr(reward.registration.tier, 'goal_distance_km')
                    and reward.registration.tier.goal_distance_km > 0
                    else 0
                ),
                "proof_image_url": reward.registration.proof_image_url if hasattr(reward.registration, 'proof_image_url') else None,
            })

        return results

    async def get_shipping_preview(self, reward_id: int) -> dict:
        """
        Get shipping preview with all details before creating order.

        Shows admin:
        - Reward details (name, type)
        - Package dimensions and weight
        - Full shipping address and phone
        - Pickup location details
        - Available couriers with estimated costs
        - Estimated delivery time
        - Serviceability check

        Args:
            reward_id: Reward ID

        Returns:
            Complete shipping preview data

        Raises:
            NotFoundException: If reward not found
            ValueError: If reward not ready for preview
        """
        # Get reward with shipping details
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            raise NotFoundException("Reward", str(reward_id))

        # Validate shipping address exists
        if not reward.shipping_details:
            raise ValueError("Reward does not have shipping address. User must provide shipping details first.")

        # Get Shiprocket config for default dimensions
        from app.modules.shipping.domain.shiprocket_config import ShiprocketConfig
        config = self.db.query(ShiprocketConfig).filter(ShiprocketConfig.is_active).first()
        if not config:
            raise ValueError("Shiprocket configuration not found.")

        # Parse shipping address
        shipping_addr = reward.shipping_details
        delivery_pincode = shipping_addr.get("pincode", "")

        # Check serviceability and get courier rates
        from app.modules.shipping.integrations.shiprocket.client import ShiprocketService
        shiprocket = ShiprocketService(self.db)

        serviceability = await shiprocket.check_pincode_serviceability(
            delivery_pincode=delivery_pincode,
            weight=float(reward.item_weight or config.default_weight)
        )

        # Format available couriers with rates
        available_couriers = []
        if serviceability.get("success") and serviceability.get("available_couriers"):
            for courier in serviceability["available_couriers"][:5]:  # Top 5 couriers
                available_couriers.append({
                    "name": courier.get("courier_name", "Unknown"),
                    "rate": courier.get("rate", 0),
                    "etd": courier.get("etd", "N/A"),
                    "cod_available": courier.get("cod", 0) == 1,
                })

        # Format addresses
        shipping_address_line = shipping_addr.get("address_line1", "")
        if shipping_addr.get("address_line2"):
            shipping_address_line += f", {shipping_addr.get('address_line2')}"

        pickup_address_line = f"Gahlot House, Ground Floor, Gyan Sarover Colony, Tiraya, Rajasthan 324008"

        return {
            "reward_name": reward.reward_name,
            "reward_type": reward.reward_type.value,
            # Package details
            "length_cm": float(reward.item_length or config.default_length),
            "breadth_cm": float(reward.item_breadth or config.default_breadth),
            "height_cm": float(reward.item_height or config.default_height),
            "weight_kg": float(reward.item_weight or config.default_weight),
            # Shipping address
            "shipping_name": shipping_addr.get("name", ""),
            "shipping_address": shipping_address_line,
            "shipping_city": shipping_addr.get("city", ""),
            "shipping_state": shipping_addr.get("state", ""),
            "shipping_pincode": delivery_pincode,
            "shipping_phone": shipping_addr.get("phone", ""),
            # Pickup location
            "pickup_location": config.default_pickup_location,
            "pickup_address": pickup_address_line,
            # Serviceability
            "available_couriers": available_couriers if available_couriers else None,
            "estimated_delivery_days": available_couriers[0]["etd"] if available_couriers else "N/A",
            "is_serviceable": serviceability.get("is_serviceable", False),
        }

    async def ship_reward_with_shiprocket(self, reward_id: int) -> dict:
        """
        Ship reward automatically using Shiprocket.

        Args:
            reward_id: Reward ID

        Returns:
            Shiprocket shipment details

        Raises:
            NotFoundException: If reward not found
            ValueError: If reward not ready for shipping
        """
        # Get reward
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            raise NotFoundException("Reward", str(reward_id))

        # Validate status
        if reward.status != RewardStatus.PENDING_SHIPMENT.value:
            raise ValueError(f"Reward must be in 'pending_shipment' status to ship. Current status: {reward.status}")

        # Validate shipping address exists
        if not reward.shipping_details:
            raise ValueError("Reward does not have shipping address. User must provide shipping details first.")

        # Initialize fulfillment service
        from app.modules.shipping.integrations.shiprocket.fulfillment_service import ShiprocketFulfillmentService
        fulfillment = ShiprocketFulfillmentService(self.db)

        # Create Shiprocket order, assign AWB, and schedule pickup
        logger.info(f"Creating Shiprocket order for reward_id={reward_id}")
        order_result = await fulfillment.create_shiprocket_order(reward.reward_id)

        logger.info(f"Assigning AWB for reward_id={reward_id}")
        awb_result = await fulfillment.assign_awb_and_generate_label(reward.reward_id)

        logger.info(f"Scheduling pickup for reward_id={reward_id}")
        pickup_result = await fulfillment.schedule_pickup(reward.reward_id)

        # Refresh reward to get updated data
        self.db.refresh(reward)

        return {
            "success": True,
            "tracking_number": reward.tracking_number,
            "courier_partner": reward.courier_partner,
            "awb": reward.tracking_number,  # Same as tracking_number
            "label_url": awb_result.get("label_url", ""),
            "shiprocket_order_id": int(reward.shiprocket_order_id) if reward.shiprocket_order_id else 0,
            "shiprocket_shipment_id": int(reward.shiprocket_shipment_id) if reward.shiprocket_shipment_id else 0,
            "pickup_scheduled_date": pickup_result.get("pickup_scheduled_date"),
        }

    def ship_reward_manually(
        self,
        reward_id: int,
        tracking_number: str,
        courier_partner: str,
        shipped_at: Optional[datetime] = None,
    ) -> UserReward:
        """
        Mark reward as shipped with manual tracking details.

        Args:
            reward_id: Reward ID
            tracking_number: Tracking/AWB number
            courier_partner: Courier company name
            shipped_at: Optional ship timestamp (defaults to now)

        Returns:
            Updated UserReward

        Raises:
            NotFoundException: If reward not found
        """
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            raise NotFoundException("Reward", str(reward_id))

        # Update reward with shipping details
        reward.status = RewardStatus.SHIPPED.value
        reward.tracking_number = tracking_number
        reward.courier_partner = courier_partner
        reward.shipped_at = shipped_at or datetime.utcnow()

        # Log in status history if it exists
        if hasattr(reward, 'status_history') and reward.status_history:
            history = reward.status_history if isinstance(reward.status_history, list) else []
            history.append({
                "status": "shipped",
                "timestamp": (shipped_at or datetime.utcnow()).isoformat(),
                "source": "manual",
                "note": f"Shipped manually by admin via {courier_partner}",
            })
            reward.status_history = history

        self.db.commit()
        self.db.refresh(reward)

        logger.info(f"Reward {reward_id} marked as shipped manually. Tracking: {tracking_number}, Courier: {courier_partner}")

        return reward

    def mark_reward_delivered(self, reward_id: int) -> UserReward:
        """
        Mark reward as delivered.

        Args:
            reward_id: Reward ID

        Returns:
            Updated UserReward

        Raises:
            NotFoundException: If reward not found
        """
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            raise NotFoundException("Reward", str(reward_id))

        # Update status to delivered
        reward.status = RewardStatus.DELIVERED.value
        reward.delivered_at = datetime.utcnow()

        # Log in status history if it exists
        if hasattr(reward, 'status_history') and reward.status_history:
            history = reward.status_history if isinstance(reward.status_history, list) else []
            history.append({
                "status": "delivered",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "manual",
                "note": "Marked as delivered manually by admin",
            })
            reward.status_history = history

        self.db.commit()
        self.db.refresh(reward)

        logger.info(f"Reward {reward_id} marked as delivered")

        return reward
