"""
Shiprocket Webhook Service
Handles real-time status updates from Shiprocket webhooks
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.user_reward import RewardStatus, UserReward

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for processing Shiprocket webhooks.

    Official Shiprocket Webhook Specifications:
    - Method: POST
    - Content-Type: application/json
    - Security Header: anx-api-key
    - Response: Must return 200 OK
    - No keywords: shiprocket, kartrocket, sr, kr in webhook URL
    """

    # Complete Shiprocket status code mapping (90+ codes from official docs)
    STATUS_MAPPING = {
        # Basic Status Codes
        1: RewardStatus.PENDING_SHIPMENT,  # New
        2: RewardStatus.PICKUP_SCHEDULED,  # Invoiced
        3: RewardStatus.PICKUP_SCHEDULED,  # Ready To Ship
        4: RewardStatus.PICKUP_SCHEDULED,  # Pickup Scheduled
        # Valid statuses: PENDING_DETAILS, PENDING_SHIPMENT, SHIPPED, DELIVERED, CANCELLED
        5: RewardStatus.CANCELLED,  # Canceled
        6: RewardStatus.SHIPPED,  # Shipped
        7: RewardStatus.DELIVERED,  # Delivered
        8: RewardStatus.PENDING_SHIPMENT,  # ePayment Failed
        9: RewardStatus.CANCELLED,  # Returned (RTO_DELIVERED → CANCELLED)
        10: RewardStatus.PENDING_SHIPMENT,  # Unmapped
        11: RewardStatus.PENDING_SHIPMENT,  # Unfulfillable
        12: RewardStatus.SHIPPED,  # Pickup Queue (PICKUP_SCHEDULED → SHIPPED)
        13: RewardStatus.SHIPPED,  # Pickup Rescheduled (PICKUP_SCHEDULED → SHIPPED)
        14: RewardStatus.SHIPPED,  # Pickup Error (PICKUP_SCHEDULED → SHIPPED)
        15: RewardStatus.CANCELLED,  # RTO Initiated (RTO_INITIATED → CANCELLED)
        16: RewardStatus.CANCELLED,  # RTO Delivered (RTO_DELIVERED → CANCELLED)
        17: RewardStatus.CANCELLED,  # RTO Acknowledged (RTO_DELIVERED → CANCELLED)
        18: RewardStatus.PENDING_SHIPMENT,  # Cancellation Requested
        19: RewardStatus.SHIPPED,  # Out for Delivery (OUT_FOR_DELIVERY → SHIPPED)
        20: RewardStatus.SHIPPED,  # In Transit (IN_TRANSIT → SHIPPED)
        21: RewardStatus.PENDING_SHIPMENT,  # Return Pending
        22: RewardStatus.CANCELLED,  # Return Initiated (RTO_INITIATED → CANCELLED)
        23: RewardStatus.CANCELLED,  # Return Pickup Queued (RTO_INITIATED → CANCELLED)
        24: RewardStatus.CANCELLED,  # Return Pickup Error (RTO_INITIATED → CANCELLED)
        25: RewardStatus.CANCELLED,  # Return In Transit (RTO_INITIATED → CANCELLED)
        26: RewardStatus.CANCELLED,  # Return Delivered (RTO_DELIVERED → CANCELLED)
        27: RewardStatus.CANCELLED,  # Return Cancelled
        28: RewardStatus.CANCELLED,  # Return Pickup Generated (RTO_INITIATED → CANCELLED)
        29: RewardStatus.PENDING_SHIPMENT,  # Return Cancellation Requested
        30: RewardStatus.CANCELLED,  # Return Pickup Cancelled
        31: RewardStatus.CANCELLED,  # Return Pickup Rescheduled (RTO_INITIATED → CANCELLED)
        32: RewardStatus.CANCELLED,  # Return Picked Up (RTO_INITIATED → CANCELLED)
        33: RewardStatus.SHIPPED,  # Lost
        34: RewardStatus.SHIPPED,  # Out For Pickup (PICKUP_SCHEDULED → SHIPPED)
        35: RewardStatus.SHIPPED,  # Pickup Exception (PICKUP_SCHEDULED → SHIPPED)
        36: RewardStatus.SHIPPED,  # Undelivered (OUT_FOR_DELIVERY → SHIPPED)
        37: RewardStatus.SHIPPED,  # Delivery Delayed (IN_TRANSIT → SHIPPED)
        38: RewardStatus.DELIVERED,  # Partial Delivered
        39: RewardStatus.DELIVERED,  # Destroyed
        40: RewardStatus.DELIVERED,  # Damaged
        41: RewardStatus.DELIVERED,  # Fulfilled
        42: RewardStatus.DELIVERED,  # Archived
        43: RewardStatus.SHIPPED,  # Reached Destination Hub (IN_TRANSIT → SHIPPED)
        44: RewardStatus.SHIPPED,  # Misrouted (IN_TRANSIT → SHIPPED)
        45: RewardStatus.CANCELLED,  # RTO_OFD (RTO_INITIATED → CANCELLED)
        46: RewardStatus.CANCELLED,  # RTO_NDR (RTO_INITIATED → CANCELLED)
        47: RewardStatus.CANCELLED,  # Return Out For Pickup (RTO_INITIATED → CANCELLED)
        48: RewardStatus.CANCELLED,  # Return Out For Delivery (RTO_INITIATED → CANCELLED)
        49: RewardStatus.CANCELLED,  # Return Pickup Exception (RTO_INITIATED → CANCELLED)
        50: RewardStatus.CANCELLED,  # Return Undelivered (RTO_INITIATED → CANCELLED)
        51: RewardStatus.SHIPPED,  # Picked Up
        52: RewardStatus.DELIVERED,  # Self Fulfilled
        53: RewardStatus.DELIVERED,  # Disposed Off
        54: RewardStatus.CANCELLED,  # Canceled before Dispatched
        55: RewardStatus.CANCELLED,  # RTO In-Transit (RTO_INITIATED → CANCELLED)
        57: RewardStatus.PENDING_SHIPMENT,  # QC Failed
        58: RewardStatus.SHIPPED,  # Reached Warehouse (IN_TRANSIT → SHIPPED)
        59: RewardStatus.SHIPPED,  # Custom Cleared (IN_TRANSIT → SHIPPED)
        60: RewardStatus.SHIPPED,  # In Flight (IN_TRANSIT → SHIPPED)
        61: RewardStatus.SHIPPED,  # Handover to Courier
        62: RewardStatus.SHIPPED,  # Booked (PICKUP_SCHEDULED → SHIPPED)
        64: RewardStatus.SHIPPED,  # In Transit Overseas (IN_TRANSIT → SHIPPED)
        65: RewardStatus.SHIPPED,  # Connection Aligned (IN_TRANSIT → SHIPPED)
        66: RewardStatus.SHIPPED,  # Reached Overseas Warehouse (IN_TRANSIT → SHIPPED)
        67: RewardStatus.SHIPPED,  # Custom Cleared Overseas (IN_TRANSIT → SHIPPED)
        68: RewardStatus.CANCELLED,  # RETURN ACKNOWLEGED (RTO_DELIVERED → CANCELLED)
        69: RewardStatus.PENDING_SHIPMENT,  # Box Packing (LABEL_GENERATED → PENDING_SHIPMENT)
        70: RewardStatus.SHIPPED,  # Pickup Booked (PICKUP_SCHEDULED → SHIPPED)
        71: RewardStatus.SHIPPED,  # DARKSTORE SCHEDULED (PICKUP_SCHEDULED → SHIPPED)
        72: RewardStatus.PENDING_SHIPMENT,  # Allocation in Progress
        73: RewardStatus.PENDING_SHIPMENT,  # FC Allocated
        74: RewardStatus.PENDING_SHIPMENT,  # Picklist Generated
        75: RewardStatus.PENDING_SHIPMENT,  # Ready to Pack
        76: RewardStatus.PENDING_SHIPMENT,  # Packed (LABEL_GENERATED → PENDING_SHIPMENT)
        80: RewardStatus.PENDING_SHIPMENT,  # FC MANIFEST GENERATED (LABEL_GENERATED → PENDING_SHIPMENT)
        81: RewardStatus.SHIPPED,  # PROCESSED AT WAREHOUSE (IN_TRANSIT → SHIPPED)
        82: RewardStatus.PENDING_SHIPMENT,  # PACKED EXCEPTION (LABEL_GENERATED → PENDING_SHIPMENT)
        83: RewardStatus.SHIPPED,  # HANDOVER EXCEPTION
        87: RewardStatus.CANCELLED,  # RTO_LOCK (RTO_INITIATED → CANCELLED)
        88: RewardStatus.SHIPPED,  # UNTRACEABLE (IN_TRANSIT → SHIPPED)
        89: RewardStatus.SHIPPED,  # ISSUE_RELATED_TO_THE_RECIPIENT (OUT_FOR_DELIVERY → SHIPPED)
        90: RewardStatus.CANCELLED,  # REACHED_BACK_AT_SELLER_CITY (RTO_INITIATED → CANCELLED)
    }

    # User-friendly status labels
    STATUS_LABELS = {
        1: "New Order",
        2: "Invoiced",
        3: "Ready To Ship",
        4: "Pickup Scheduled",
        5: "Cancelled",
        6: "Shipped",
        7: "Delivered",
        19: "Out for Delivery",
        20: "In Transit",
        43: "Reached Destination Hub",
        51: "Picked Up",
        70: "Pickup Booked",
        88: "Untraceable - Please Contact Support",
        89: "Issue with Recipient Address",
        90: "Returned to Seller City",
    }

    def __init__(self, db: Session, webhook_secret: str | None = None):
        """
        Initialize webhook service.

        Args:
            db: Database session
            webhook_secret: Secret token for webhook verification
        """
        self.db = db
        self.webhook_secret = webhook_secret

    def verify_signature(self, payload: dict, signature: str) -> bool:
        """
        Verify webhook signature from Shiprocket.

        Args:
            payload: Webhook payload data
            signature: Signature from anx-api-key header

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        try:
            # Compute HMAC signature
            payload_string = json.dumps(payload, sort_keys=True)
            computed_signature = hmac.new(
                self.webhook_secret.encode(), payload_string.encode(), hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(computed_signature, signature)
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False

    async def process_webhook(self, webhook_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process incoming webhook from Shiprocket.

        Args:
            webhook_data: Webhook payload from Shiprocket

        Returns:
            Processing result dict

        Sample webhook data:
        {
            "awb": "19041424751540",
            "courier_name": "Delhivery Surface",
            "current_status": "IN TRANSIT",
            "current_status_id": 20,
            "shipment_status": "IN TRANSIT",
            "shipment_status_id": 18,
            "current_timestamp": "23 05 2023 11:43:52",
            "order_id": "1373900_150876814",
            "sr_order_id": 348456385,
            "awb_assigned_date": "2023-05-19 11:59:16",
            "pickup_scheduled_date": "2023-05-19 11:59:17",
            "etd": "2023-05-23 15:40:19",
            "scans": [...]
        }
        """
        try:
            # Extract key fields
            awb = webhook_data.get("awb")
            current_status_id = webhook_data.get("current_status_id")
            current_status = webhook_data.get("current_status")
            courier_name = webhook_data.get("courier_name")
            etd = webhook_data.get("etd")
            scans = webhook_data.get("scans", [])
            pod_status = webhook_data.get("pod_status")

            if not awb:
                logger.error("Webhook missing AWB number")
                return {"success": False, "error": "Missing AWB"}

            # Find reward by AWB
            reward = self.db.query(UserReward).filter(UserReward.tracking_number == awb).first()

            if not reward:
                logger.warning(f"Reward not found for AWB: {awb}")
                return {"success": False, "error": f"Reward not found for AWB {awb}"}

            # Map status code to our internal status
            new_status = self.STATUS_MAPPING.get(
                current_status_id,
                RewardStatus.IN_TRANSIT,  # Default to in_transit for unknown codes
            )

            # Update reward
            old_status = reward.status
            reward.status = new_status
            reward.courier_partner = courier_name or reward.courier_partner
            reward.last_tracking_update = func.now()

            # Update ETD if provided
            if etd:
                try:
                    reward.estimated_delivery_date = datetime.strptime(
                        etd, "%Y-%m-%d %H:%M:%S"
                    ).date()
                except:
                    pass

            # Process scans (tracking history)
            if scans:
                latest_scan = scans[-1]  # Get most recent scan

                # Update current location
                reward.current_location = latest_scan.get("location")

                # Initialize status history if needed
                if not reward.status_history:
                    reward.status_history = []

                # Add to status history
                reward.status_history.append(
                    {
                        "status": latest_scan.get("sr-status-label", current_status),
                        "status_code": latest_scan.get("sr-status"),
                        "timestamp": latest_scan.get("date"),
                        "location": latest_scan.get("location"),
                        "activity": latest_scan.get("activity"),
                        "courier_status": latest_scan.get("status"),
                    }
                )

                # Check if delivered
                sr_status = latest_scan.get("sr-status")
                if sr_status == "7" or current_status_id == 7:
                    reward.status = RewardStatus.DELIVERED
                    reward.delivered_at = func.now()
                    try:
                        reward.actual_delivery_date = datetime.strptime(
                            latest_scan.get("date"), "%Y-%m-%d %H:%M:%S"
                        ).date()
                    except:
                        reward.actual_delivery_date = datetime.now().date()

            # Update POD (Proof of Delivery) if available
            if pod_status:
                if not reward.status_history:
                    reward.status_history = []

                reward.status_history.append(
                    {"pod_status": pod_status, "timestamp": datetime.utcnow().isoformat()}
                )

            # Commit changes
            self.db.commit()

            logger.info(
                f"✅ Webhook processed for AWB {awb}: "
                f"{old_status.value} → {new_status.value} "
                f"(Shiprocket status: {current_status})"
            )

            return {
                "success": True,
                "reward_id": str(reward.id),
                "old_status": old_status.value,
                "new_status": new_status.value,
                "current_location": reward.current_location,
            }

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def get_status_label(self, status_code: int) -> str:
        """
        Get user-friendly status label.

        Args:
            status_code: Shiprocket status code

        Returns:
            Human-readable status label
        """
        return self.STATUS_LABELS.get(status_code, f"Status Code {status_code}")

    def should_notify_user(self, old_status: RewardStatus, new_status: RewardStatus) -> bool:
        """
        Determine if user should be notified of status change.

        Args:
            old_status: Previous reward status
            new_status: New reward status

        Returns:
            True if user should be notified
        """
        # Notify on these important status changes
        notify_statuses = [
            RewardStatus.SHIPPED,
            RewardStatus.OUT_FOR_DELIVERY,
            RewardStatus.DELIVERED,
            RewardStatus.RTO_INITIATED,
        ]

        return new_status in notify_statuses and old_status != new_status

    def should_alert_admin(self, status: RewardStatus, status_code: int) -> bool:
        """
        Determine if admin should be alerted about this status.

        Args:
            status: Current reward status
            status_code: Shiprocket status code

        Returns:
            True if admin alert is needed
        """
        # Alert admin on problematic statuses
        alert_codes = [
            33,  # Lost
            35,  # Pickup Exception
            36,  # Undelivered
            37,  # Delivery Delayed
            40,  # Damaged
            88,  # Untraceable
            89,  # Issue with recipient
        ]

        return status_code in alert_codes
