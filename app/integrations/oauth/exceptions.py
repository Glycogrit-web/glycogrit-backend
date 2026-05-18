"""
OAuth Integration Exceptions
"""


class OAuthException(Exception):
    """Base exception for OAuth-related errors"""
    def __init__(self, message: str, provider: str = None):
        self.message = message
        self.provider = provider
        super().__init__(self.message)


class TokenRefreshException(OAuthException):
    """Exception raised when token refresh fails"""
    pass


class ProviderConfigException(OAuthException):
    """Exception raised when OAuth provider is not properly configured"""
    pass


class ConnectionAlreadyExistsException(OAuthException):
    """Exception raised when connection already exists for another user"""
    pass


class TokenExchangeException(OAuthException):
    """Exception raised when authorization code exchange fails"""
    pass
