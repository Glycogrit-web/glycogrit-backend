"""
Fitness Trackers Module - Domain-Driven Design

Unified OAuth framework for fitness tracker integrations.

Consolidates 6 separate API files (3,511 lines) into a single DDD module:
- Strava
- Garmin
- Fitbit
- Wahoo
- Google Fit
- Polar

Public API:
    Domain:
        - FitnessConnection: Unified connection model
        - ConnectionEntity: Connection business rules
        - ProviderType: Provider enumeration

    Value Objects:
        - AccessToken: OAuth access token with expiration
        - RefreshToken: OAuth refresh token
        - AthleteId: Provider-specific athlete ID
        - SyncWindow: Time window for syncing
        - SyncStatus: Sync operation result

    Services:
        - FitnessTrackerService: Main service with CQRS
        - OAuthProvider: Abstract provider interface
        - ProviderFactory: Provider instance factory

    API:
        - fitness_trackers_router: Unified API endpoints
"""

from app.modules.fitness_trackers.domain.connection import FitnessConnection, ProviderType
from app.modules.fitness_trackers.domain.entities import ConnectionEntity
from app.modules.fitness_trackers.domain.value_objects import (
    AccessToken,
    RefreshToken,
    AthleteId,
    SyncWindow,
    SyncStatus,
)
from app.modules.fitness_trackers.services.fitness_tracker_service import FitnessTrackerService
from app.modules.fitness_trackers.services.provider_factory import ProviderFactory
from app.modules.fitness_trackers.api.fitness_trackers import router as fitness_trackers_router

__all__ = [
    # Domain
    "FitnessConnection",
    "ConnectionEntity",
    "ProviderType",
    # Value Objects
    "AccessToken",
    "RefreshToken",
    "AthleteId",
    "SyncWindow",
    "SyncStatus",
    # Services
    "FitnessTrackerService",
    "ProviderFactory",
    # API
    "fitness_trackers_router",
]
