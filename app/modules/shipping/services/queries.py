"""
Query objects for Shipping Service.

Queries represent read operations that don't modify state.
"""
from dataclasses import dataclass


@dataclass
class GetShipmentByIdQuery:
    """
    Query to get a shipment by ID.
    """
    shipment_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.shipment_id <= 0:
            raise ValueError("shipment_id must be positive")


@dataclass
class GetShipmentByUserRewardQuery:
    """
    Query to get a shipment by user reward ID.
    """
    user_reward_id: str

    def __post_init__(self):
        """Validate query data"""
        if not self.user_reward_id:
            raise ValueError("user_reward_id is required")


@dataclass
class GetUserShipmentsQuery:
    """
    Query to get all shipments for a user.
    """
    user_id: int
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetEventShipmentsQuery:
    """
    Query to get all shipments for an event.
    """
    event_id: int
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class TrackShipmentQuery:
    """
    Query to get tracking information for a shipment.
    """
    shipment_id: int

    def __post_init__(self):
        """Validate query data"""
        if self.shipment_id <= 0:
            raise ValueError("shipment_id must be positive")


@dataclass
class GetStaleShipmentsQuery:
    """
    Query to get stale shipments that need attention.
    """
    max_age_days: int = 30

    def __post_init__(self):
        """Validate query data"""
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be positive")


@dataclass
class GetShipmentsByStatusQuery:
    """
    Query to get shipments by status.
    """
    status: str
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if not self.status:
            raise ValueError("status is required")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
