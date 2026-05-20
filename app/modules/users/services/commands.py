"""
CQRS Commands for Users Module

Commands represent write operations that change state.
Each command encapsulates a specific business operation.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class RegisterUserCommand:
    """Command to register a new user"""
    first_name: str
    last_name: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


@dataclass
class RegisterOAuthUserCommand:
    """Command to register or authenticate user via OAuth"""
    email: str
    oauth_provider: str
    oauth_id: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str] = None


@dataclass
class UpdateProfileCommand:
    """Command to update user profile"""
    user_id: int
    current_user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    t_shirt_size: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@dataclass
class ChangePasswordCommand:
    """Command to change user password"""
    user_id: int
    current_user_id: int
    current_password: str
    new_password: str


@dataclass
class SetPasswordCommand:
    """Command to set password for OAuth users"""
    user_id: int
    current_user_id: int
    phone: str
    password: str


@dataclass
class ConnectEmailCommand:
    """Command to connect email to user account"""
    user_id: int
    current_user_id: int
    email: str


@dataclass
class DisconnectEmailCommand:
    """Command to disconnect email from user account"""
    user_id: int
    current_user_id: int


@dataclass
class ConnectPhoneCommand:
    """Command to connect phone to user account"""
    user_id: int
    current_user_id: int
    phone: str


@dataclass
class DisconnectPhoneCommand:
    """Command to disconnect phone from user account"""
    user_id: int
    current_user_id: int


@dataclass
class DeactivateUserCommand:
    """Command to deactivate user account"""
    user_id: int
    current_user_id: int


@dataclass
class ActivateUserCommand:
    """Command to activate user account"""
    user_id: int
    admin_user_id: int


@dataclass
class GrantAdminRoleCommand:
    """Command to grant admin role"""
    user_id: int
    admin_user_id: int


@dataclass
class RevokeAdminRoleCommand:
    """Command to revoke admin role"""
    user_id: int
    admin_user_id: int
