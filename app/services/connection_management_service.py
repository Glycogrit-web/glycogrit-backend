"""
Connection Management Service

Centralizes logic for managing fitness tracker connections across
all providers, reducing code duplication.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection
from app.models.fitbit_connection import FitbitConnection
from app.core.exceptions import NotFoundException
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ConnectionManagementService:
    """
    Service for managing fitness tracker connections.

    Provides a unified interface for connection CRUD operations
    across all fitness tracker providers.
    """

    # Map of provider names to their connection models
    PROVIDER_MODELS = {
        "strava": StravaConnection,
        "fitbit": FitbitConnection,
    }

    def __init__(self, db: Session):
        """
        Initialize connection management service

        Args:
            db: Database session
        """
        self.db = db

    def get_connection_model(self, provider: str):
        """
        Get the connection model class for a provider

        Args:
            provider: Provider name

        Returns:
            Model class or FitnessTrackerConnection for generic providers
        """
        return self.PROVIDER_MODELS.get(provider, FitnessTrackerConnection)

    def get_user_connection(
        self,
        user_id: int,
        provider: str,
        active_only: bool = True
    ) -> Optional[Any]:
        """
        Get a user's connection for a specific provider

        Args:
            user_id: User ID
            provider: Provider name
            active_only: Only return active connections

        Returns:
            Connection object or None
        """
        connection_model = self.get_connection_model(provider)

        query_filters = [connection_model.user_id == user_id]

        # For generic FitnessTrackerConnection, also filter by provider
        if connection_model == FitnessTrackerConnection:
            query_filters.append(connection_model.provider == provider)

        if active_only:
            query_filters.append(connection_model.is_active == True)

        return self.db.query(connection_model).filter(
            and_(*query_filters)
        ).first()

    def get_all_user_connections(
        self,
        user_id: int,
        active_only: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all connections for a user across all providers

        Args:
            user_id: User ID
            active_only: Only return active connections

        Returns:
            Dictionary mapping provider names to connection data
        """
        connections = {}

        # Check specific provider models
        for provider, model in self.PROVIDER_MODELS.items():
            try:
                query = self.db.query(model).filter(model.user_id == user_id)
                if active_only:
                    query = query.filter(model.is_active == True)

                connection = query.first()
                if connection:
                    connections[provider] = {
                        'id': connection.id,
                        'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                        'is_active': connection.is_active
                    }
            except Exception as e:
                # Table may not exist if migration hasn't run
                logger.warning(f"Failed to query {provider} connections: {str(e)}")

        # Check wahoo connections
        try:
            from app.models.wahoo_connection import WahooConnection
            query = self.db.query(WahooConnection).filter(WahooConnection.user_id == user_id)
            if active_only:
                query = query.filter(WahooConnection.is_active == True)

            connection = query.first()
            if connection:
                connections['wahoo'] = {
                    'id': connection.id,
                    'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                    'is_active': connection.is_active
                }
        except Exception as e:
            logger.warning(f"Failed to query Wahoo connections: {str(e)}")

        # Check garmin connections
        try:
            from app.models.garmin_connection import GarminConnection
            query = self.db.query(GarminConnection).filter(GarminConnection.user_id == user_id)
            if active_only:
                query = query.filter(GarminConnection.is_active == True)

            connection = query.first()
            if connection:
                connections['garmin'] = {
                    'id': connection.id,
                    'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                    'is_active': connection.is_active
                }
        except Exception as e:
            logger.warning(f"Failed to query Garmin connections: {str(e)}")

        # Check generic fitness tracker connections
        query = self.db.query(FitnessTrackerConnection).filter(
            FitnessTrackerConnection.user_id == user_id
        )
        if active_only:
            query = query.filter(FitnessTrackerConnection.is_active == True)

        for tracker in query.all():
            connections[tracker.provider] = {
                'id': tracker.id,
                'last_sync_at': tracker.last_sync_at.isoformat() if tracker.last_sync_at else None,
                'is_active': tracker.is_active
            }

        return connections

    def create_connection(
        self,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        user_info: Dict[str, Any],
        scope: Optional[str] = None
    ) -> Any:
        """
        Create or update a connection

        Args:
            user_id: User ID
            provider: Provider name
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration datetime
            user_info: User info from provider
            scope: OAuth scopes

        Returns:
            Created/updated connection object
        """
        connection_model = self.get_connection_model(provider)

        # Check for existing connection
        existing = self.get_user_connection(user_id, provider, active_only=False)

        provider_user_id = user_info.get("id") or user_info.get("athlete", {}).get("id", "")

        if existing:
            # Update existing connection
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_expires_at = expires_at
            existing.scope = scope
            existing.provider_data = json.dumps(user_info)
            existing.provider_user_id = provider_user_id
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated {provider} connection for user {user_id}")
            return existing
        else:
            # Create new connection
            connection_data = {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": expires_at,
                "scope": scope,
                "provider_data": json.dumps(user_info),
                "provider_user_id": provider_user_id,
                "is_active": True
            }

            # Add provider field for generic connection
            if connection_model == FitnessTrackerConnection:
                connection_data["provider"] = provider

            connection = connection_model(**connection_data)
            self.db.add(connection)
            self.db.commit()
            self.db.refresh(connection)
            logger.info(f"Created {provider} connection for user {user_id}")
            return connection

    def delete_connection(
        self,
        connection_id: int,
        user_id: int
    ) -> tuple[bool, str]:
        """
        Delete a connection by ID

        Args:
            connection_id: Connection ID
            user_id: User ID (for ownership verification)

        Returns:
            Tuple of (success, provider_name)

        Raises:
            HTTPException: If connection not found
        """
        # Try each provider model
        for provider, model in self.PROVIDER_MODELS.items():
            try:
                connection = self.db.query(model).filter(
                    model.id == connection_id,
                    model.user_id == user_id
                ).first()

                if connection:
                    self.db.delete(connection)
                    self.db.commit()
                    logger.info(f"Deleted {provider} connection {connection_id} for user {user_id}")
                    return True, provider
            except Exception as e:
                logger.warning(f"Error checking {provider} connection: {str(e)}")

        # Try Wahoo
        try:
            from app.models.wahoo_connection import WahooConnection
            connection = self.db.query(WahooConnection).filter(
                WahooConnection.id == connection_id,
                WahooConnection.user_id == user_id
            ).first()

            if connection:
                self.db.delete(connection)
                self.db.commit()
                logger.info(f"Deleted wahoo connection {connection_id} for user {user_id}")
                return True, "wahoo"
        except Exception as e:
            logger.warning(f"Error checking Wahoo connection: {str(e)}")

        # Try Garmin
        try:
            from app.models.garmin_connection import GarminConnection
            connection = self.db.query(GarminConnection).filter(
                GarminConnection.id == connection_id,
                GarminConnection.user_id == user_id
            ).first()

            if connection:
                self.db.delete(connection)
                self.db.commit()
                logger.info(f"Deleted garmin connection {connection_id} for user {user_id}")
                return True, "garmin"
        except Exception as e:
            logger.warning(f"Error checking Garmin connection: {str(e)}")

        # Try generic fitness tracker connection
        connection = self.db.query(FitnessTrackerConnection).filter(
            FitnessTrackerConnection.id == connection_id,
            FitnessTrackerConnection.user_id == user_id
        ).first()

        if connection:
            provider = connection.provider
            self.db.delete(connection)
            self.db.commit()
            logger.info(f"Deleted {provider} connection {connection_id} for user {user_id}")
            return True, provider

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    def check_duplicate_provider_connection(
        self,
        provider_user_id: str,
        provider: str,
        exclude_user_id: Optional[int] = None
    ) -> bool:
        """
        Check if a provider account is already connected to another user

        Args:
            provider_user_id: Provider's user ID
            provider: Provider name
            exclude_user_id: User ID to exclude from check (for current user)

        Returns:
            True if duplicate exists, False otherwise
        """
        connection_model = self.get_connection_model(provider)

        query_filters = [connection_model.provider_user_id == provider_user_id]

        if connection_model == FitnessTrackerConnection:
            query_filters.append(connection_model.provider == provider)

        if exclude_user_id:
            query_filters.append(connection_model.user_id != exclude_user_id)

        existing = self.db.query(connection_model).filter(and_(*query_filters)).first()
        return existing is not None

    def update_last_sync(
        self,
        user_id: int,
        provider: str,
        sync_time: Optional[datetime] = None
    ) -> None:
        """
        Update last sync time for a connection

        Args:
            user_id: User ID
            provider: Provider name
            sync_time: Sync datetime (defaults to now)
        """
        connection = self.get_user_connection(user_id, provider)
        if connection:
            connection.last_sync_at = sync_time or datetime.now(timezone.utc)
            self.db.commit()
            logger.debug(f"Updated last_sync_at for {provider} connection (user {user_id})")

    def deactivate_connection(
        self,
        user_id: int,
        provider: str
    ) -> bool:
        """
        Deactivate a connection without deleting it

        Args:
            user_id: User ID
            provider: Provider name

        Returns:
            True if connection was deactivated, False if not found
        """
        connection = self.get_user_connection(user_id, provider, active_only=False)
        if connection:
            connection.is_active = False
            self.db.commit()
            logger.info(f"Deactivated {provider} connection for user {user_id}")
            return True
        return False
