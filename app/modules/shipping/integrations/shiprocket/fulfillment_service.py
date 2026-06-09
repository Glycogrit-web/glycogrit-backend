"""
Reward Fulfillment Service
Business logic for reward fulfillment with Shiprocket integration
"""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.modules.shipping.domain.shipment import ShiprocketOrder, ShiprocketOrderStatus
from app.models.user_reward import RewardStatus, UserReward
from app.modules.shipping.integrations.shiprocket.client import ShiprocketService
from app.modules.shipping.services.courier_selection_service import CourierSelectionService

logger = logging.getLogger(__name__)


class RewardFulfillmentService:
    """
    Service for managing reward fulfillment process.
    Handles Shiprocket order creation, label generation, and tracking updates.
    """

    def __init__(self, db: Session):
        """
        Initialize reward fulfillment service.

        Args:
            db: Database session
        """
        self.db = db
        self.shiprocket = ShiprocketService(db)

    async def create_shiprocket_order(self, reward_id: str) -> dict[str, Any]:
        """
        Create Shiprocket order for a single reward.

        Args:
            reward_id: UserReward ID (UUID)

        Returns:
            Dict with order creation result
        """
        logger.info(f"📦 [FULFILLMENT] Starting order creation for reward: {reward_id}")

        # Get reward
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()

        if not reward:
            logger.error(f"❌ [FULFILLMENT] Reward not found: {reward_id}")
            return {"success": False, "error": "Reward not found"}

        logger.info(f"   Reward found: {reward.reward_name} (status: {reward.status.value})")

        # Validate reward status
        if not reward.requires_shipping:
            logger.error(f"❌ [FULFILLMENT] Reward doesn't require shipping")
            return {"success": False, "error": "Reward doesn't require shipping"}

        if reward.status != RewardStatus.PENDING_SHIPMENT:
            logger.error(f"❌ [FULFILLMENT] Invalid status: {reward.status.value}, expected pending_shipment")
            return {
                "success": False,
                "error": f"Reward status is {reward.status.value}, expected pending_shipment",
            }

        if not reward.shipping_details:
            logger.error(f"❌ [FULFILLMENT] No shipping details provided")
            return {"success": False, "error": "Shipping details not provided"}

        logger.info(f"   Shipping to: {reward.shipping_details.get('name')} - {reward.shipping_details.get('city')}")

        # Check if order already exists
        existing_order = (
            self.db.query(ShiprocketOrder)
            .filter(ShiprocketOrder.user_reward_id == reward_id)
            .first()
        )

        if existing_order:
            logger.error(f"❌ [FULFILLMENT] Order already exists: {existing_order.order_reference}")
            return {"success": False, "error": "Shiprocket order already exists"}

        # Generate order reference
        order_reference = (
            f"RNR-EVT-{reward.event_id}-USR-{reward.user_id}-RWD-{str(reward.id)[:8].upper()}"
        )

        logger.info(f"   Generated order reference: {order_reference}")

        # Create Shiprocket order
        logger.info(f"🚀 [FULFILLMENT] Calling Shiprocket API to create order...")
        result = await self.shiprocket.create_order(
            order_reference=order_reference,
            user_reward=reward,
            shipping_details=reward.shipping_details,
        )

        if result["success"]:
            logger.info(f"✅ [FULFILLMENT] Shiprocket order created successfully!")
            logger.info(f"   Order ID: {result['order_id']}")
            logger.info(f"   Shipment ID: {result['shipment_id']}")

            # Create ShiprocketOrder record
            shiprocket_order = ShiprocketOrder(
                user_reward_id=reward.id,
                event_id=reward.event_id,
                user_id=reward.user_id,
                order_reference=order_reference,
                shiprocket_order_id=str(result["order_id"]),
                shiprocket_shipment_id=str(result["shipment_id"]),
                status=ShiprocketOrderStatus.CREATED,
                shiprocket_request=result["payload"],
                shiprocket_response=result["response"],
                order_sent_at=func.now(),
            )
            self.db.add(shiprocket_order)

            # Update reward status
            reward.status = RewardStatus.LABEL_GENERATED
            reward.shiprocket_order_id = str(result["order_id"])
            reward.shiprocket_shipment_id = str(result["shipment_id"])

            self.db.commit()

            logger.info(f"💾 [FULFILLMENT] Database updated - ShiprocketOrder record created")

            # Auto-assign AWB and generate label if configured
            config = self.shiprocket.config
            if config.auto_generate_label:
                logger.info(f"🏷️  [FULFILLMENT] Auto-generate label enabled, proceeding to AWB assignment...")
                await self.assign_awb_and_generate_label(reward_id)

            return {
                "success": True,
                "reward_id": str(reward.id),
                "shiprocket_order_id": result["order_id"],
                "shiprocket_shipment_id": result["shipment_id"],
            }
        else:
            # Log error
            error_msg = result["error"]
            reward.fulfillment_error = error_msg
            self.db.commit()

            logger.error(f"❌ [FULFILLMENT] Shiprocket order creation FAILED for reward {reward_id}")
            logger.error(f"   Error: {error_msg[:200]}")

            # Check if it's a blocking error
            if result.get("is_blocked"):
                logger.error(f"🚫 [FULFILLMENT] IP BLOCKED - This is a Cloudflare/WAF issue")
                logger.error(f"   Railway's IP address is being blocked by Shiprocket's firewall")

            return {"success": False, "error": error_msg, "reward_id": str(reward.id)}

    async def assign_awb_and_generate_label(
        self,
        reward_id: str,
        courier_id: Optional[int] = None,
        selection_strategy: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Assign AWB and generate shipping label for reward with auto-courier selection.

        Args:
            reward_id: UserReward ID
            courier_id: Optional courier ID for manual selection (overrides auto-selection)
            selection_strategy: Optional strategy override ('cheapest', 'fastest', 'balanced')

        Returns:
            Dict with result including courier selection details
        """
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            return {"success": False, "error": "Reward not found"}

        shiprocket_order = reward.shiprocket_order
        if not shiprocket_order:
            return {"success": False, "error": "Shiprocket order not found"}

        config = self.shiprocket.config

        # Step 1: Get available couriers if auto-selection is enabled and no courier specified
        if not courier_id and config.auto_select_courier:
            try:
                # Check pincode serviceability to get available couriers
                serviceability = await self.shiprocket.check_pincode_serviceability(
                    delivery_pincode=reward.shipping_details.get('pincode'),
                    weight=reward.item_weight or config.default_weight,
                    length=reward.item_length or config.default_length,
                    breadth=reward.item_breadth or config.default_breadth,
                    height=reward.item_height or config.default_height,
                )

                if serviceability.get('success') and serviceability.get('is_serviceable'):
                    available_couriers = serviceability.get('available_couriers', [])

                    if available_couriers:
                        # Auto-select courier using selection service
                        strategy = selection_strategy or config.courier_selection_strategy
                        selection_service = CourierSelectionService()

                        selected_courier = selection_service.select_by_strategy(
                            couriers=available_couriers,
                            strategy=strategy,
                            blacklisted_courier_ids=config.blacklisted_couriers or []
                        )

                        if selected_courier:
                            courier_id = selected_courier.get('courier_company_id')

                            # Store selection metadata
                            shiprocket_order.selected_courier_rate = selected_courier.get('rate')
                            shiprocket_order.alternative_couriers = available_couriers
                            shiprocket_order.cost_savings = selection_service.calculate_savings(
                                selected_courier, available_couriers
                            )
                            shiprocket_order.selection_strategy_used = strategy

                            logger.info(
                                f"✅ Auto-selected courier {selected_courier.get('courier_name')} "
                                f"(ID: {courier_id}) for reward {reward_id}. "
                                f"Rate: ₹{selected_courier.get('rate')}, "
                                f"Savings: ₹{shiprocket_order.cost_savings}"
                            )
                        else:
                            logger.warning(f"⚠️ No suitable courier found after selection for reward {reward_id}")
                    else:
                        logger.warning(f"⚠️ No couriers available for reward {reward_id}")
                else:
                    logger.warning(
                        f"⚠️ Pincode not serviceable or check failed for reward {reward_id}: "
                        f"{serviceability.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                logger.error(f"❌ Error in courier selection for reward {reward_id}: {str(e)}")
                # Continue with default courier selection by Shiprocket

        # Step 2: Assign AWB
        awb_result = await self.shiprocket.assign_awb(
            shipment_id=int(shiprocket_order.shiprocket_shipment_id),
            courier_id=courier_id
        )

        if awb_result["success"]:
            # Update records
            shiprocket_order.shiprocket_awb = awb_result["awb_code"]
            shiprocket_order.courier_id = awb_result["courier_company_id"]
            shiprocket_order.courier_name = awb_result["courier_name"]
            shiprocket_order.status = ShiprocketOrderStatus.LABEL_GENERATED
            shiprocket_order.label_generated_at = func.now()

            reward.tracking_number = awb_result["awb_code"]
            reward.shiprocket_awb = awb_result["awb_code"]
            reward.courier_partner = awb_result["courier_name"]

            # Generate label
            label_result = await self.shiprocket.generate_label(
                shipment_id=int(shiprocket_order.shiprocket_shipment_id)
            )

            if label_result["success"]:
                shiprocket_order.label_url = label_result["label_url"]
                reward.status = RewardStatus.LABEL_GENERATED

            # Generate manifest
            manifest_result = await self.shiprocket.generate_manifest(
                shipment_id=int(shiprocket_order.shiprocket_shipment_id)
            )

            if manifest_result["success"]:
                shiprocket_order.manifest_url = manifest_result["manifest_url"]

            self.db.commit()

            logger.info(f"✅ AWB assigned and label generated for reward {reward_id}")

            # Schedule pickup if auto-enabled
            if config.auto_schedule_pickup:
                await self.schedule_pickup(reward_id)

            return {
                "success": True,
                "awb": shiprocket_order.shiprocket_awb,
                "courier_name": shiprocket_order.courier_name,
                "courier_id": shiprocket_order.courier_id,
                "selected_courier_rate": (
                    float(shiprocket_order.selected_courier_rate)
                    if shiprocket_order.selected_courier_rate else None
                ),
                "cost_savings": (
                    float(shiprocket_order.cost_savings)
                    if shiprocket_order.cost_savings else None
                ),
                "selection_strategy_used": shiprocket_order.selection_strategy_used,
            }
        else:
            logger.error(
                f"❌ Failed to assign AWB for reward {reward_id}: {awb_result.get('error')}"
            )
            return awb_result

    async def schedule_pickup(self, reward_id: str) -> dict[str, Any]:
        """
        Schedule pickup for reward shipment.

        Args:
            reward_id: UserReward ID

        Returns:
            Dict with result
        """
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            return {"success": False, "error": "Reward not found"}

        shiprocket_order = reward.shiprocket_order
        if not shiprocket_order:
            return {"success": False, "error": "Shiprocket order not found"}

        pickup_result = await self.shiprocket.schedule_pickup(
            shipment_id=int(shiprocket_order.shiprocket_shipment_id)
        )

        if pickup_result["success"]:
            shiprocket_order.pickup_scheduled_date = pickup_result["pickup_scheduled_date"]
            shiprocket_order.pickup_token_number = pickup_result["pickup_token_number"]
            shiprocket_order.status = ShiprocketOrderStatus.PICKUP_SCHEDULED
            shiprocket_order.pickup_scheduled_at = func.now()

            reward.status = RewardStatus.PICKUP_SCHEDULED
            reward.pickup_scheduled_date = pickup_result["pickup_scheduled_date"]

            self.db.commit()

            logger.info(f"✅ Pickup scheduled for reward {reward_id}")
            return {"success": True}
        else:
            logger.error(
                f"❌ Failed to schedule pickup for reward {reward_id}: {pickup_result.get('error')}"
            )
            return pickup_result

    async def bulk_create_orders(self, reward_ids: list[str]) -> dict[str, Any]:
        """
        Bulk create Shiprocket orders for multiple rewards.

        Args:
            reward_ids: List of UserReward IDs

        Returns:
            Dict with bulk operation result:
            {
                "success": True,
                "success_count": int,
                "failed_count": int,
                "results": list,
                "failed_orders": list
            }
        """
        results = []
        success_count = 0
        failed_count = 0

        for reward_id in reward_ids:
            try:
                result = await self.create_shiprocket_order(reward_id)
                results.append(result)

                if result["success"]:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"❌ Exception creating order for reward {reward_id}: {str(e)}")
                results.append({"success": False, "reward_id": reward_id, "error": str(e)})
                failed_count += 1

        logger.info(f"✅ Bulk order creation: {success_count} succeeded, {failed_count} failed")

        return {
            "success": True,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "failed_orders": [r for r in results if not r["success"]],
        }

    async def refresh_tracking(self, reward_id: str) -> dict[str, Any]:
        """
        Refresh tracking status from Shiprocket.

        Args:
            reward_id: UserReward ID

        Returns:
            Dict with updated tracking info
        """
        reward = self.db.query(UserReward).filter(UserReward.id == reward_id).first()
        if not reward:
            return {"success": False, "error": "Reward not found"}

        shiprocket_order = reward.shiprocket_order
        if not shiprocket_order or not shiprocket_order.shiprocket_shipment_id:
            return {"success": False, "error": "No shipment ID found"}

        tracking_result = await self.shiprocket.track_shipment(
            shipment_id=int(shiprocket_order.shiprocket_shipment_id)
        )

        if tracking_result["success"]:
            # Map Shiprocket status to our status
            status_mapping = {
                "Delivered": RewardStatus.DELIVERED,
                "Out for Delivery": RewardStatus.OUT_FOR_DELIVERY,
                "In Transit": RewardStatus.IN_TRANSIT,
                "Shipped": RewardStatus.SHIPPED,
                "Pickup Scheduled": RewardStatus.PICKUP_SCHEDULED,
            }

            new_status = status_mapping.get(tracking_result["status"], RewardStatus.IN_TRANSIT)

            # Update tracking info
            reward.status = new_status
            reward.tracking_url = tracking_result["tracking_url"]
            reward.estimated_delivery_date = tracking_result.get("etd")
            reward.last_tracking_update = func.now()

            # Get latest activity
            tracking_history = tracking_result.get("tracking_history", [])
            if tracking_history:
                latest_activity = tracking_history[0]
                reward.current_location = latest_activity.get("location")

                # Check if delivered
                if latest_activity.get("sr_status") == 7:
                    reward.actual_delivery_date = datetime.strptime(
                        latest_activity.get("date"), "%Y-%m-%d %H:%M:%S"
                    ).date()
                    reward.delivered_at = func.now()

                # Update status history
                if not reward.status_history:
                    reward.status_history = []

                reward.status_history.append(
                    {
                        "status": new_status.value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "location": reward.current_location,
                        "activity": latest_activity.get("activity"),
                    }
                )

            self.db.commit()

            logger.info(f"✅ Tracking updated for reward {reward_id}: {new_status.value}")

            return {"success": True, "reward": reward.to_dict()}
        else:
            logger.error(
                f"❌ Failed to refresh tracking for reward {reward_id}: {tracking_result.get('error')}"
            )
            return tracking_result

    def get_pending_shipment_rewards(self, event_id: int | None = None) -> list[UserReward]:
        """
        Get all rewards pending shipment.

        Args:
            event_id: Optional event ID to filter by

        Returns:
            List of UserReward instances
        """
        query = self.db.query(UserReward).filter(
            UserReward.status == RewardStatus.PENDING_SHIPMENT,
            UserReward.requires_shipping,
            UserReward.shipping_details.isnot(None),
        )

        if event_id:
            query = query.filter(UserReward.event_id == event_id)

        return query.all()

    def get_shipped_rewards(self, event_id: int | None = None) -> list[UserReward]:
        """
        Get all shipped rewards.

        Args:
            event_id: Optional event ID to filter by

        Returns:
            List of UserReward instances
        """
        query = self.db.query(UserReward).filter(
            UserReward.status.in_(
                [RewardStatus.SHIPPED, RewardStatus.IN_TRANSIT, RewardStatus.OUT_FOR_DELIVERY]
            )
        )

        if event_id:
            query = query.filter(UserReward.event_id == event_id)

        return query.all()
