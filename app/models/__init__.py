"""
SQLAlchemy Models Package

Note: Some models are defined in DDD modules to avoid circular imports:
- Registration, RegistrationTier, EventRegistrationTier → app.modules.registrations.domain
- Payment, PaymentLink, Settlement → app.modules.payments.domain
- Event, EventActivity → app.modules.events.domain
- ShiprocketOrder, ShiprocketConfig → app.modules.shipping.domain

Import these from their respective DDD domain locations.
"""

from app.core.enums import RewardStatus, RewardType  # Import from centralized enums
from app.models.activity_progress import ActivityProgress
from app.models.fitbit_connection import FitbitConnection
from app.models.fitness_tracker import FitnessTrackerConnection  # noqa: F401

# Register fitness tracker connection models (needed for User relationships)
from app.models.strava_connection import StravaConnection
from app.models.user import User
from app.models.user_activity_log import UserActivityLog
from app.models.user_reward import UserReward

# ============================================================================
# Register DDD domain models with SQLAlchemy
# These imports are needed so SQLAlchemy can resolve string-based relationships
# in the User model (e.g., relationship("Registration", ...))
# We import but don't export them - they should be imported from their domain locations
# ============================================================================
from app.modules.events.domain.event import Event, EventActivity  # noqa: F401
from app.modules.payments.domain.payment import Payment  # noqa: F401
from app.modules.payments.domain.payment_link import PaymentLink  # noqa: F401
from app.modules.registrations.domain.event_registration_tier import (  # noqa: F401
    EventRegistrationTier,
)
from app.modules.registrations.domain.registration import Registration  # noqa: F401
from app.modules.shipping.domain.shipment import ShiprocketOrder  # noqa: F401

# NOTE: FitnessConnection (new DDD model) is NOT imported here to avoid conflict
# with FitnessTrackerConnection. Import it directly where needed or from conftest.py

__all__ = [
    "User",
    "UserActivityLog",
    "StravaConnection",
    "FitbitConnection",
    "ActivityProgress",
    "UserReward",
    "RewardStatus",
    "RewardType",
]
