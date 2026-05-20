"""
Fitness Tracker Service

Main business logic service with CQRS handlers.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from app.modules.fitness_trackers.domain.connection import FitnessConnection
from app.modules.fitness_trackers.domain.entities import ConnectionEntity
from app.modules.fitness_trackers.domain.value_objects import ProviderType, SyncWindow, SyncStatus, ActivityCount
from app.modules.fitness_trackers.repositories.connection_repository import ConnectionRepository
from app.modules.fitness_trackers.services.provider_factory import ProviderFactory
from app.modules.fitness_trackers.services.commands import *
from app.modules.fitness_trackers.services.queries import *
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    PermissionDeniedException,
)

logger = logging.getLogger(__name__)


class FitnessTrackerService(BaseService):
    """Service for fitness tracker operations using CQRS pattern"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.repository = ConnectionRepository(db)

    # COMMAND HANDLERS (Write Operations)

    async def handle_connect_provider(
        self,
        command: ConnectProviderCommand
    ) -> FitnessConnection:
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
        existing = self.repository.get_by_user_and_provider(
            command.user_id,
            command.provider
        )
        if existing and existing.is_active:
            raise AlreadyExistsException(
                "Connection",
                "provider",
                command.provider.value
            )

        # Get provider instance
        try:
            provider = ProviderFactory.create(command.provider)
        except ValueError as e:
            raise ValidationException(str(e))

        # Exchange code for tokens
        try:
            token_data = await provider.exchange_code_for_tokens(
                command.authorization_code
            )
        except Exception as e:
            raise ValidationException(f"Failed to exchange authorization code: {str(e)}")

        # Check if athlete ID already connected to another user
        if self.repository.athlete_id_exists(
            command.provider,
            token_data["athlete_id"]
        ):
            raise AlreadyExistsException(
                "Connection",
                "athlete_id",
                token_data["athlete_id"]
            )

        # Create or update connection
        connection_data = {
            "user_id": command.user_id,
            "provider": command.provider,
            "athlete_id": token_data["athlete_id"],
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": token_data.get("expires_at"),
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
        self,
        command: DisconnectProviderCommand
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
        connection = self.repository.get_by_user_and_provider(
            command.user_id,
            command.provider
        )

        if not connection:
            raise NotFoundException("Connection", "provider", command.provider.value)

        # Deactivate connection
        return self.repository.deactivate_connection(
            command.user_id,
            command.provider
        )

    async def handle_refresh_token(
        self,
        command: RefreshTokenCommand
    ) -> FitnessConnection:
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
        connection = self.get_or_404(
            self.repository,
            command.connection_id,
            "Connection"
        )

        entity = ConnectionEntity(connection)

        if not entity.refresh_token:
            raise ValidationException("No refresh token available")

        # Get provider and refresh
        provider = ProviderFactory.create(connection.provider)

        try:
            token_data = await provider.refresh_access_token(
                entity.refresh_token.value
            )
        except Exception as e:
            raise ValidationException(f"Failed to refresh token: {str(e)}")

        # Update connection
        update_data = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", connection.refresh_token),
            "expires_at": token_data.get("expires_at"),
        }

        return self.repository.update(command.connection_id, update_data)

    async def handle_sync_activities(
        self,
        command: SyncActivitiesCommand
    ) -> SyncStatus:
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
        connection = self.get_or_404(
            self.repository,
            command.connection_id,
            "Connection"
        )

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
            activities = await provider.get_activities(
                connection.access_token,
                sync_window
            )

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
        connection = self.repository.get_by_user_and_provider(
            command.user_id,
            command.provider
        )

        if not connection:
            raise NotFoundException("Connection", "provider", command.provider.value)

        return self.repository.update(connection.id, {"sync_enabled": True})

    def handle_disable_sync(self, command: DisableSyncCommand) -> FitnessConnection:
        """Handle DisableSyncCommand"""
        connection = self.repository.get_by_user_and_provider(
            command.user_id,
            command.provider
        )

        if not connection:
            raise NotFoundException("Connection", "provider", command.provider.value)

        return self.repository.update(connection.id, {"sync_enabled": False})

    # QUERY HANDLERS (Read Operations)

    def handle_get_connection(self, query: GetConnectionQuery) -> FitnessConnection:
        """Handle GetConnectionQuery"""
        return self.get_or_404(
            self.repository,
            query.connection_id,
            "Connection"
        )

    def handle_get_user_connection(
        self,
        query: GetUserConnectionQuery
    ) -> Optional[FitnessConnection]:
        """Handle GetUserConnectionQuery"""
        return self.repository.get_by_user_and_provider(
            query.user_id,
            query.provider
        )

    def handle_get_user_connections(
        self,
        query: GetUserConnectionsQuery
    ) -> List[FitnessConnection]:
        """Handle GetUserConnectionsQuery"""
        return self.repository.get_user_connections(
            query.user_id,
            query.active_only
        )

    def handle_get_connection_status(
        self,
        query: GetConnectionStatusQuery
    ) -> Dict[str, Any]:
        """Handle GetConnectionStatusQuery"""
        connection = self.repository.get_by_user_and_provider(
            query.user_id,
            query.provider
        )

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
        self,
        query: GetAvailableProvidersQuery
    ) -> List[Dict[str, str]]:
        """Handle GetAvailableProvidersQuery"""
        providers = ProviderFactory.get_available_providers()

        return [
            {
                "provider": provider.value,
                "name": provider.value.replace("_", " ").title(),
            }
            for provider in providers
        ]

    def handle_get_authorization_url(
        self,
        query: GetAuthorizationUrlQuery
    ) -> str:
        """Handle GetAuthorizationUrlQuery"""
        try:
            provider = ProviderFactory.create(query.provider)
            return provider.get_full_authorization_url(query.state)
        except ValueError as e:
            raise ValidationException(str(e))
