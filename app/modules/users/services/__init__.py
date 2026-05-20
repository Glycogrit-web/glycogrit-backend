"""
Users Service Layer

Contains business logic and CQRS commands/queries.
"""

from app.modules.users.services.user_service import UserService
from app.modules.users.services.auth_service import AuthService
from app.modules.users.services.commands import (
    RegisterUserCommand,
    UpdateProfileCommand,
    ChangePasswordCommand,
    ConnectEmailCommand,
    ConnectPhoneCommand,
    DisconnectEmailCommand,
    DisconnectPhoneCommand,
)
from app.modules.users.services.queries import (
    GetUserByIdQuery,
    GetUserByEmailQuery,
    GetUserByPhoneQuery,
    GetActiveUsersQuery,
)

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
