"""
Fitness Tracker Commands (Write Operations)
"""

from dataclasses import dataclass

from app.modules.fitness_trackers.domain.value_objects import ProviderType


@dataclass
class ConnectProviderCommand:
    """Command to connect a fitness tracker provider"""

    user_id: int
    provider: ProviderType
    authorization_code: str


@dataclass
class DisconnectProviderCommand:
    """Command to disconnect a fitness tracker provider"""

    user_id: int
    provider: ProviderType


@dataclass
class RefreshTokenCommand:
    """Command to refresh access token"""

    connection_id: int


@dataclass
class SyncActivitiesCommand:
    """Command to sync activities from provider"""

    connection_id: int
    event_id: int | None = None
    force: bool = False  # Force sync even if recently synced


@dataclass
class EnableSyncCommand:
    """Command to enable automatic syncing"""

    user_id: int
    provider: ProviderType


@dataclass
class DisableSyncCommand:
    """Command to disable automatic syncing"""

    user_id: int
    provider: ProviderType


@dataclass
class SubscribeWebhookCommand:
    """Command to subscribe to webhook notifications"""

    connection_id: int
    callback_url: str


@dataclass
class UnsubscribeWebhookCommand:
    """Command to unsubscribe from webhook notifications"""

    connection_id: int
