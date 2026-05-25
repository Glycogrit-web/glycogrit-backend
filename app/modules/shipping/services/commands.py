"""
Command objects for Shipping Service.

Commands represent write operations that modify state.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class CreateShipmentCommand:
    """
    Command to create a new shipment order.
    """
    user_reward_id: str
    event_id: int
    user_id: int
    shipping_address: dict[str, Any]
    product_details: dict[str, Any]

    def __post_init__(self):
        """Validate command data"""
        if not self.user_reward_id:
            raise ValueError("user_reward_id is required")
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.shipping_address:
            raise ValueError("shipping_address is required")
        if not self.product_details:
            raise ValueError("product_details is required")


@dataclass
class RetryShipmentCommand:
    """
    Command to retry a failed shipment.
    """
    shipment_id: int

    def __post_init__(self):
        """Validate command data"""
        if self.shipment_id <= 0:
            raise ValueError("shipment_id must be positive")


@dataclass
class CancelShipmentCommand:
    """
    Command to cancel a shipment.
    """
    shipment_id: int
    reason: str = "Cancelled by user"

    def __post_init__(self):
        """Validate command data"""
        if self.shipment_id <= 0:
            raise ValueError("shipment_id must be positive")
        if not self.reason:
            raise ValueError("reason is required")


@dataclass
class SchedulePickupCommand:
    """
    Command to schedule pickup for a shipment.
    """
    shipment_id: int
    pickup_date: str  # ISO format date

    def __post_init__(self):
        """Validate command data"""
        if self.shipment_id <= 0:
            raise ValueError("shipment_id must be positive")
        if not self.pickup_date:
            raise ValueError("pickup_date is required")


@dataclass
class GenerateManifestCommand:
    """
    Command to generate manifest for shipments.
    """
    shipment_ids: list[int]

    def __post_init__(self):
        """Validate command data"""
        if not self.shipment_ids:
            raise ValueError("At least one shipment_id is required")
        if any(sid <= 0 for sid in self.shipment_ids):
            raise ValueError("All shipment_ids must be positive")
