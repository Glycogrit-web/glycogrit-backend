"""
Fitness Tracker Domain Entities

Business logic for fitness tracker connections and synchronization.
"""

from datetime import datetime, timedelta

from app.modules.fitness_trackers.domain.value_objects import (
    AccessToken,
    AthleteId,
    ProviderType,
    RefreshToken,
    SyncWindow,
)


class ConnectionEntity:
    """
    Connection entity with business rules for OAuth connections.
    """

    def __init__(self, connection):
        """
        Initialize from FitnessConnection model.

        Args:
            connection: FitnessConnection database model
        """
        self.connection = connection

    @property
    def access_token(self) -> AccessToken | None:
        """Get access token as value object"""
        if not self.connection.access_token or not self.connection.token_expires_at:
            return None
        return AccessToken(
            value=self.connection.access_token,
            expires_at=self.connection.token_expires_at
        )

    @property
    def refresh_token(self) -> RefreshToken | None:
        """Get refresh token as value object"""
        if not self.connection.refresh_token:
            return None
        return RefreshToken(value=self.connection.refresh_token)

    @property
    def athlete_id(self) -> AthleteId:
        """Get athlete ID as value object"""
        return AthleteId(
            provider=self.connection.provider,
            value=self.connection.athlete_id
        )

    # Business Rules

    def is_token_valid(self) -> bool:
        """
        Business Rule: Token is valid if exists and not expired.

        Returns:
            True if token is valid
        """
        token = self.access_token
        if not token:
            return False
        return not token.is_expired

    def needs_token_refresh(self) -> bool:
        """
        Business Rule: Token needs refresh if expires in < 1 hour.

        Returns:
            True if token should be refreshed
        """
        token = self.access_token
        if not token:
            return False
        return token.needs_refresh

    def can_sync(self) -> tuple[bool, str | None]:
        """
        Business Rule: Connection can sync if active, enabled, and has valid token.

        Returns:
            Tuple of (can_sync, reason_if_not)
        """
        if not self.connection.is_active:
            return False, "Connection is inactive"

        if not self.connection.sync_enabled:
            return False, "Sync is disabled"

        if not self.is_token_valid():
            return False, "Token is expired or invalid"

        return True, None

    def should_retry_after_error(self) -> tuple[bool, str | None]:
        """
        Business Rule: Retry sync after error if error count < 5.

        Returns:
            Tuple of (should_retry, reason_if_not)
        """
        if self.connection.error_count >= 5:
            return False, "Too many consecutive errors (5+)"

        return True, None

    def get_recommended_sync_window(self) -> SyncWindow:
        """
        Business Rule: Sync window based on last sync time.

        Returns:
            Recommended SyncWindow
        """
        if not self.connection.last_sync_at:
            # First sync: last 30 days
            return SyncWindow.last_n_days(30)

        # Incremental sync: since last sync
        return SyncWindow.since(self.connection.last_sync_at)

    def is_sync_recent(self, hours: int = 1) -> bool:
        """
        Business Rule: Check if last sync was recent.

        Args:
            hours: Number of hours to consider "recent"

        Returns:
            True if last sync was within specified hours
        """
        if not self.connection.last_sync_at:
            return False

        threshold = datetime.utcnow() - timedelta(hours=hours)
        return self.connection.last_sync_at >= threshold

    def can_disconnect(self) -> tuple[bool, str | None]:
        """
        Business Rule: Connection can always be disconnected by user.

        Returns:
            Tuple of (can_disconnect, reason_if_not)
        """
        # Always allow disconnect, but could add business rules here
        # e.g., warn if there's an active challenge
        return True, None

    def increment_error_count(self) -> None:
        """
        Business Rule: Track consecutive errors.

        Increments error count. Auto-disables after 5 errors.
        """
        self.connection.error_count += 1

        if self.connection.error_count >= 5:
            self.connection.sync_enabled = False

    def reset_error_count(self) -> None:
        """
        Business Rule: Reset error count on successful sync.
        """
        self.connection.error_count = 0
        self.connection.last_error = None

    def mark_sync_success(self, synced_at: datetime | None = None) -> None:
        """
        Business Rule: Update connection after successful sync.

        Args:
            synced_at: Sync timestamp (defaults to now)
        """
        self.connection.last_sync_at = synced_at or datetime.utcnow()
        self.reset_error_count()

    def mark_sync_failure(self, error_message: str) -> None:
        """
        Business Rule: Update connection after failed sync.

        Args:
            error_message: Error description
        """
        self.connection.last_error = error_message
        self.increment_error_count()

    def supports_webhooks(self) -> bool:
        """
        Business Rule: Check if provider supports webhooks.

        Returns:
            True if provider supports webhook subscriptions
        """
        webhook_providers = {
            ProviderType.STRAVA,
            ProviderType.GARMIN,
        }
        return self.connection.provider in webhook_providers

    def has_webhook_subscription(self) -> bool:
        """
        Business Rule: Check if webhook is subscribed.

        Returns:
            True if webhook subscription exists
        """
        return bool(self.connection.webhook_subscription_id)
