"""
Garmin OAuth Provider Implementation
Note: Garmin uses OAuth 1.0a, which is different from OAuth 2.0
This is a simplified adapter that fits into our framework
"""

import os
import json
from typing import Dict, Any, Type, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.garmin_connection import GarminConnection
from app.models.user import User
from ..base import OAuthConfig
from ..exceptions import ProviderConfigException, ConnectionAlreadyExistsException


class GarminOAuthProvider:
    """
    Garmin OAuth 1.0a adapter
    Since Garmin uses OAuth 1.0a (not 2.0), it doesn't fully fit the base OAuthProvider pattern
    This is a simplified adapter that provides similar interface
    """

    def __init__(self):
        self.client_id = os.getenv("GARMIN_CLIENT_ID")
        self.client_secret = os.getenv("GARMIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GARMIN_REDIRECT_URI", "http://localhost:5173/auth/garmin/callback")
        self.provider_name = "garmin"

        if not self.client_id or not self.client_secret:
            raise ProviderConfigException(
                "Garmin integration not configured. Missing client credentials.",
                provider=self.provider_name
            )

    def get_provider_name(self) -> str:
        return "garmin"

    def get_connection_model(self) -> Type[GarminConnection]:
        return GarminConnection

    def get_connection(self, user: User, db: Session) -> Optional[GarminConnection]:
        """Get user's Garmin connection"""
        return db.query(GarminConnection).filter_by(user_id=user.id).first()

    def get_active_connection(self, user: User, db: Session) -> Optional[GarminConnection]:
        """Get user's active Garmin connection"""
        return db.query(GarminConnection).filter_by(
            user_id=user.id,
            is_active=True
        ).first()

    def disconnect(self, user: User, db: Session) -> bool:
        """Disconnect Garmin from user account"""
        connection = self.get_connection(user, db)

        if not connection:
            return False

        # Clear primary sync source if this was it
        if user.primary_sync_source == "garmin":
            user.primary_sync_source = None

        db.delete(connection)
        db.commit()
        return True

    def create_connection(
        self,
        user: User,
        db: Session,
        user_id_garmin: str,
        access_token: str,
        access_token_secret: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> GarminConnection:
        """
        Create or update Garmin connection
        Since OAuth 1.0a flow is different, this is called directly from the API endpoint
        """
        # Check if this Garmin user is already connected to another account
        existing_garmin_connection = db.query(GarminConnection).filter_by(
            user_id_garmin=user_id_garmin
        ).first()

        if existing_garmin_connection and existing_garmin_connection.user_id != user.id:
            raise ConnectionAlreadyExistsException(
                "This Garmin account is already connected to another user",
                provider=self.provider_name
            )

        # Check if user already has a connection
        existing_user_connection = db.query(GarminConnection).filter_by(
            user_id=user.id
        ).first()

        if existing_user_connection:
            # Update existing
            existing_user_connection.user_id_garmin = user_id_garmin
            existing_user_connection.access_token = access_token
            existing_user_connection.access_token_secret = access_token_secret
            existing_user_connection.user_data = user_data
            existing_user_connection.is_active = True
            existing_user_connection.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_user_connection)
            connection = existing_user_connection
        else:
            # Create new
            connection = GarminConnection(
                user_id=user.id,
                user_id_garmin=user_id_garmin,
                access_token=access_token,
                access_token_secret=access_token_secret,
                user_data=user_data,
                is_active=True
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)

        # Auto-set as primary if user has none
        if not user.primary_sync_source:
            user.primary_sync_source = "garmin"
            db.commit()

        return connection
