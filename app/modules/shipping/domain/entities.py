"""
Domain Entities for Shipping Module

Domain entities encapsulate business rules and behavior.
They represent core business concepts with identity.
"""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from app.core.enums import ShipmentStatus
from app.modules.shipping.domain.value_objects import (
    CourierInfo,
    PickupSchedule,
    ShiprocketOrderId,
    TrackingNumber,
)

if TYPE_CHECKING:
    from app.models.shiprocket_order import ShiprocketOrder


class ShipmentEntity:
    """
    Domain entity for Shipment with business rules.

    This entity encapsulates shipping business logic and rules,
    separating domain concerns from data persistence.
    """

    def __init__(self, shipment: "ShiprocketOrder"):
        """
        Initialize ShipmentEntity from ORM model.

        Args:
            shipment: ShiprocketOrder ORM model instance
        """
        self._shipment = shipment

    @property
    def id(self) -> int:
        """Shipment ID"""
        return self._shipment.id

    @property
    def order_reference(self) -> str:
        """Our internal order reference"""
        return self._shipment.order_reference

    @property
    def status(self) -> str:
        """Current shipment status"""
        return self._shipment.status.value if self._shipment.status else "pending"

    @property
    def tracking_number(self) -> TrackingNumber | None:
        """Get tracking number as value object"""
        if self._shipment.shiprocket_awb:
            return TrackingNumber(
                value=self._shipment.shiprocket_awb, courier_name=self._shipment.courier_name
            )
        return None

    @property
    def shiprocket_order_id(self) -> ShiprocketOrderId | None:
        """Get Shiprocket order ID as value object"""
        if self._shipment.shiprocket_order_id:
            return ShiprocketOrderId(value=self._shipment.shiprocket_order_id)
        return None

    @property
    def courier_info(self) -> CourierInfo | None:
        """Get courier information as value object"""
        if self._shipment.courier_id and self._shipment.courier_name:
            return CourierInfo(
                courier_id=self._shipment.courier_id, courier_name=self._shipment.courier_name
            )
        return None

    @property
    def pickup_schedule(self) -> PickupSchedule | None:
        """Get pickup schedule as value object"""
        if self._shipment.pickup_location:
            return PickupSchedule(
                location=self._shipment.pickup_location,
                scheduled_date=self._shipment.pickup_scheduled_date,
                token_number=self._shipment.pickup_token_number,
            )
        return None

    # Business Rule Methods

    @property
    def is_pending(self) -> bool:
        """Check if order is still pending (not yet sent to Shiprocket)"""
        return self.status == ShipmentStatus.PENDING.value

    @property
    def is_created_in_shiprocket(self) -> bool:
        """Check if order has been created in Shiprocket"""
        return self._shipment.shiprocket_order_id is not None

    @property
    def has_tracking_number(self) -> bool:
        """Check if tracking number has been assigned"""
        return self._shipment.shiprocket_awb is not None

    @property
    def has_label(self) -> bool:
        """Check if shipping label has been generated"""
        return self._shipment.label_url is not None

    @property
    def is_pickup_scheduled(self) -> bool:
        """Check if pickup has been scheduled"""
        return self._shipment.pickup_scheduled_date is not None

    @property
    def is_manifested(self) -> bool:
        """Check if manifest has been generated"""
        return self._shipment.manifest_url is not None

    @property
    def is_failed(self) -> bool:
        """Check if order creation failed"""
        return self.status == ShipmentStatus.CANCELLED.value

    @property
    def can_retry(self) -> bool:
        """
        Business rule: Check if failed order can be retried.

        An order can be retried if:
        1. Status is FAILED
        2. Not yet created in Shiprocket (no shiprocket_order_id)
        3. Created less than 7 days ago

        Returns:
            True if order can be retried
        """
        if not self.is_failed:
            return False

        if self.is_created_in_shiprocket:
            return False  # Already created, cannot retry

        # Check if order is not too old
        if self._shipment.created_at:
            age_days = (datetime.now() - self._shipment.created_at).days
            return age_days < 7

        return True

    @property
    def can_cancel(self) -> bool:
        """
        Business rule: Check if order can be cancelled.

        An order can be cancelled if:
        1. Not yet manifested
        2. Not failed (failed orders don't need cancellation)
        3. Created in Shiprocket (has shiprocket_order_id)

        Returns:
            True if order can be cancelled
        """
        if self.is_failed:
            return False  # Failed orders don't need cancellation

        if not self.is_created_in_shiprocket:
            return False  # Nothing to cancel

        if self.is_manifested:
            return False  # Too late to cancel

        return True

    @property
    def requires_pickup(self) -> bool:
        """
        Business rule: Check if pickup needs to be scheduled.

        Returns:
            True if label is generated but pickup not scheduled
        """
        return self.has_label and not self.is_pickup_scheduled

    @property
    def is_ready_for_manifest(self) -> bool:
        """
        Business rule: Check if order is ready for manifest generation.

        An order is ready for manifest if:
        1. Pickup is scheduled
        2. Not yet manifested

        Returns:
            True if ready for manifest
        """
        return self.is_pickup_scheduled and not self.is_manifested

    def get_age_in_days(self) -> int:
        """
        Calculate order age in days.

        Returns:
            Age in days since order creation
        """
        if not self._shipment.created_at:
            return 0
        return (datetime.now() - self._shipment.created_at).days

    def is_stale(self, max_age_days: int = 30) -> bool:
        """
        Business rule: Check if pending order is stale.

        Pending orders older than max_age_days should be reviewed/cancelled.

        Args:
            max_age_days: Maximum age in days (default: 30)

        Returns:
            True if order is pending and older than max_age_days
        """
        return self.is_pending and self.get_age_in_days() > max_age_days

    def get_expected_pickup_date(self) -> date | None:
        """
        Business rule: Calculate expected pickup date.

        If pickup not scheduled, estimate based on label generation date.

        Returns:
            Expected pickup date or None
        """
        if self.is_pickup_scheduled:
            return self._shipment.pickup_scheduled_date

        if self._shipment.label_generated_at:
            # Estimate: pickup usually within 2 business days
            return (self._shipment.label_generated_at + timedelta(days=2)).date()

        return None

    def has_error(self) -> bool:
        """Check if order has error message"""
        return self._shipment.error_message is not None

    def get_error_summary(self) -> str | None:
        """Get error message summary"""
        if not self.has_error():
            return None

        error_msg = self._shipment.error_message
        # Truncate long error messages
        if len(error_msg) > 200:
            return error_msg[:197] + "..."
        return error_msg

    def can_generate_label(self) -> bool:
        """
        Business rule: Check if label can be generated.

        Returns:
            True if order is created in Shiprocket but no label yet
        """
        return self.is_created_in_shiprocket and not self.has_label

    def __repr__(self) -> str:
        return (
            f"ShipmentEntity(id={self.id}, "
            f"order_reference='{self.order_reference}', "
            f"status='{self.status}')"
        )
