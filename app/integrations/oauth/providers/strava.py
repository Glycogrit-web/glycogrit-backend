"""
Strava OAuth Provider Implementation
"""

import os
import json
from typing import Dict, Any, Type
from datetime import datetime, timezone

from app.models.strava_connection import StravaConnection
from app.models.user import User
from ..base import OAuthProvider, OAuthConfig, OAuthTokens


class StravaOAuthProvider(OAuthProvider):
    """Strava-specific OAuth implementation"""

    def __init__(self):
        config = OAuthConfig(
            client_id=os.getenv("STRAVA_CLIENT_ID"),
            client_secret=os.getenv("STRAVA_CLIENT_SECRET"),
            redirect_uri=os.getenv("STRAVA_REDIRECT_URI", "http://localhost:5173/auth/strava/callback"),
            authorization_url="https://www.strava.com/oauth/authorize",
            token_url="https://www.strava.com/oauth/token",
            scopes="activity:read_all,profile:read_all",
            provider_name="strava"
        )
        super().__init__(config)

    def get_provider_name(self) -> str:
        return "strava"

    def get_connection_model(self) -> Type[StravaConnection]:
        return StravaConnection

    def get_user_identifier(self, token_data: Dict[str, Any]) -> str:
        """Extract athlete ID from Strava token response"""
        return str(token_data['athlete']['id'])

    def extract_user_data(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract athlete profile data"""
        athlete = token_data.get('athlete', {})
        return {
            'athlete_id': athlete.get('id'),
            'first_name': athlete.get('firstname', ''),
            'last_name': athlete.get('lastname', ''),
            'profile_url': athlete.get('profile', ''),
            'city': athlete.get('city', ''),
            'state': athlete.get('state', ''),
            'country': athlete.get('country', ''),
            'athlete_data': athlete  # Store full data
        }

    def get_additional_auth_params(self) -> Dict[str, str]:
        """Strava-specific authorization parameters"""
        return {
            "approval_prompt": "auto"
        }

    def get_connection_query_filters(self, user_identifier: str) -> Dict[str, Any]:
        """Filter by athlete_id"""
        return {"athlete_id": int(user_identifier)}

    def create_connection_instance(
        self,
        user: User,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ) -> StravaConnection:
        """Create Strava connection with athlete data"""
        return StravaConnection(
            user_id=user.id,
            athlete_id=int(user_identifier),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=tokens.expires_at,
            scope=tokens.scope,
            athlete_data=json.dumps(user_data['athlete_data']),
            is_active=True
        )

    def update_connection_instance(
        self,
        connection: StravaConnection,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ):
        """Update Strava connection with new data"""
        connection.access_token = tokens.access_token
        connection.refresh_token = tokens.refresh_token
        connection.expires_at = tokens.expires_at
        connection.scope = tokens.scope
        connection.athlete_id = int(user_identifier)
        connection.athlete_data = json.dumps(user_data['athlete_data'])
        connection.is_active = True
        connection.updated_at = datetime.now(timezone.utc)
