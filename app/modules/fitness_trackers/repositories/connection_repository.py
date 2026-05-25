"""
Fitness Connection Repository

Data access layer for fitness tracker connections.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.modules.fitness_trackers.domain.connection import FitnessConnection, ProviderType
from app.services.base import BaseRepository


class ConnectionRepository(BaseRepository[FitnessConnection]):
    """Repository for fitness tracker connections"""

    def __init__(self, db: Session):
        super().__init__(FitnessConnection, db)

    def get_by_user_and_provider(
        self,
        user_id: int,
        provider: ProviderType
    ) -> Optional[FitnessConnection]:
        """
        Get connection by user ID and provider.

        Args:
            user_id: User ID
            provider: Provider type

        Returns:
            FitnessConnection or None
        """
        return self.db.query(FitnessConnection).filter(
            and_(
                FitnessConnection.user_id == user_id,
                FitnessConnection.provider == provider
            )
        ).first()

    def get_by_athlete_id(
        self,
        provider: ProviderType,
        athlete_id: str
    ) -> Optional[FitnessConnection]:
        """
        Get connection by provider and athlete ID.

        Args:
            provider: Provider type
            athlete_id: Provider-specific athlete ID

        Returns:
            FitnessConnection or None
        """
        return self.db.query(FitnessConnection).filter(
            and_(
                FitnessConnection.provider == provider,
                FitnessConnection.athlete_id == athlete_id
            )
        ).first()

    def get_user_connections(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[FitnessConnection]:
        """
        Get all connections for a user.

        Args:
            user_id: User ID
            active_only: Only return active connections

        Returns:
            List of FitnessConnection
        """
        query = self.db.query(FitnessConnection).filter(
            FitnessConnection.user_id == user_id
        )

        if active_only:
            query = query.filter(FitnessConnection.is_active == True)

        return query.order_by(FitnessConnection.created_at.desc()).all()

    def get_connections_needing_sync(
        self,
        provider: Optional[ProviderType] = None,
        limit: int = 100
    ) -> List[FitnessConnection]:
        """
        Get connections that need syncing.

        Criteria:
        - Active
        - Sync enabled
        - No recent sync (last_sync_at is NULL or > 1 hour ago)
        - Error count < 5

        Args:
            provider: Filter by provider (optional)
            limit: Maximum number of connections

        Returns:
            List of FitnessConnection
        """
        from datetime import datetime, timedelta

        hour_ago = datetime.utcnow() - timedelta(hours=1)

        query = self.db.query(FitnessConnection).filter(
            and_(
                FitnessConnection.is_active == True,
                FitnessConnection.sync_enabled == True,
                FitnessConnection.error_count < 5,
                or_(
                    FitnessConnection.last_sync_at == None,
                    FitnessConnection.last_sync_at < hour_ago
                )
            )
        )

        if provider:
            query = query.filter(FitnessConnection.provider == provider)

        return query.limit(limit).all()

    def get_connections_with_errors(
        self,
        provider: Optional[ProviderType] = None
    ) -> List[FitnessConnection]:
        """
        Get connections with sync errors.

        Args:
            provider: Filter by provider (optional)

        Returns:
            List of FitnessConnection with errors
        """
        query = self.db.query(FitnessConnection).filter(
            FitnessConnection.error_count > 0
        )

        if provider:
            query = query.filter(FitnessConnection.provider == provider)

        return query.order_by(FitnessConnection.error_count.desc()).all()

    def get_connections_with_webhooks(
        self,
        provider: Optional[ProviderType] = None
    ) -> List[FitnessConnection]:
        """
        Get connections with webhook subscriptions.

        Args:
            provider: Filter by provider (optional)

        Returns:
            List of FitnessConnection with webhooks
        """
        query = self.db.query(FitnessConnection).filter(
            FitnessConnection.webhook_subscription_id != None
        )

        if provider:
            query = query.filter(FitnessConnection.provider == provider)

        return query.all()

    def connection_exists(
        self,
        user_id: int,
        provider: ProviderType
    ) -> bool:
        """
        Check if connection exists for user and provider.

        Args:
            user_id: User ID
            provider: Provider type

        Returns:
            True if connection exists
        """
        return self.db.query(FitnessConnection).filter(
            and_(
                FitnessConnection.user_id == user_id,
                FitnessConnection.provider == provider
            )
        ).count() > 0

    def athlete_id_exists(
        self,
        provider: ProviderType,
        athlete_id: str
    ) -> bool:
        """
        Check if athlete ID exists for provider.

        Args:
            provider: Provider type
            athlete_id: Provider-specific athlete ID

        Returns:
            True if athlete ID exists
        """
        return self.db.query(FitnessConnection).filter(
            and_(
                FitnessConnection.provider == provider,
                FitnessConnection.athlete_id == athlete_id
            )
        ).count() > 0

    def deactivate_connection(
        self,
        user_id: int,
        provider: ProviderType
    ) -> Optional[FitnessConnection]:
        """
        Deactivate a connection (soft delete).

        Args:
            user_id: User ID
            provider: Provider type

        Returns:
            Updated FitnessConnection or None
        """
        connection = self.get_by_user_and_provider(user_id, provider)
        if connection:
            connection.is_active = False
            connection.sync_enabled = False
            self.db.commit()
            self.db.refresh(connection)
        return connection
