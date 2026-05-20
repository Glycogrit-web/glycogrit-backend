"""
Users Module - Domain-Driven Design

This module handles all user-related functionality including:
- User registration and authentication
- Profile management
- OAuth integration
- Role-based access control
"""

from app.modules.users.domain.user import User
from app.modules.users.services.user_service import UserService
from app.modules.users.services.auth_service import AuthService
from app.modules.users.repositories.user_repository import UserRepository

__all__ = [
    "User",
    "UserService",
    "AuthService",
    "UserRepository",
]
