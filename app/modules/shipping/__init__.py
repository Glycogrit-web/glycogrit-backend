"""
Shipping Module

This module handles all shipping and fulfillment operations including:
- Shipment order creation and tracking
- Integration with shipping providers (Shiprocket)
- Pickup scheduling and manifest generation
- Webhook handling for shipment status updates

Architecture:
    - domain/: Domain models, entities, and value objects
    - services/: Application services and business logic
    - integrations/: External provider integrations (Shiprocket)
    - repositories/: Data access layer
    - schemas/: Request/response validation schemas
    - api/: HTTP route handlers

Usage:
    from app.modules.shipping import ShippingService, ShipmentEntity
    from app.modules.shipping import ShiprocketOrder, TrackingNumber
"""

# Domain layer exports
from app.modules.shipping.domain.shipment import ShiprocketOrder, ShiprocketOrderStatus
from app.modules.shipping.domain.config import ShiprocketConfig
from app.modules.shipping.domain.entities import ShipmentEntity
from app.modules.shipping.domain.value_objects import (
    TrackingNumber,
    ShiprocketOrderId,
    ShippingAddress,
    PickupSchedule,
    CourierInfo
)

# Service layer exports
from app.modules.shipping.services.shipping_service import ShippingService
from app.modules.shipping.services.commands import (
    CreateShipmentCommand,
    RetryShipmentCommand,
    CancelShipmentCommand,
    SchedulePickupCommand,
    GenerateManifestCommand
)
from app.modules.shipping.services.queries import (
    GetShipmentByIdQuery,
    GetShipmentByUserRewardQuery,
    GetUserShipmentsQuery,
    GetEventShipmentsQuery,
    TrackShipmentQuery,
    GetStaleShipmentsQuery,
    GetShipmentsByStatusQuery
)

__all__ = [
    # Domain
    'ShiprocketOrder',
    'ShiprocketOrderStatus',
    'ShiprocketConfig',
    'ShipmentEntity',
    'TrackingNumber',
    'ShiprocketOrderId',
    'ShippingAddress',
    'PickupSchedule',
    'CourierInfo',

    # Services
    'ShippingService',

    # Commands
    'CreateShipmentCommand',
    'RetryShipmentCommand',
    'CancelShipmentCommand',
    'SchedulePickupCommand',
    'GenerateManifestCommand',

    # Queries
    'GetShipmentByIdQuery',
    'GetShipmentByUserRewardQuery',
    'GetUserShipmentsQuery',
    'GetEventShipmentsQuery',
    'TrackShipmentQuery',
    'GetStaleShipmentsQuery',
    'GetShipmentsByStatusQuery'
]