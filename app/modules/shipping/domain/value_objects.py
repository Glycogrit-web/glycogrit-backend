"""
Value Objects for Shipping Domain

Value objects are immutable objects that represent concepts in the domain
through their attributes rather than identity.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TrackingNumber:
    """
    Value object for shipment tracking numbers (AWB - Air Waybill).

    Immutable representation of a tracking number from the courier.
    """

    value: str
    courier_name: str | None = None

    def __post_init__(self):
        """Validate tracking number constraints"""
        if not self.value:
            raise ValueError("Tracking number cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Tracking number too long (max 100 characters)")

    def __str__(self) -> str:
        if self.courier_name:
            return f"{self.value} ({self.courier_name})"
        return self.value

    def __repr__(self) -> str:
        return f"TrackingNumber(value='{self.value}', courier_name='{self.courier_name}')"


@dataclass(frozen=True)
class ShiprocketOrderId:
    """
    Value object for Shiprocket order IDs.

    Ensures order IDs are valid and immutable.
    """

    value: str

    def __post_init__(self):
        """Validate order ID constraints"""
        if not self.value:
            raise ValueError("Shiprocket order ID cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Order ID too long (max 100 characters)")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ShiprocketOrderId(value='{self.value}')"


@dataclass(frozen=True)
class ShippingAddress:
    """
    Value object for shipping addresses.

    Encapsulates address validation and formatting.
    """

    name: str
    phone: str
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    pincode: str
    country: str = "India"

    def __post_init__(self):
        """Validate address constraints"""
        if not self.name or len(self.name) < 2:
            raise ValueError("Name must be at least 2 characters")
        if not self.phone or len(self.phone) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if not self.address_line1:
            raise ValueError("Address line 1 is required")
        if not self.city:
            raise ValueError("City is required")
        if not self.state:
            raise ValueError("State is required")
        if not self.pincode or len(self.pincode) != 6:
            raise ValueError("Pincode must be 6 digits")

    def to_dict(self) -> dict:
        """Convert to dictionary for API requests"""
        result = {
            "name": self.name,
            "phone": self.phone,
            "address": self.address_line1,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "country": self.country,
        }
        if self.address_line2:
            result["address"] = f"{self.address_line1}, {self.address_line2}"
        return result

    def __str__(self) -> str:
        address = self.address_line1
        if self.address_line2:
            address = f"{address}, {self.address_line2}"
        return f"{address}, {self.city}, {self.state} - {self.pincode}"

    def __repr__(self) -> str:
        return f"ShippingAddress(name='{self.name}', city='{self.city}', pincode='{self.pincode}')"


@dataclass(frozen=True)
class PickupSchedule:
    """
    Value object for pickup scheduling information.
    """

    location: str
    scheduled_date: date | None = None
    token_number: str | None = None

    def __post_init__(self):
        """Validate pickup schedule constraints"""
        if not self.location:
            raise ValueError("Pickup location is required")

    def is_scheduled(self) -> bool:
        """Check if pickup is actually scheduled"""
        return self.scheduled_date is not None

    def __str__(self) -> str:
        if self.scheduled_date:
            return f"Pickup at {self.location} on {self.scheduled_date}"
        return f"Pickup location: {self.location} (not scheduled)"

    def __repr__(self) -> str:
        return (
            f"PickupSchedule(location='{self.location}', "
            f"scheduled_date={self.scheduled_date}, "
            f"token_number='{self.token_number}')"
        )


@dataclass(frozen=True)
class CourierInfo:
    """
    Value object for courier information.
    """

    courier_id: int
    courier_name: str

    def __post_init__(self):
        """Validate courier info constraints"""
        if self.courier_id <= 0:
            raise ValueError("Courier ID must be positive")
        if not self.courier_name:
            raise ValueError("Courier name is required")

    def __str__(self) -> str:
        return f"{self.courier_name} (ID: {self.courier_id})"

    def __repr__(self) -> str:
        return f"CourierInfo(courier_id={self.courier_id}, courier_name='{self.courier_name}')"
