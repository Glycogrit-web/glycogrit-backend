"""
Fitness Tracker Queries (Read Operations)
"""

from dataclasses import dataclass

from app.modules.fitness_trackers.domain.value_objects import ProviderType


@dataclass
class GetConnectionQuery:
    """Query to get connection by ID"""
    connection_id: int


@dataclass
class GetUserConnectionQuery:
    """Query to get user's connection for specific provider"""
    user_id: int
    provider: ProviderType


@dataclass
class GetUserConnectionsQuery:
    """Query to get all connections for user"""
    user_id: int
    active_only: bool = True


@dataclass
class GetConnectionStatusQuery:
    """Query to get connection status and health"""
    user_id: int
    provider: ProviderType


@dataclass
class GetAvailableProvidersQuery:
    """Query to get list of configured providers"""
    pass


@dataclass
class GetAuthorizationUrlQuery:
    """Query to get OAuth authorization URL"""
    provider: ProviderType
    state: str | None = None
