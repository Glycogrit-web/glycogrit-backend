"""
Custom exception classes for the GlycoGrit backend.

These exceptions provide consistent error handling across the application
with appropriate HTTP status codes.
"""

from typing import Any


class AppException(Exception):
    """Base application exception that all custom exceptions inherit from."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a requested resource is not found (HTTP 404)."""

    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, status_code=404)
        self.resource = resource
        self.identifier = identifier


class PermissionDeniedException(AppException):
    """Raised when a user lacks permission to perform an action (HTTP 403)."""

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, status_code=403)


class AlreadyExistsException(AppException):
    """Raised when attempting to create a resource that already exists (HTTP 409)."""

    def __init__(self, resource: str, field: str, value: Any):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(message, status_code=409)
        self.resource = resource
        self.field = field
        self.value = value


class ValidationException(AppException):
    """Raised when input validation fails (HTTP 400)."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, status_code=400)
        self.field = field


class DatabaseException(AppException):
    """Raised when a database operation fails (HTTP 500)."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500)


class AuthenticationException(AppException):
    """Raised when authentication fails (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)
