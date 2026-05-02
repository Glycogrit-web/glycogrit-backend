"""
High-level Shipping Service

This service orchestrates shipping operations across different providers.
Currently focused on Shiprocket integration, but designed to support multiple providers.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging

from app.modules.shipping.domain.entities import ShipmentEntity
from app.modules.shipping.domain.value_objects import ShippingAddress

logger = logging.getLogger(__name__)


class ShippingService:
    """
    High-level service for shipping operations.

    This service provides a unified interface for shipping operations,
    delegating to specific provider integrations (like Shiprocket).
    """

    def __init__(self, db: Session):
        """
        Initialize the ShippingService.

        Args:
            db: Database session
        """
        self.db = db

    def create_shipment(
        self,
        user_reward_id: str,
        event_id: int,
        user_id: int,
        shipping_address: ShippingAddress,
        product_details: Dict[str, Any]
    ) -> ShipmentEntity:
        """
        Create a new shipment order.

        Args:
            user_reward_id: User reward UUID
            event_id: Event ID
            user_id: User ID
            shipping_address: Shipping address as value object
            product_details: Product information (name, price, SKU, etc.)

        Returns:
            ShipmentEntity with shipment details

        Raises:
            ValidationException: If validation fails
            ShippingException: If shipment creation fails
        """
        # Import here to avoid circular dependency
        from app.modules.shipping.integrations.shiprocket.fulfillment_service import (
            RewardFulfillmentService
        )

        fulfillment_service = RewardFulfillmentService(self.db)

        # Delegate to Shiprocket fulfillment service
        # This service handles the actual order creation
        shipment = fulfillment_service.fulfill_reward(
            user_reward_id=user_reward_id,
            event_id=event_id,
            user_id=user_id,
            shipping_address=shipping_address.to_dict(),
            product_details=product_details
        )

        return ShipmentEntity(shipment)

    def get_shipment_by_id(self, shipment_id: int) -> Optional[ShipmentEntity]:
        """
        Get a shipment by ID.

        Args:
            shipment_id: Shipment ID

        Returns:
            ShipmentEntity or None if not found
        """
        from app.modules.shipping.domain.shipment import ShiprocketOrder

        shipment = self.db.query(ShiprocketOrder).filter(
            ShiprocketOrder.id == shipment_id
        ).first()

        if shipment:
            return ShipmentEntity(shipment)
        return None

    def get_shipment_by_user_reward(
        self,
        user_reward_id: str
    ) -> Optional[ShipmentEntity]:
        """
        Get a shipment by user reward ID.

        Args:
            user_reward_id: User reward UUID

        Returns:
            ShipmentEntity or None if not found
        """
        from app.modules.shipping.domain.shipment import ShiprocketOrder

        shipment = self.db.query(ShiprocketOrder).filter(
            ShiprocketOrder.user_reward_id == user_reward_id
        ).first()

        if shipment:
            return ShipmentEntity(shipment)
        return None

    def get_user_shipments(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ShipmentEntity]:
        """
        Get all shipments for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ShipmentEntity instances
        """
        from app.modules.shipping.domain.shipment import ShiprocketOrder

        shipments = self.db.query(ShiprocketOrder).filter(
            ShiprocketOrder.user_id == user_id
        ).order_by(ShiprocketOrder.created_at.desc()).offset(skip).limit(limit).all()

        return [ShipmentEntity(s) for s in shipments]

    def retry_failed_shipment(self, shipment_id: int) -> ShipmentEntity:
        """
        Retry a failed shipment order.

        Args:
            shipment_id: Shipment ID

        Returns:
            Updated ShipmentEntity

        Raises:
            ValidationException: If shipment cannot be retried
            ShippingException: If retry fails
        """
        from app.modules.shipping.integrations.shiprocket.retry_handler import (
            ShiprocketRetryHandler
        )

        shipment_entity = self.get_shipment_by_id(shipment_id)
        if not shipment_entity:
            raise ValueError(f"Shipment {shipment_id} not found")

        if not shipment_entity.can_retry:
            raise ValueError(
                f"Shipment {shipment_id} cannot be retried. "
                f"Status: {shipment_entity.status}, "
                f"Age: {shipment_entity.get_age_in_days()} days"
            )

        retry_handler = ShiprocketRetryHandler(self.db)
        updated_shipment = retry_handler.retry_order(shipment_id)

        return ShipmentEntity(updated_shipment)

    def cancel_shipment(self, shipment_id: int, reason: str = "Cancelled by user") -> ShipmentEntity:
        """
        Cancel a shipment order.

        Args:
            shipment_id: Shipment ID
            reason: Cancellation reason

        Returns:
            Updated ShipmentEntity

        Raises:
            ValidationException: If shipment cannot be cancelled
            ShippingException: If cancellation fails
        """
        shipment_entity = self.get_shipment_by_id(shipment_id)
        if not shipment_entity:
            raise ValueError(f"Shipment {shipment_id} not found")

        if not shipment_entity.can_cancel:
            raise ValueError(
                f"Shipment {shipment_id} cannot be cancelled. "
                f"Status: {shipment_entity.status}"
            )

        # Import here to avoid circular dependency
        from app.modules.shipping.integrations.shiprocket.client import (
            ShiprocketService
        )

        shiprocket_service = ShiprocketService(self.db)

        # Cancel the order in Shiprocket
        if shipment_entity.shiprocket_order_id:
            shiprocket_service.cancel_order(
                order_id=shipment_entity.shiprocket_order_id.value
            )

        # Update local status
        shipment_entity._shipment.status = "cancelled"
        shipment_entity._shipment.error_message = reason
        self.db.commit()

        return ShipmentEntity(shipment_entity._shipment)

    def track_shipment(self, shipment_id: int) -> Dict[str, Any]:
        """
        Get tracking information for a shipment.

        Args:
            shipment_id: Shipment ID

        Returns:
            Tracking information dictionary

        Raises:
            ValidationException: If shipment not found or no tracking available
        """
        shipment_entity = self.get_shipment_by_id(shipment_id)
        if not shipment_entity:
            raise ValueError(f"Shipment {shipment_id} not found")

        if not shipment_entity.has_tracking_number:
            raise ValueError(f"Shipment {shipment_id} does not have a tracking number yet")

        return {
            "tracking_number": shipment_entity.tracking_number.value,
            "courier_name": shipment_entity.tracking_number.courier_name,
            "tracking_url": shipment_entity._shipment.tracking_url,
            "status": shipment_entity.status,
            "pickup_scheduled": shipment_entity.is_pickup_scheduled,
            "pickup_date": (
                shipment_entity.pickup_schedule.scheduled_date.isoformat()
                if shipment_entity.pickup_schedule and shipment_entity.pickup_schedule.scheduled_date
                else None
            )
        }

    def get_stale_shipments(self, max_age_days: int = 30) -> List[ShipmentEntity]:
        """
        Get all stale shipments that need attention.

        Args:
            max_age_days: Maximum age in days for pending shipments

        Returns:
            List of stale ShipmentEntity instances
        """
        from app.modules.shipping.domain.shipment import ShiprocketOrder, ShiprocketOrderStatus
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        shipments = self.db.query(ShiprocketOrder).filter(
            ShiprocketOrder.status == ShiprocketOrderStatus.PENDING,
            ShiprocketOrder.created_at < cutoff_date
        ).all()

        return [ShipmentEntity(s) for s in shipments]
