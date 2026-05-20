"""
Rewards Module

Physical reward fulfillment via Shiprocket integration.
"""

from app.modules.rewards.domain.value_objects import (
    ShippingAddress,
    ShipmentStatus,
    ShiprocketOrderId,
    TrackingNumber,
    RewardCategory,
)
from app.modules.rewards.services.reward_service import RewardService
from app.modules.rewards.api.rewards import router as rewards_router

__all__ = [
    "ShippingAddress",
    "ShipmentStatus",
    "ShiprocketOrderId",
    "TrackingNumber",
    "RewardCategory",
    "RewardService",
    "rewards_router",
]
