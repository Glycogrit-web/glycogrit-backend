"""
Base OAuth Provider Implementation
Template Method Pattern for unified OAuth flow across all fitness trackers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Type, TypeVar
from sqlalchemy.orm import Session
import httpx
import json
import logging

from app.models.user import User
from .exceptions import (
    ProviderConfigException,
    TokenRefreshException,
    ConnectionAlreadyExistsException,
    TokenExchangeException,
    OAuthException
)

logger = logging.getLogger(__name__)

# Generic type for connection models
ConnectionModel = TypeVar('ConnectionModel')


@dataclass
class OAuthConfig:
    """OAuth provider configuration"""
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_url: str
    token_url: str
    scopes: str
    provider_name: str

    def validate(self):
        """Validate configuration"""
        if not self.client_id or not self.client_secret:
            raise ProviderConfigException(
                f"{self.provider_name} integration not configured. Missing client credentials.",
                provider=self.provider_name
            )


@dataclass
class OAuthTokens:
    """OAuth tokens data"""
    access_token: str
    refresh_token: str
    expires_in: int
    scope: Optional[str] = None

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration datetime"""
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)


@dataclass
class OAuthCallbackResult:
    """Result of OAuth callback processing"""
    connection: Any  # The connection model instance
    user_data: Dict[str, Any]
    is_new_connection: bool


