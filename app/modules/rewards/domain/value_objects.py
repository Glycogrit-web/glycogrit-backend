"""
Reward Value Objects
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class RewardCategory(str, Enum):
    """Reward category"""
    MEDAL = "medal"
    TSHIRT = "tshirt"
    FINISHER_KIT = "finisher_kit"
    BADGE = "badge"


class ShipmentStatus(str, Enum):
    """Shipment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ShiprocketOrderId:
    """Shiprocket order ID"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Shiprocket order ID cannot be empty")


@dataclass(frozen=True)
class TrackingNumber:
    """Shipment tracking number"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Tracking number cannot be empty")


@dataclass(frozen=True)
class ShippingAddress:
    """Shipping address details"""
    name: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    pincode: str
    phone: str

    def __post_init__(self):
        if not all([self.name, self.address_line1, self.city, self.state, self.pincode, self.phone]):
            raise ValueError("Required address fields cannot be empty")
        if len(self.pincode) != 6:
            raise ValueError("Pincode must be 6 digits")

    def to_dict(self) -> dict:
        """Convert to dict for API"""
        return {
            "name": self.name,
            "address": self.address_line1,
            "address_2": self.address_line2 or "",
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "phone": self.phone,
        }
