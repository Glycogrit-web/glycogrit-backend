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
        5: RewardStatus.CANCELLED,  # Canceled
        6: RewardStatus.SHIPPED,  # Shipped
        7: RewardStatus.DELIVERED,  # Delivered
        8: RewardStatus.PENDING_SHIPMENT,  # ePayment Failed
        9: RewardStatus.RTO_DELIVERED,  # Returned
        10: RewardStatus.PENDING_SHIPMENT,  # Unmapped
        11: RewardStatus.PENDING_SHIPMENT,  # Unfulfillable
        12: RewardStatus.PICKUP_SCHEDULED,  # Pickup Queue
        13: RewardStatus.PICKUP_SCHEDULED,  # Pickup Rescheduled
        14: RewardStatus.PICKUP_SCHEDULED,  # Pickup Error
        15: RewardStatus.RTO_INITIATED,  # RTO Initiated
        16: RewardStatus.RTO_DELIVERED,  # RTO Delivered
        17: RewardStatus.RTO_DELIVERED,  # RTO Acknowledged
        18: RewardStatus.PENDING_SHIPMENT,  # Cancellation Requested
        19: RewardStatus.OUT_FOR_DELIVERY,  # Out for Delivery
        20: RewardStatus.IN_TRANSIT,  # In Transit
        21: RewardStatus.PENDING_SHIPMENT,  # Return Pending
        22: RewardStatus.RTO_INITIATED,  # Return Initiated
        23: RewardStatus.RTO_INITIATED,  # Return Pickup Queued
        24: RewardStatus.RTO_INITIATED,  # Return Pickup Error
        25: RewardStatus.RTO_INITIATED,  # Return In Transit
        26: RewardStatus.RTO_DELIVERED,  # Return Delivered
        27: RewardStatus.CANCELLED,  # Return Cancelled
        28: RewardStatus.RTO_INITIATED,  # Return Pickup Generated
        29: RewardStatus.PENDING_SHIPMENT,  # Return Cancellation Requested
        30: RewardStatus.CANCELLED,  # Return Pickup Cancelled
        31: RewardStatus.RTO_INITIATED,  # Return Pickup Rescheduled
        32: RewardStatus.RTO_INITIATED,  # Return Picked Up
        33: RewardStatus.SHIPPED,  # Lost
        34: RewardStatus.PICKUP_SCHEDULED,  # Out For Pickup
        35: RewardStatus.PICKUP_SCHEDULED,  # Pickup Exception
        36: RewardStatus.OUT_FOR_DELIVERY,  # Undelivered
        37: RewardStatus.IN_TRANSIT,  # Delivery Delayed
        38: RewardStatus.DELIVERED,  # Partial Delivered
        39: RewardStatus.DELIVERED,  # Destroyed
        40: RewardStatus.DELIVERED,  # Damaged
        41: RewardStatus.DELIVERED,  # Fulfilled
        42: RewardStatus.DELIVERED,  # Archived
        43: RewardStatus.IN_TRANSIT,  # Reached Destination Hub
        44: RewardStatus.IN_TRANSIT,  # Misrouted
        45: RewardStatus.RTO_INITIATED,  # RTO_OFD
        46: RewardStatus.RTO_INITIATED,  # RTO_NDR
        47: RewardStatus.RTO_INITIATED,  # Return Out For Pickup
        48: RewardStatus.RTO_INITIATED,  # Return Out For Delivery
        49: RewardStatus.RTO_INITIATED,  # Return Pickup Exception
        50: RewardStatus.RTO_INITIATED,  # Return Undelivered
        51: RewardStatus.SHIPPED,  # Picked Up
        52: RewardStatus.DELIVERED,  # Self Fulfilled
        53: RewardStatus.DELIVERED,  # Disposed Off
        54: RewardStatus.CANCELLED,  # Canceled before Dispatched
        55: RewardStatus.RTO_INITIATED,  # RTO In-Transit
        57: RewardStatus.PENDING_SHIPMENT,  # QC Failed
        58: RewardStatus.IN_TRANSIT,  # Reached Warehouse
        59: RewardStatus.IN_TRANSIT,  # Custom Cleared
        60: RewardStatus.IN_TRANSIT,  # In Flight
        61: RewardStatus.SHIPPED,  # Handover to Courier
        62: RewardStatus.PICKUP_SCHEDULED,  # Booked
        64: RewardStatus.IN_TRANSIT,  # In Transit Overseas
        65: RewardStatus.IN_TRANSIT,  # Connection Aligned
        66: RewardStatus.IN_TRANSIT,  # Reached Overseas Warehouse
        67: RewardStatus.IN_TRANSIT,  # Custom Cleared Overseas
        68: RewardStatus.RTO_DELIVERED,  # RETURN ACKNOWLEGED
        69: RewardStatus.LABEL_GENERATED,  # Box Packing
        70: RewardStatus.PICKUP_SCHEDULED,  # Pickup Booked
        71: RewardStatus.PICKUP_SCHEDULED,  # DARKSTORE SCHEDULED
        72: RewardStatus.PENDING_SHIPMENT,  # Allocation in Progress
        73: RewardStatus.PENDING_SHIPMENT,  # FC Allocated
        74: RewardStatus.PENDING_SHIPMENT,  # Picklist Generated
        75: RewardStatus.PENDING_SHIPMENT,  # Ready to Pack
        76: RewardStatus.LABEL_GENERATED,  # Packed
        80: RewardStatus.LABEL_GENERATED,  # FC MANIFEST GENERATED
        81: RewardStatus.IN_TRANSIT,  # PROCESSED AT WAREHOUSE
        82: RewardStatus.LABEL_GENERATED,  # PACKED EXCEPTION
        83: RewardStatus.SHIPPED,  # HANDOVER EXCEPTION
        87: RewardStatus.RTO_INITIATED,  # RTO_LOCK
        88: RewardStatus.IN_TRANSIT,  # UNTRACEABLE
        89: RewardStatus.OUT_FOR_DELIVERY,  # ISSUE_RELATED_TO_THE_RECIPIENT
        90: RewardStatus.RTO_INITIATED,  # REACHED_BACK_AT_SELLER_CITY
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
                self.webhook_secret.encode(),
                payload_string.encode(),
                hashlib.sha256
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
            reward = self.db.query(UserReward).filter(
                UserReward.tracking_number == awb
            ).first()

            if not reward:
                logger.warning(f"Reward not found for AWB: {awb}")
                return {"success": False, "error": f"Reward not found for AWB {awb}"}

            # Map status code to our internal status
            new_status = self.STATUS_MAPPING.get(
                current_status_id,
                RewardStatus.IN_TRANSIT  # Default to in_transit for unknown codes
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
                reward.status_history.append({
                    "status": latest_scan.get("sr-status-label", current_status),
                    "status_code": latest_scan.get("sr-status"),
                    "timestamp": latest_scan.get("date"),
                    "location": latest_scan.get("location"),
                    "activity": latest_scan.get("activity"),
                    "courier_status": latest_scan.get("status")
                })

                # Check if delivered
                sr_status = latest_scan.get("sr-status")
                if sr_status == "7" or current_status_id == 7:
                    reward.status = RewardStatus.DELIVERED
                    reward.delivered_at = func.now()
                    try:
                        reward.actual_delivery_date = datetime.strptime(
                            latest_scan.get("date"),
                            "%Y-%m-%d %H:%M:%S"
                        ).date()
                    except:
                        reward.actual_delivery_date = datetime.now().date()

            # Update POD (Proof of Delivery) if available
            if pod_status:
                if not reward.status_history:
                    reward.status_history = []

                reward.status_history.append({
                    "pod_status": pod_status,
                    "timestamp": datetime.utcnow().isoformat()
                })

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
                "current_location": reward.current_location
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
