"""
Rewards Module

Physical reward fulfillment via Shiprocket integration.
"""

from app.modules.rewards.api.rewards import router as rewards_router
from app.modules.rewards.domain.value_objects import (
    RewardCategory,
    ShipmentStatus,
    ShippingAddress,
    ShiprocketOrderId,
    TrackingNumber,
)
from app.modules.rewards.services.reward_service import RewardService

__all__ = [
    "ShippingAddress",
    "ShipmentStatus",
    "ShiprocketOrderId",
    "TrackingNumber",
    "RewardCategory",
    "RewardService",
    "rewards_router",
]
