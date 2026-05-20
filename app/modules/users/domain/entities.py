"""
User Entity - Contains business logic and rules

Entities are defined by their identity (ID) and contain business rules.
They are mutable and their state can change over time.
"""

from typing import Optional
from datetime import date
from app.modules.users.domain.value_objects import Email, PhoneNumber, UserRole, FullName, Address


class UserEntity:
    """
    User entity representing a user in the system.

    Business Rules:
    1. User must have at least one identifier (email OR phone)
    2. User can have both email and phone
    3. User cannot disconnect last identifier
    4. OAuth users cannot disconnect their OAuth email
    5. User must have password OR OAuth provider
    6. Admin emails are automatically granted admin role
    """

    def __init__(
        self,
        id: int,
        first_name: str,
        last_name: str,
        role: UserRole,
        is_active: bool,
        email_verified: bool,
        email: Optional[Email] = None,
        phone: Optional[PhoneNumber] = None,
        password_hash: Optional[str] = None,
        oauth_provider: Optional[str] = None,
        oauth_id: Optional[str] = None,
        profile_picture_url: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        gender: Optional[str] = None,
        age: Optional[int] = None,
        t_shirt_size: Optional[str] = None,
        address: Optional[Address] = None,
        primary_sync_source: Optional[str] = None,
    ):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.password_hash = password_hash
        self.oauth_provider = oauth_provider
        self.oauth_id = oauth_id
        self.profile_picture_url = profile_picture_url
        self.role = role
        self.is_active = is_active
        self.email_verified = email_verified
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.age = age
        self.t_shirt_size = t_shirt_size
        self.address = address or Address()
        self.primary_sync_source = primary_sync_source

        # Validate business rules
        self._validate()

    def _validate(self):
        """Validate business rules"""
        # Rule 1: Must have at least one identifier
        if not self.email and not self.phone:
            raise ValueError("User must have at least one identifier (email or phone)")

        # Rule 2: Must have authentication method
        if not self.password_hash and not self.oauth_provider:
            raise ValueError("User must have password or OAuth provider")

    @property
    def full_name(self) -> FullName:
        """Get user's full name"""
        return FullName(self.first_name, self.last_name)

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        return self.role.is_admin()

    @property
    def is_super_admin(self) -> bool:
        """Check if user is super admin"""
        return self.role.is_super_admin()

    @property
    def has_password(self) -> bool:
        """Check if user has password set"""
        return self.password_hash is not None and self.password_hash != ''

    @property
    def is_oauth_user(self) -> bool:
        """Check if user registered via OAuth"""
        return self.oauth_provider is not None

    def has_email(self) -> bool:
        """Check if user has email configured"""
        return self.email is not None

    def has_phone(self) -> bool:
        """Check if user has phone configured"""
        return self.phone is not None

    def can_disconnect_email(self) -> bool:
        """
        Check if email can be safely disconnected.

        Business Rules:
        - Must have phone as alternative
        - Cannot disconnect OAuth email
        """
        if self.is_oauth_user:
            return False  # Cannot disconnect OAuth email
        return self.has_email() and self.has_phone()

    def can_disconnect_phone(self) -> bool:
        """
        Check if phone can be safely disconnected.

        Business Rule: Must have email as alternative
        """
        return self.has_phone() and self.has_email()

    def connect_email(self, email: Email):
        """
        Connect email to user account.

        Business Rule: User must not already have email
        """
        if self.has_email():
            raise ValueError("User already has an email address")
        self.email = email

    def disconnect_email(self):
        """
        Disconnect email from user account.

        Business Rules:
        - Must have phone as alternative
        - Cannot disconnect OAuth email
        """
        if not self.can_disconnect_email():
            if self.is_oauth_user:
                raise ValueError(f"Cannot disconnect email used for {self.oauth_provider} authentication")
            raise ValueError("Cannot disconnect email without phone as alternative")
        self.email = None

    def connect_phone(self, phone: PhoneNumber):
        """
        Connect phone to user account.

        Business Rule: User must not already have phone
        """
        if self.has_phone():
            raise ValueError("User already has a phone number")
        self.phone = phone

    def disconnect_phone(self):
        """
        Disconnect phone from user account.

        Business Rule: Must have email as alternative
        """
        if not self.can_disconnect_phone():
            raise ValueError("Cannot disconnect phone without email as alternative")
        self.phone = None

    def set_password(self, password_hash: str):
        """
        Set password for user.

        Business Rule: OAuth users can set password to enable password login
        """
        if self.has_password:
            raise ValueError("User already has password set. Use change_password instead")
        self.password_hash = password_hash

    def change_password(self, new_password_hash: str):
        """
        Change user's password.

        Business Rule: User must already have a password
        """
        if not self.has_password:
            raise ValueError("User does not have password set. Use set_password instead")
        self.password_hash = new_password_hash

    def deactivate(self):
        """Deactivate user account"""
        self.is_active = False

    def activate(self):
        """Activate user account"""
        self.is_active = True

    def verify_email(self):
        """Mark email as verified"""
        if not self.has_email():
            raise ValueError("Cannot verify email: user has no email")
        self.email_verified = True

    def grant_admin_role(self):
        """Grant admin role to user"""
        self.role = UserRole.ADMIN

    def grant_super_admin_role(self):
        """Grant super admin role to user"""
        self.role = UserRole.SUPER_ADMIN

    def revoke_admin_role(self):
        """Revoke admin privileges"""
        self.role = UserRole.USER

    def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        gender: Optional[str] = None,
        age: Optional[int] = None,
        t_shirt_size: Optional[str] = None,
        address: Optional[Address] = None,
    ):
        """Update user profile information"""
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if date_of_birth is not None:
            self.date_of_birth = date_of_birth
        if gender is not None:
            self.gender = gender
        if age is not None:
            self.age = age
        if t_shirt_size is not None:
            self.t_shirt_size = t_shirt_size
        if address is not None:
            self.address = address

    def set_primary_sync_source(self, source: str):
        """
        Set primary fitness tracker sync source.

        Business Rule: Only one source can auto-sync at a time
        """
        valid_sources = ['strava', 'fitbit', 'garmin', 'wahoo', 'google_fit']
        if source not in valid_sources:
            raise ValueError(f"Invalid sync source: {source}")
        self.primary_sync_source = source

    def __repr__(self) -> str:
        identifier = str(self.email) if self.email else (str(self.phone) if self.phone else f"id:{self.id}")
        return f"<UserEntity(id={self.id}, identifier='{identifier}', role={self.role.value})>"

    def __eq__(self, other) -> bool:
        """Entities are equal if they have the same ID"""
        if not isinstance(other, UserEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Entities are hashed by their ID"""
        return hash(self.id)
