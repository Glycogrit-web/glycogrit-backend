"""
User Service - Business logic for user management

Implements CQRS pattern with commands and queries.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.modules.users.domain.user import User
from app.modules.users.repositories.user_repository import UserRepository
from app.modules.users.services.commands import (
    RegisterUserCommand,
    UpdateProfileCommand,
    ChangePasswordCommand,
    SetPasswordCommand,
    ConnectEmailCommand,
    DisconnectEmailCommand,
    ConnectPhoneCommand,
    DisconnectPhoneCommand,
    DeactivateUserCommand,
    ActivateUserCommand,
    GrantAdminRoleCommand,
    RevokeAdminRoleCommand,
)
from app.modules.users.services.queries import (
    GetUserByIdQuery,
    GetUserByEmailQuery,
    GetUserByPhoneQuery,
    GetUserByIdentifierQuery,
    GetActiveUsersQuery,
    GetAllUsersQuery,
    GetUsersByRoleQuery,
    CountActiveUsersQuery,
    CountUsersByRoleQuery,
)
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    AuthenticationException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.auth import hash_password, verify_password
from app.core.config import settings


class UserService(BaseService):
    """Service for user-related business logic using CQRS pattern."""

    def __init__(self, db: Session):
        """
        Initialize the UserService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = UserRepository(db)

    # COMMAND HANDLERS (Write Operations)

    def handle_register_user(self, command: RegisterUserCommand) -> User:
        """
        Handle RegisterUserCommand.

        Args:
            command: RegisterUserCommand with registration data

        Returns:
            Created User instance

        Raises:
            ValidationException: If neither email nor phone provided
            AlreadyExistsException: If email or phone already exists
        """
        # Validate at least one identifier
        if not command.email and not command.phone:
            raise ValidationException("Either email or phone must be provided")

        # Check if email already exists
        if command.email and self.repository.email_exists(command.email):
            raise AlreadyExistsException("User", "email", command.email)

        # Check if phone already exists
        if command.phone and self.repository.phone_exists(command.phone):
            raise AlreadyExistsException("User", "phone", command.phone)

        # Determine role based on email
        user_role = "admin" if command.email and command.email.lower() in settings.admin_emails_list else "user"

        # Create new user
        user_data = {
            "email": command.email.lower() if command.email else None,
            "phone": command.phone,
            "password_hash": hash_password(command.password),
            "first_name": command.first_name,
            "last_name": command.last_name,
            "city": command.city,
            "state": command.state,
            "is_active": True,
            "email_verified": False,
            "role": user_role
        }

        return self.repository.create(user_data)

    def handle_update_profile(self, command: UpdateProfileCommand) -> User:
        """
        Handle UpdateProfileCommand.

        Args:
            command: UpdateProfileCommand with update data

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the profile
            AlreadyExistsException: If email or phone already exists
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user profile")

        # Build update data
        update_data = {}
        if command.first_name is not None:
            update_data["first_name"] = command.first_name
        if command.last_name is not None:
            update_data["last_name"] = command.last_name
        if command.date_of_birth is not None:
            update_data["date_of_birth"] = command.date_of_birth
        if command.gender is not None:
            update_data["gender"] = command.gender
        if command.age is not None:
            update_data["age"] = command.age
        if command.t_shirt_size is not None:
            update_data["t_shirt_size"] = command.t_shirt_size
        if command.city is not None:
            update_data["city"] = command.city
        if command.state is not None:
            update_data["state"] = command.state
        if command.postal_code is not None:
            update_data["postal_code"] = command.postal_code
        if command.country is not None:
            update_data["country"] = command.country

        # Update user
        return self.repository.update(command.user_id, update_data)

    def handle_change_password(self, command: ChangePasswordCommand) -> User:
        """
        Handle ChangePasswordCommand.

        Args:
            command: ChangePasswordCommand with password data

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            AuthenticationException: If current password is incorrect
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Verify current password
        if not verify_password(command.current_password, user.password_hash):
            raise AuthenticationException("Current password is incorrect")

        # Update password
        new_password_hash = hash_password(command.new_password)
        return self.repository.update(command.user_id, {"password_hash": new_password_hash})

    def handle_set_password(self, command: SetPasswordCommand) -> User:
        """
        Handle SetPasswordCommand (for OAuth users).

        Args:
            command: SetPasswordCommand with password and phone

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            ValidationException: If user already has password
            AlreadyExistsException: If phone already exists
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Check if user already has password
        if user.has_password:
            raise ValidationException("User already has a password set")

        # Validate phone uniqueness
        if not self.repository.can_connect_phone(command.phone, command.user_id):
            raise AlreadyExistsException("User", "phone", command.phone)

        # Update user
        password_hash = hash_password(command.password)
        return self.repository.update(command.user_id, {
            "phone": command.phone,
            "password_hash": password_hash
        })

    def handle_connect_email(self, command: ConnectEmailCommand) -> User:
        """
        Handle ConnectEmailCommand.

        Args:
            command: ConnectEmailCommand with email

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            AlreadyExistsException: If email already exists
            ValidationException: If user already has email
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Check if user already has email
        if user.has_email():
            raise ValidationException("User already has an email address")

        # Validate email uniqueness
        if not self.repository.can_connect_email(command.email, command.user_id):
            raise AlreadyExistsException("User", "email", command.email)

        # Update user
        return self.repository.update(command.user_id, {"email": command.email.lower()})

    def handle_disconnect_email(self, command: DisconnectEmailCommand) -> User:
        """
        Handle DisconnectEmailCommand.

        Args:
            command: DisconnectEmailCommand

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            ValidationException: If user can't disconnect email
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Check if OAuth user
        if user.oauth_provider:
            raise ValidationException(
                f"Cannot disconnect email used for {user.oauth_provider} authentication"
            )

        # Check if user can disconnect email
        if not user.can_disconnect_email():
            raise ValidationException("Cannot disconnect email without phone as alternative")

        # Update user
        return self.repository.update(command.user_id, {"email": None})

    def handle_connect_phone(self, command: ConnectPhoneCommand) -> User:
        """
        Handle ConnectPhoneCommand.

        Args:
            command: ConnectPhoneCommand with phone

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            AlreadyExistsException: If phone already exists
            ValidationException: If user already has phone
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Check if user already has phone
        if user.has_phone():
            raise ValidationException("User already has a phone number")

        # Validate phone uniqueness
        if not self.repository.can_connect_phone(command.phone, command.user_id):
            raise AlreadyExistsException("User", "phone", command.phone)

        # Update user
        return self.repository.update(command.user_id, {"phone": command.phone})

    def handle_disconnect_phone(self, command: DisconnectPhoneCommand) -> User:
        """
        Handle DisconnectPhoneCommand.

        Args:
            command: DisconnectPhoneCommand

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
            ValidationException: If user can't disconnect phone
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Check if user can disconnect phone
        if not user.can_disconnect_phone():
            raise ValidationException("Cannot disconnect phone without email as alternative")

        # Update user
        return self.repository.update(command.user_id, {"phone": None})

    def handle_deactivate_user(self, command: DeactivateUserCommand) -> User:
        """
        Handle DeactivateUserCommand.

        Args:
            command: DeactivateUserCommand

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If current user doesn't own the account
        """
        # Get user
        user = self.get_or_404(self.repository, command.user_id, "User")

        # Check ownership
        self.check_ownership(user.id, command.current_user_id, "user account")

        # Deactivate
        return self.repository.deactivate_user(command.user_id)

    def handle_activate_user(self, command: ActivateUserCommand) -> User:
        """
        Handle ActivateUserCommand (admin only).

        Args:
            command: ActivateUserCommand

        Returns:
            Updated User instance

        Raises:
            NotFoundException: If user not found
            PermissionDeniedException: If admin user doesn't have permissions
        """
        # Get admin user
        admin = self.get_or_404(self.repository, command.admin_user_id, "User")
        if not admin.is_admin:
            raise PermissionDeniedException("Admin access required")

        # Activate user
        return self.repository.activate_user(command.user_id)

    def handle_grant_admin_role(self, command: GrantAdminRoleCommand) -> User:
        """
        Handle GrantAdminRoleCommand (super admin only).

        Args:
            command: GrantAdminRoleCommand

        Returns:
            Updated User instance
        """
        # Get admin user
        admin = self.get_or_404(self.repository, command.admin_user_id, "User")
        if admin.role != "super_admin":
            raise PermissionDeniedException("Super admin access required")

        # Grant admin role
        return self.repository.update(command.user_id, {"role": "admin"})

    def handle_revoke_admin_role(self, command: RevokeAdminRoleCommand) -> User:
        """
        Handle RevokeAdminRoleCommand (super admin only).

        Args:
            command: RevokeAdminRoleCommand

        Returns:
            Updated User instance
        """
        # Get admin user
        admin = self.get_or_404(self.repository, command.admin_user_id, "User")
        if admin.role != "super_admin":
            raise PermissionDeniedException("Super admin access required")

        # Revoke admin role
        return self.repository.update(command.user_id, {"role": "user"})

    # QUERY HANDLERS (Read Operations)

    def handle_get_user_by_id(self, query: GetUserByIdQuery) -> User:
        """
        Handle GetUserByIdQuery.

        Args:
            query: GetUserByIdQuery with user ID

        Returns:
            User instance

        Raises:
            NotFoundException: If user not found
        """
        return self.get_or_404(self.repository, query.user_id, "User")

    def handle_get_user_by_email(self, query: GetUserByEmailQuery) -> Optional[User]:
        """
        Handle GetUserByEmailQuery.

        Args:
            query: GetUserByEmailQuery with email

        Returns:
            User instance if found, None otherwise
        """
        return self.repository.get_by_email(query.email)

    def handle_get_user_by_phone(self, query: GetUserByPhoneQuery) -> Optional[User]:
        """
        Handle GetUserByPhoneQuery.

        Args:
            query: GetUserByPhoneQuery with phone

        Returns:
            User instance if found, None otherwise
        """
        return self.repository.get_by_phone(query.phone)

    def handle_get_user_by_identifier(self, query: GetUserByIdentifierQuery) -> Optional[User]:
        """
        Handle GetUserByIdentifierQuery (auto-detect email/phone).

        Args:
            query: GetUserByIdentifierQuery with identifier

        Returns:
            User instance if found, None otherwise
        """
        return self.repository.get_by_identifier(query.identifier)

    def handle_get_active_users(self, query: GetActiveUsersQuery) -> List[User]:
        """
        Handle GetActiveUsersQuery.

        Args:
            query: GetActiveUsersQuery with pagination

        Returns:
            List of active User instances
        """
        return self.repository.get_active_users(query.skip, query.limit)

    def handle_get_all_users(self, query: GetAllUsersQuery) -> List[User]:
        """
        Handle GetAllUsersQuery.

        Args:
            query: GetAllUsersQuery with pagination

        Returns:
            List of all User instances
        """
        return self.repository.get_all(query.skip, query.limit)

    def handle_get_users_by_role(self, query: GetUsersByRoleQuery) -> List[User]:
        """
        Handle GetUsersByRoleQuery.

        Args:
            query: GetUsersByRoleQuery with role and pagination

        Returns:
            List of User instances with specified role
        """
        return self.repository.get_users_by_role(query.role, query.skip, query.limit)

    def handle_count_active_users(self, query: CountActiveUsersQuery) -> int:
        """
        Handle CountActiveUsersQuery.

        Args:
            query: CountActiveUsersQuery

        Returns:
            Number of active users
        """
        return self.repository.count_active_users()

    def handle_count_users_by_role(self, query: CountUsersByRoleQuery) -> int:
        """
        Handle CountUsersByRoleQuery.

        Args:
            query: CountUsersByRoleQuery with role

        Returns:
            Number of users with specified role
        """
        return self.repository.count_by_role(query.role)
