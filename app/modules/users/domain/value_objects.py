"""
Value Objects for Users Domain

Value objects are immutable and defined by their attributes.
They encapsulate validation logic and domain rules.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
import re


class UserRole(str, Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    def is_admin(self) -> bool:
        """Check if role has admin privileges"""
        return self in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    def is_super_admin(self) -> bool:
        """Check if role is super admin"""
        return self == UserRole.SUPER_ADMIN


@dataclass(frozen=True)
class Email:
    """
    Email value object with validation.

    Business Rules:
    - Must be a valid email format
    - Case-insensitive (stored lowercase)
    - Cannot be empty or None
    """
    value: str

    def __post_init__(self):
        """Validate email format"""
        if not self.value:
            raise ValueError("Email cannot be empty")

        # Simple email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.value):
            raise ValueError(f"Invalid email format: {self.value}")

        # Store lowercase
        object.__setattr__(self, 'value', self.value.lower())

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, Email):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    @property
    def domain(self) -> str:
        """Get email domain"""
        return self.value.split('@')[1]

    @property
    def local_part(self) -> str:
        """Get local part of email"""
        return self.value.split('@')[0]


@dataclass(frozen=True)
class PhoneNumber:
    """
    Phone number value object with validation.

    Business Rules:
    - Must be exactly 10 digits (Indian format)
    - Stored without formatting
    - Cannot be empty or None
    """
    value: str

    def __post_init__(self):
        """Validate and normalize phone number"""
        if not self.value:
            raise ValueError("Phone number cannot be empty")

        # Remove any non-digit characters
        cleaned = re.sub(r'[^\d]', '', self.value)

        # Validate 10 digits
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError(f"Phone number must be exactly 10 digits: {self.value}")

        # Store cleaned version
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, PhoneNumber):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    def formatted(self) -> str:
        """Format phone number for display (XXX-XXX-XXXX)"""
        return f"{self.value[:3]}-{self.value[3:6]}-{self.value[6:]}"

    def with_country_code(self, country_code: str = "+91") -> str:
        """Get phone number with country code"""
        return f"{country_code}{self.value}"


@dataclass(frozen=True)
class FullName:
    """
    Full name value object.

    Business Rules:
    - First name and last name required
    - Names must not be empty
    - Trimmed of whitespace
    """
    first_name: str
    last_name: str

    def __post_init__(self):
        """Validate names"""
        if not self.first_name or not self.first_name.strip():
            raise ValueError("First name cannot be empty")
        if not self.last_name or not self.last_name.strip():
            raise ValueError("Last name cannot be empty")

        # Trim whitespace
        object.__setattr__(self, 'first_name', self.first_name.strip())
        object.__setattr__(self, 'last_name', self.last_name.strip())

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full(self) -> str:
        """Get full name"""
        return str(self)

    @property
    def initials(self) -> str:
        """Get initials (F.L.)"""
        return f"{self.first_name[0].upper()}.{self.last_name[0].upper()}."


@dataclass(frozen=True)
class Address:
    """
    Address value object.

    Business Rules:
    - All fields optional
    - Trimmed of whitespace
    """
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    def __post_init__(self):
        """Normalize address fields"""
        if self.city:
            object.__setattr__(self, 'city', self.city.strip())
        if self.state:
            object.__setattr__(self, 'state', self.state.strip())
        if self.postal_code:
            object.__setattr__(self, 'postal_code', self.postal_code.strip())
        if self.country:
            object.__setattr__(self, 'country', self.country.strip())

    def is_complete(self) -> bool:
        """Check if address is complete"""
        return all([self.city, self.state, self.postal_code, self.country])

    def __str__(self) -> str:
        parts = [p for p in [self.city, self.state, self.postal_code, self.country] if p]
        return ", ".join(parts) if parts else "No address"
