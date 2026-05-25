"""
Users Service Layer

Contains business logic and CQRS commands/queries.
"""

from app.modules.users.services.auth_service import AuthService
from app.modules.users.services.commands import (
    ChangePasswordCommand,
    ConnectEmailCommand,
    ConnectPhoneCommand,
    DisconnectEmailCommand,
    DisconnectPhoneCommand,
    RegisterUserCommand,
    UpdateProfileCommand,
)
from app.modules.users.services.queries import (
    GetActiveUsersQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByPhoneQuery,
)
from app.modules.users.services.user_service import UserService

__all__ = [
    "UserService",
    "AuthService",
    "RegisterUserCommand",
    "UpdateProfileCommand",
    "ChangePasswordCommand",
    "ConnectEmailCommand",
    "ConnectPhoneCommand",
    "DisconnectEmailCommand",
    "DisconnectPhoneCommand",
    "GetUserByIdQuery",
    "GetUserByEmailQuery",
    "GetUserByPhoneQuery",
    "GetActiveUsersQuery",
]