class OAuthProvider(ABC):
    """
    Abstract base class for OAuth providers
    Implements Template Method pattern for OAuth flow

    Usage:
        class StravaOAuthProvider(OAuthProvider):
            def get_provider_name(self) -> str:
                return "strava"

            def get_user_identifier(self, token_data: Dict) -> str:
                return str(token_data['athlete']['id'])

            # ... implement other abstract methods
    """

    def __init__(self, config: OAuthConfig):
        self.config = config
        self.config.validate()

    # ==================== Template Methods (Override as needed) ====================

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'strava', 'garmin')"""
        pass

    @abstractmethod
    def get_connection_model(self) -> Type[ConnectionModel]:
        """Return the SQLAlchemy model class for this provider's connections"""
        pass

    @abstractmethod
    def get_user_identifier(self, token_data: Dict[str, Any]) -> str:
        """Extract unique user identifier from token response"""
        pass

    @abstractmethod
    def extract_user_data(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format user profile data from token response
        Should return a dict with keys like 'name', 'email', etc.
        """
        pass

    def get_additional_auth_params(self) -> Dict[str, str]:
        """
        Additional parameters for authorization URL
        Override to add provider-specific params
        """
        return {}

    def get_token_refresh_data(self, refresh_token: str) -> Dict[str, str]:
        """
        Build token refresh request data
        Override for provider-specific refresh flow
        """
        return {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

    def get_token_exchange_data(self, code: str) -> Dict[str, str]:
        """
        Build authorization code exchange request data
        Override for provider-specific exchange flow
        """
        return {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri
        }

    def get_token_headers(self) -> Dict[str, str]:
        """
        Headers for token requests
        Override for provider-specific headers
        """
        return {"Content-Type": "application/x-www-form-urlencoded"}

    def create_connection_instance(
        self,
        user: User,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ) -> ConnectionModel:
        """
        Create new connection model instance
        Override for provider-specific connection creation
        """
        model_class = self.get_connection_model()
        return model_class(
            user_id=user.id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=tokens.expires_at,
            scope=tokens.scope,
            is_active=True
        )

    def update_connection_instance(
        self,
        connection: ConnectionModel,
        tokens: OAuthTokens,
        user_identifier: str,
        user_data: Dict[str, Any]
    ):
        """
        Update existing connection with new token data
        Override for provider-specific updates
        """
        connection.access_token = tokens.access_token
        connection.refresh_token = tokens.refresh_token
        connection.expires_at = tokens.expires_at
        connection.scope = tokens.scope
        connection.is_active = True
        connection.updated_at = datetime.now(timezone.utc)

    def get_connection_query_filters(self, user_identifier: str) -> Dict[str, Any]:
        """
        Return filters to find existing connection by user identifier
        Override for provider-specific identifier field
        """
        return {}  # Must be overridden by subclass

    # ==================== Public API (Concrete Methods) ====================

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Full authorization URL
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scopes,
        }

        if state:
            params["state"] = state

        # Add provider-specific params
        params.update(self.get_additional_auth_params())

        # Build URL
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.authorization_url}?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> OAuthTokens:
        """
        Exchange authorization code for access tokens

        Args:
            code: Authorization code from OAuth callback

        Returns:
            OAuthTokens instance

        Raises:
            TokenExchangeException: If exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    headers=self.get_token_headers(),
                    data=self.get_token_exchange_data(code)
                )

            if response.status_code != 200:
                raise TokenExchangeException(
                    f"Failed to exchange code: {response.text}",
                    provider=self.get_provider_name()
                )

            token_data = response.json()

            return OAuthTokens(
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', token_data.get('refresh_token')),
                expires_in=token_data.get('expires_in', 3600),
                scope=token_data.get('scope')
            )

        except httpx.HTTPError as e:
            raise TokenExchangeException(
                f"HTTP error during token exchange: {str(e)}",
                provider=self.get_provider_name()
            )

    async def refresh_access_token(self, connection: ConnectionModel, db: Session) -> str:
        """
        Refresh expired access token

        Args:
            connection: Connection model instance
            db: Database session

        Returns:
            New access token

        Raises:
            TokenRefreshException: If refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    headers=self.get_token_headers(),
                    data=self.get_token_refresh_data(connection.refresh_token)
                )

            if response.status_code != 200:
                logger.error(
                    f"{self.get_provider_name()} token refresh failed: {response.text}"
                )
                raise TokenRefreshException(
                    f"Failed to refresh token: {response.text}",
                    provider=self.get_provider_name()
                )

            token_data = response.json()

            # Update connection
            connection.access_token = token_data['access_token']
            connection.refresh_token = token_data.get('refresh_token', connection.refresh_token)
            connection.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            connection.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(connection)

            logger.info(f"{self.get_provider_name()} token refreshed for connection {connection.id}")

            return connection.access_token

        except httpx.HTTPError as e:
            raise TokenRefreshException(
                f"HTTP error during token refresh: {str(e)}",
                provider=self.get_provider_name()
            )

    async def ensure_valid_token(self, connection: ConnectionModel, db: Session) -> str:
        """
        Ensure connection has valid access token, refresh if needed

        Args:
            connection: Connection model instance
            db: Database session

        Returns:
            Valid access token
        """
        if datetime.now(timezone.utc) >= connection.expires_at:
            logger.info(f"Token expired for {self.get_provider_name()} connection {connection.id}, refreshing...")
            return await self.refresh_access_token(connection, db)

        return connection.access_token

    async def handle_callback(
        self,
        code: str,
        user: User,
        db: Session
    ) -> OAuthCallbackResult:
        """
        Complete OAuth flow: exchange code and create/update connection
        This is the main template method that orchestrates the OAuth flow

        Args:
            code: Authorization code from callback
            user: Current user
            db: Database session

        Returns:
            OAuthCallbackResult with connection and user data

        Raises:
            ConnectionAlreadyExistsException: If provider account is linked to another user
        """
        # Step 1: Exchange code for tokens
        token_data_dict = await self._exchange_code_with_full_response(code)
        tokens = OAuthTokens(
            access_token=token_data_dict['access_token'],
            refresh_token=token_data_dict.get('refresh_token'),
            expires_in=token_data_dict.get('expires_in', 3600),
            scope=token_data_dict.get('scope')
        )

        # Step 2: Extract user identifier and data
        user_identifier = self.get_user_identifier(token_data_dict)
        user_data = self.extract_user_data(token_data_dict)

        # Step 3: Check if this provider account is already connected to another user
        model_class = self.get_connection_model()
        filters = self.get_connection_query_filters(user_identifier)
        existing_provider_connection = db.query(model_class).filter_by(**filters).first()

        if existing_provider_connection and existing_provider_connection.user_id != user.id:
            raise ConnectionAlreadyExistsException(
                f"This {self.get_provider_name()} account is already connected to another user",
                provider=self.get_provider_name()
            )

        # Step 4: Check if user already has a connection
        existing_user_connection = db.query(model_class).filter_by(user_id=user.id).first()

        is_new_connection = False

        if existing_user_connection:
            # Update existing connection
            self.update_connection_instance(
                existing_user_connection,
                tokens,
                user_identifier,
                user_data
            )
            db.commit()
            db.refresh(existing_user_connection)
            connection = existing_user_connection
            logger.info(f"Updated {self.get_provider_name()} connection for user {user.id}")
        else:
            # Create new connection
            connection = self.create_connection_instance(user, tokens, user_identifier, user_data)
            db.add(connection)
            db.commit()
            db.refresh(connection)
            is_new_connection = True
            logger.info(f"Created new {self.get_provider_name()} connection for user {user.id}")

        # Step 5: Auto-set as primary sync source if user has none
        if not user.primary_sync_source:
            user.primary_sync_source = self.get_provider_name()
            db.commit()
            logger.info(f"Auto-set {self.get_provider_name()} as primary sync source for user {user.id}")

        return OAuthCallbackResult(
            connection=connection,
            user_data=user_data,
            is_new_connection=is_new_connection
        )

    def disconnect(self, user: User, db: Session) -> bool:
        """
        Disconnect provider from user account

        Args:
            user: User to disconnect
            db: Database session

        Returns:
            True if disconnected, False if no connection existed
        """
        model_class = self.get_connection_model()
        connection = db.query(model_class).filter_by(user_id=user.id).first()

        if not connection:
            return False

        # Clear primary sync source if this was it
        if user.primary_sync_source == self.get_provider_name():
            user.primary_sync_source = None
            logger.info(f"Cleared primary sync source for user {user.id}")

        db.delete(connection)
        db.commit()

        logger.info(f"Disconnected {self.get_provider_name()} for user {user.id}")
        return True

    def get_connection(self, user: User, db: Session) -> Optional[ConnectionModel]:
        """
        Get user's connection for this provider

        Args:
            user: User to get connection for
            db: Database session

        Returns:
            Connection instance or None
        """
        model_class = self.get_connection_model()
        return db.query(model_class).filter_by(user_id=user.id).first()

    def get_active_connection(self, user: User, db: Session) -> Optional[ConnectionModel]:
        """
        Get user's active connection for this provider

        Args:
            user: User to get connection for
            db: Database session

        Returns:
            Active connection instance or None
        """
        model_class = self.get_connection_model()
        return db.query(model_class).filter_by(
            user_id=user.id,
            is_active=True
        ).first()

    # ==================== Private Helper Methods ====================

    async def _exchange_code_with_full_response(self, code: str) -> Dict[str, Any]:
        """Internal method to get full token response for subclass processing"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    headers=self.get_token_headers(),
                    data=self.get_token_exchange_data(code)
                )

            if response.status_code != 200:
                raise TokenExchangeException(
                    f"Failed to exchange code: {response.text}",
                    provider=self.get_provider_name()
                )

            return response.json()

        except httpx.HTTPError as e:
            raise TokenExchangeException(
                f"HTTP error during token exchange: {str(e)}",
                provider=self.get_provider_name()
            )
