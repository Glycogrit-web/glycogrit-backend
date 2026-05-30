"""
Fitness Tracker Service

Main business logic service with CQRS handlers.
"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    ValidationException,
)
from app.modules.fitness_trackers.domain.connection import FitnessConnection
from app.modules.fitness_trackers.domain.entities import ConnectionEntity
from app.modules.fitness_trackers.domain.value_objects import (
    ActivityCount,
    SyncStatus,
)
from app.modules.fitness_trackers.repositories.connection_repository import ConnectionRepository
from app.modules.fitness_trackers.services.commands import *
from app.modules.fitness_trackers.services.provider_factory import ProviderFactory
from app.modules.fitness_trackers.services.queries import *
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class FitnessTrackerService(BaseService):
    """Service for fitness tracker operations using CQRS pattern"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.repository = ConnectionRepository(db)

    # COMMAND HANDLERS (Write Operations)

    async def handle_connect_provider(self, command: ConnectProviderCommand) -> FitnessConnection:
        """
        Handle ConnectProviderCommand.

        Business Rules:
        1. One connection per user per provider
        2. Provider must be configured
        3. Authorization code must be valid

        Args:
            command: ConnectProviderCommand

        Returns:
            Created FitnessConnection

        Raises:
            AlreadyExistsException: If connection already exists
            ValidationException: If provider not configured or auth fails
        """
        # Check if connection already exists
        existing = self.repository.get_by_user_and_provider(command.user_id, command.provider)
        if existing and existing.is_active:
            raise AlreadyExistsException("Connection", "provider", command.provider.value)

        # Get provider instance
        try:
            provider = ProviderFactory.create(command.provider)
        except ValueError as e:
            raise ValidationException(str(e))

        # Exchange code for tokens
        try:
            token_data = await provider.exchange_code_for_tokens(command.authorization_code)
        except Exception as e:
            raise ValidationException(f"Failed to exchange authorization code: {str(e)}")

        # Check if athlete ID already connected to another user
        if self.repository.athlete_id_exists(command.provider, token_data["athlete_id"]):
            raise AlreadyExistsException("Connection", "athlete_id", token_data["athlete_id"])

        # Create or update connection
        connection_data = {
            "user_id": command.user_id,
            "provider": command.provider.value,  # Use .value to store lowercase string
            "athlete_id": token_data["athlete_id"],
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": token_data.get("expires_at"),
            "scope": token_data.get("scope"),
            "athlete_data": json.dumps(token_data.get("athlete_data", {})),
            "is_active": True,
            "sync_enabled": True,
        }

        if existing:
            # Reactivate existing connection
            for key, value in connection_data.items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            return self.repository.create(connection_data)

    async def handle_disconnect_provider(
        self, command: DisconnectProviderCommand
    ) -> FitnessConnection:
        """
        Handle DisconnectProviderCommand.

        Business Rules:
        1. Only owner can disconnect
        2. Connection can always be disconnected

        Args:
            command: DisconnectProviderCommand

        Returns:
            Deactivated FitnessConnection

        Raises:
            NotFoundException: If connection not found
        """
        connection = self.repository.get_by_user_and_provider(command.user_id, command.provider)

        if not connection:
            raise NotFoundException("Connection", command.provider.value)

        # Deactivate connection
        return self.repository.deactivate_connection(command.user_id, command.provider)

    async def handle_refresh_token(self, command: RefreshTokenCommand) -> FitnessConnection:
        """
        Handle RefreshTokenCommand.

        Business Rules:
        1. Token must exist and be refreshable
        2. Provider must support token refresh

        Args:
            command: RefreshTokenCommand

        Returns:
            Updated FitnessConnection

        Raises:
            NotFoundException: If connection not found
            ValidationException: If refresh fails
        """
        connection = self.get_or_404(self.repository, command.connection_id, "Connection")

        entity = ConnectionEntity(connection)

        if not entity.refresh_token:
            raise ValidationException("No refresh token available")

        # Get provider and refresh
        provider = ProviderFactory.create(connection.provider)

        try:
            token_data = await provider.refresh_access_token(entity.refresh_token.value)
        except Exception as e:
            raise ValidationException(f"Failed to refresh token: {str(e)}")

        # Update connection
        update_data = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", connection.refresh_token),
            "expires_at": token_data.get("expires_at"),
        }

        return self.repository.update(command.connection_id, update_data)

    async def handle_sync_activities(self, command: SyncActivitiesCommand) -> SyncStatus:
        """
        Handle SyncActivitiesCommand.

        Business Rules:
        1. Connection must be active and have valid token
        2. Skip if recently synced (unless force=True)
        3. Sync activities and update progress

        Args:
            command: SyncActivitiesCommand

        Returns:
            SyncStatus

        Raises:
            NotFoundException: If connection not found
            ValidationException: If connection cannot sync
        """
        connection = self.get_or_404(self.repository, command.connection_id, "Connection")

        entity = ConnectionEntity(connection)

        # Check if can sync
        can_sync, reason = entity.can_sync()
        if not can_sync:
            raise ValidationException(reason)

        # Check if recently synced
        if not command.force and entity.is_sync_recent(hours=1):
            return SyncStatus.success(ActivityCount.zero())

        # Refresh token if needed
        if entity.needs_token_refresh():
            await self.handle_refresh_token(RefreshTokenCommand(connection.id))
            self.db.refresh(connection)

        # Get provider and sync
        provider = ProviderFactory.create(connection.provider)
        sync_window = entity.get_recommended_sync_window()

        try:
            activities = await provider.get_activities(connection.access_token, sync_window)

            # TODO: Process activities and update progress
            # This would integrate with the Activities module
            activity_count = ActivityCount(len(activities))

            # Mark sync success
            entity.mark_sync_success()
            self.db.commit()

            return SyncStatus.success(activity_count)

        except Exception as e:
            logger.error(f"Sync failed for connection {connection.id}: {str(e)}")
            entity.mark_sync_failure(str(e))
            self.db.commit()

            return SyncStatus.failure(str(e))

    def handle_enable_sync(self, command: EnableSyncCommand) -> FitnessConnection:
        """Handle EnableSyncCommand"""
        connection = self.repository.get_by_user_and_provider(command.user_id, command.provider)

        if not connection:
            raise NotFoundException("Connection", command.provider.value)

        return self.repository.update(connection.id, {"sync_enabled": True})

    def handle_disable_sync(self, command: DisableSyncCommand) -> FitnessConnection:
        """Handle DisableSyncCommand"""
        connection = self.repository.get_by_user_and_provider(command.user_id, command.provider)

        if not connection:
            raise NotFoundException("Connection", command.provider.value)

        return self.repository.update(connection.id, {"sync_enabled": False})

    # QUERY HANDLERS (Read Operations)

    def handle_get_connection(self, query: GetConnectionQuery) -> FitnessConnection:
        """Handle GetConnectionQuery"""
        return self.get_or_404(self.repository, query.connection_id, "Connection")

    def handle_get_user_connection(self, query: GetUserConnectionQuery) -> FitnessConnection | None:
        """Handle GetUserConnectionQuery"""
        return self.repository.get_by_user_and_provider(query.user_id, query.provider)

    def handle_get_user_connections(
        self, query: GetUserConnectionsQuery
    ) -> list[FitnessConnection]:
        """Handle GetUserConnectionsQuery"""
        return self.repository.get_user_connections(query.user_id, query.active_only)

    def handle_get_connection_status(self, query: GetConnectionStatusQuery) -> dict[str, Any]:
        """Handle GetConnectionStatusQuery"""
        connection = self.repository.get_by_user_and_provider(query.user_id, query.provider)

        if not connection:
            return {
                "connected": False,
                "provider": query.provider.value,
            }

        entity = ConnectionEntity(connection)

        return {
            "connected": True,
            "provider": query.provider.value,
            "is_active": connection.is_active,
            "sync_enabled": connection.sync_enabled,
            "token_valid": entity.is_token_valid(),
            "last_sync_at": connection.last_sync_at,
            "error_count": connection.error_count,
            "last_error": connection.last_error,
        }

    def handle_get_available_providers(
        self, query: GetAvailableProvidersQuery
    ) -> list[dict[str, str]]:
        """Handle GetAvailableProvidersQuery"""
        providers = ProviderFactory.get_available_providers()

        return [
            {
                "provider": provider.value,
                "name": provider.value.replace("_", " ").title(),
            }
            for provider in providers
        ]

    def handle_get_authorization_url(self, query: GetAuthorizationUrlQuery) -> str:
        """Handle GetAuthorizationUrlQuery"""
        try:
            provider = ProviderFactory.create(query.provider)
            return provider.get_full_authorization_url(query.state)
        except ValueError as e:
            raise ValidationException(str(e))

    def handle_get_strava_progress(self, query):
        """
        Handle GetStravaProgressQuery.

        Returns the user's progress for the specified event.
        This doesn't require an active Strava connection - it returns
        the actual progress data regardless of sync source.

        Args:
            query: GetStravaProgressQuery

        Returns:
            ActivityProgress instance or None if not found
        """
        from app.modules.activities.repositories.progress_repository import ProgressRepository

        progress_repo = ProgressRepository(self.db)
        return progress_repo.get_user_progress(query.user_id, query.event_id)

    def get_all_providers_with_connection_status(self, user_id: int) -> list[dict]:
        """
        Get all available fitness providers with user's connection status.

        Returns list of all providers (OAuth + manual upload) with:
        - Provider metadata (display_name, supports_oauth, etc.)
        - Connection status (connected, last_sync_at, etc.)
        - Primary source flag

        Args:
            user_id: User ID

        Returns:
            List of provider dictionaries with connection status
        """
        from app.core.oauth_provider_manager import OAuthProviderManager

        # 1. Get all supported OAuth providers
        provider_manager = OAuthProviderManager()
        all_providers = provider_manager.list_providers()

        # Filter to only production-ready providers (exclude wahoo, garmin for now)
        SUPPORTED_PROVIDERS = ["google_fit", "strava", "fitbit"]
        available_providers = [p for p in all_providers if p in SUPPORTED_PROVIDERS]

        # 2. Get user's actual connections from database
        user_connections = self.repository.get_user_connections(user_id, active_only=True)

        # Create map: provider_name -> connection object
        connections_map = {conn.provider: conn for conn in user_connections}

        # 3. Get primary source
        # NOTE: Primary source tracking not yet implemented in database
        # TODO: Implement primary source tracking - requires database migration
        # For now, set all providers as non-primary
        primary_provider = None

        # 4. Build response list
        result = []

        # Add OAuth providers
        for provider_name in available_providers:
            connection = connections_map.get(provider_name)

            result.append(
                {
                    "provider": provider_name,
                    "display_name": self._get_display_name(provider_name),
                    "connected": connection is not None,
                    "connection_id": connection.id if connection else None,
                    "last_sync_at": connection.last_sync_at if connection else None,
                    "last_sync_status": self._get_sync_status(connection) if connection else None,
                    "requires_file_upload": False,  # OAuth providers
                    "supports_oauth": True,
                    "is_primary": provider_name == primary_provider,  # Always False for now
                    "same_account_as_login": self._check_same_account(
                        provider_name, user_id
                    ),
                    "error_count": connection.error_count if connection else 0,
                    "last_error": connection.last_error if connection else None,
                    "athlete_name": self._get_athlete_name(connection) if connection else None,
                }
            )

        # 5. Add manual upload provider
        result.append(
            {
                "provider": "manual_upload",
                "display_name": "Manual Upload",
                "connected": True,  # Always available
                "connection_id": None,
                "last_sync_at": None,
                "last_sync_status": None,
                "requires_file_upload": True,
                "supports_oauth": False,
                "is_primary": False,  # Manual upload cannot be primary
                "same_account_as_login": False,
                "error_count": 0,
                "last_error": None,
                "athlete_name": None,
            }
        )

        return result

    def _get_display_name(self, provider: str) -> str:
        """Map provider slug to display name"""
        display_names = {
            "strava": "Strava",
            "google_fit": "Google Fit",
            "fitbit": "Fitbit",
            "garmin": "Garmin",
            "wahoo": "Wahoo",
        }
        return display_names.get(provider, provider.replace("_", " ").title())

    def _get_sync_status(self, connection) -> str | None:
        """Determine sync status from connection"""
        if connection.last_error:
            return "error"
        if connection.last_sync_at:
            return "success"
        return None

    def _check_same_account(self, provider: str, user_id: int) -> bool:
        """Check if Google Fit uses same account as login"""
        # TODO: Implement logic to check if Google Fit connection uses same Google account
        return False

    def _get_athlete_name(self, connection) -> str | None:
        """Extract athlete name from connection athlete_data JSON"""
        if not connection or not connection.athlete_data:
            return None

        try:
            athlete_data = json.loads(connection.athlete_data)
            # Different providers store name differently
            return (
                athlete_data.get("name")
                or athlete_data.get("athlete_name")
                or f"{athlete_data.get('firstname', '')} {athlete_data.get('lastname', '')}".strip()
                or None
            )
        except (json.JSONDecodeError, AttributeError, KeyError):
            return None
