"""
Fitbit OAuth Provider Implementation
Note: Fitbit now uses Google OAuth since migration to Google Health API
"""

import os
import json
from typing import Dict, Any, Type
from datetime import datetime, timezone

from app.models.fitbit_connection import FitbitConnection
from app.models.user import User
from ..base import OAuthProvider, OAuthConfig, OAuthTokens


class FitbitOAuthProvider(OAuthProvider):
    """Fitbit-specific OAuth implementation (via Google Health API)"""

    def __init__(self):
        config = OAuthConfig(
            client_id=os.getenv("FITBIT_CLIENT_ID"),
            client_secret=os.getenv("FITBIT_CLIENT_SECRET"),
            redirect_uri=os.getenv("FITBIT_REDIRECT_URI", "http://localhost:5173/auth/fitbit/callback"),
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes="https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.location.read https://www.googleapis.com/auth/userinfo.profile",
            provider_name="fitbit"
        )
        super().__init__(config)

    def get_provider_name(self) -> str:
        return "fitbit"

    def get_connection_model(self) -> Type[FitbitConnection]:
        return FitbitConnection

    def get_user_identifier(self, token_data: Dict[str, Any]) -> str:
        """Extract user ID from Google OAuth response (sub field)"""
        return token_data.get('sub', token_data.get('id', 'unknown'))

    def extract_user_data(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user profile data from Google OAuth"""
        return {
            'fitbit_user_id': self.get_user_identifier(token_data),
            'user_data': token_data  # Store full data
        }

    def get_additional_auth_params(self) -> Dict[str, str]:
        """Google OAuth specific parameters"""
        return {
            "access_type": "offline",
            "prompt": "consent"
        }

    def get_connection_query_filters(self, user_identifier: str) -> Dict[str, Any]:
        """Filter by fitbit_user_id"""
        return {"fitbit_user_id": user_identifier}

    def create_connection_instance(
        self,
        user: User,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ) -> FitbitConnection:
        """Create Fitbit connection with user data"""
        return FitbitConnection(
            user_id=user.id,
            fitbit_user_id=user_identifier,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=tokens.expires_at,
            scope=tokens.scope,
            user_data=json.dumps(user_data['user_data']),
            is_active=True
        )

    def update_connection_instance(
        self,
        connection: FitbitConnection,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ):
        """Update Fitbit connection with new data"""
        connection.access_token = tokens.access_token
        connection.refresh_token = tokens.refresh_token
        connection.expires_at = tokens.expires_at
        connection.scope = tokens.scope
        connection.fitbit_user_id = user_identifier
        connection.user_data = json.dumps(user_data['user_data'])
        connection.is_active = True
        connection.updated_at = datetime.now(timezone.utc)
