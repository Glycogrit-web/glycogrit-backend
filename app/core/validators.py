"""
Reusable Validation Utilities and Custom Pydantic Types
Reduces validation boilerplate across schemas
"""

import re
from typing import Any

from pydantic import BaseModel, Field, GetCoreSchemaHandler, field_validator
from pydantic_core import core_schema

# ==================== Phone Number Validation ====================


class IndianPhoneStr(str):
    """
    Custom Pydantic type for Indian phone numbers
    Validates and normalizes to 10 digits

    Usage:
        class UserSchema(BaseModel):
            phone: IndianPhoneStr
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> str:
        """Validate and normalize Indian phone number"""
        if not value:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters
        cleaned = re.sub(r"\D", "", value)

        # Remove leading +91 or 91
        if cleaned.startswith("91") and len(cleaned) > 10:
            cleaned = cleaned[2:]
        elif cleaned.startswith("+91"):
            cleaned = cleaned[3:]

        # Validate length
        if len(cleaned) != 10:
            raise ValueError(f"Indian phone number must be 10 digits, got {len(cleaned)}")

        # Validate starts with valid digit (6-9)
        if cleaned[0] not in "6789":
            raise ValueError("Indian phone number must start with 6, 7, 8, or 9")

        return cleaned


class InternationalPhoneStr(str):
    """
    Custom type for international phone numbers
    More lenient validation

    Usage:
        class UserSchema(BaseModel):
            phone: InternationalPhoneStr
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> str:
        """Validate international phone number"""
        if not value:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", value)

        # Validate length (between 10 and 15 digits)
        digit_count = len(re.sub(r"\D", "", cleaned))
        if digit_count < 10 or digit_count > 15:
            raise ValueError(f"Phone number must be between 10 and 15 digits, got {digit_count}")

        return cleaned


# ==================== PIN Code Validation ====================


class IndianPinCodeStr(str):
    """
    Custom type for Indian PIN codes
    Validates 6-digit postal codes

    Usage:
        class AddressSchema(BaseModel):
            pin_code: IndianPinCodeStr
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> str:
        """Validate Indian PIN code"""
        if not value:
            raise ValueError("PIN code is required")

        # Remove all non-digit characters
        cleaned = re.sub(r"\D", "", value)

        # Validate length
        if len(cleaned) != 6:
            raise ValueError(f"PIN code must be 6 digits, got {len(cleaned)}")

        # Validate doesn't start with 0
        if cleaned[0] == "0":
            raise ValueError("PIN code cannot start with 0")

        return cleaned


# ==================== Name Validation ====================


class PersonNameStr(str):
    """
    Custom type for person names
    Validates proper name format

    Usage:
        class UserSchema(BaseModel):
            first_name: PersonNameStr
            last_name: PersonNameStr
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> str:
        """Validate person name"""
        if not value:
            raise ValueError("Name is required")

        # Strip whitespace
        cleaned = value.strip()

        # Validate length
        if len(cleaned) < 1:
            raise ValueError("Name cannot be empty")

        if len(cleaned) > 100:
            raise ValueError("Name cannot exceed 100 characters")

        # Validate contains only letters, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")

        return cleaned


# ==================== Validation Helper Functions ====================


class ValidationHelper:
    """
    Static validation helper methods
    Can be used in field validators or standalone
    """

    @staticmethod
    def validate_indian_phone(phone: str) -> str:
        """
        Validate and normalize Indian phone number

        Args:
            phone: Phone number string

        Returns:
            Normalized 10-digit phone number

        Raises:
            ValueError: If phone number is invalid
        """
        if not phone:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters
        cleaned = re.sub(r"\D", "", phone)

        # Remove leading +91 or 91
        if cleaned.startswith("91") and len(cleaned) > 10:
            cleaned = cleaned[2:]

        # Validate length
        if len(cleaned) != 10:
            raise ValueError(f"Phone number must be 10 digits, got {len(cleaned)}")

        # Validate starts with valid digit
        if cleaned[0] not in "6789":
            raise ValueError("Phone number must start with 6, 7, 8, or 9")

        return cleaned

    @staticmethod
    def validate_pin_code(pin: str) -> str:
        """
        Validate Indian PIN code

        Args:
            pin: PIN code string

        Returns:
            Normalized 6-digit PIN code

        Raises:
            ValueError: If PIN code is invalid
        """
        if not pin:
            raise ValueError("PIN code is required")

        # Remove all non-digit characters
        cleaned = re.sub(r"\D", "", pin)

        # Validate length
        if len(cleaned) != 6:
            raise ValueError(f"PIN code must be 6 digits, got {len(cleaned)}")

        # Validate doesn't start with 0
        if cleaned[0] == "0":
            raise ValueError("PIN code cannot start with 0")

        return cleaned

    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email format

        Args:
            email: Email string

        Returns:
            Lowercase normalized email

        Raises:
            ValueError: If email is invalid
        """
        if not email:
            raise ValueError("Email is required")

        # Basic email regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")

        return email.lower().strip()

    @staticmethod
    def validate_password_strength(
        password: str, min_length: int = 8, require_special: bool = False
    ) -> str:
        """
        Validate password strength with enhanced security requirements

        Security Requirements:
        - Minimum length (default: 8 characters)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - Optional: At least one special character
        - No common passwords or patterns

        Args:
            password: Password string
            min_length: Minimum password length (default: 8)
            require_special: Require special character (default: False)

        Returns:
            Password if valid

        Raises:
            ValueError: If password doesn't meet security requirements
        """
        if not password:
            raise ValueError("Password is required")

        # Length requirement
        if len(password) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters")

        if len(password) > 128:
            raise ValueError("Password cannot exceed 128 characters")

        # Uppercase letter requirement
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")

        # Lowercase letter requirement
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")

        # Digit requirement
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit")

        # Special character requirement (optional, but recommended)
        if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError(
                'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'
            )

        # Common password detection (basic blacklist)
        common_passwords = [
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "password1",
            "password123",
            "welcome",
            "admin",
            "letmein",
            "monkey",
        ]

        if password.lower() in common_passwords:
            raise ValueError("Password is too common. Please choose a stronger password")

        # Pattern detection (sequential, repeated characters)
        if re.search(r"(.)\1{2,}", password):  # Same character 3+ times
            raise ValueError("Password cannot contain repeated characters (e.g., '111', 'aaa')")

        if "123456" in password or "abcdef" in password.lower():
            raise ValueError("Password cannot contain sequential patterns")

        return password

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate URL format

        Args:
            url: URL string

        Returns:
            URL if valid

        Raises:
            ValueError: If URL is invalid
        """
        if not url:
            raise ValueError("URL is required")

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"

        if not re.match(url_pattern, url):
            raise ValueError("Invalid URL format")

        return url

    @staticmethod
    def sanitize_input(text: str, max_length: int | None = None) -> str:
        """
        Sanitize user input by removing potentially dangerous characters

        Args:
            text: Input text
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove null bytes
        sanitized = text.replace("\x00", "")

        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()

        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized


# ==================== Reusable Field Validators ====================


def validate_positive_number(value: float) -> float:
    """Validator for positive numbers"""
    if value <= 0:
        raise ValueError("Value must be positive")
    return value


def validate_non_negative_number(value: float) -> float:
    """Validator for non-negative numbers"""
    if value < 0:
        raise ValueError("Value cannot be negative")
    return value


def validate_percentage(value: float) -> float:
    """Validator for percentage (0-100)"""
    if value < 0 or value > 100:
        raise ValueError("Percentage must be between 0 and 100")
    return value


def validate_non_empty_string(value: str) -> str:
    """Validator for non-empty strings"""
    if not value or not value.strip():
        raise ValueError("Value cannot be empty")
    return value.strip()


# ==================== Example Schema with Custom Types ====================


class ExampleUserSchema(BaseModel):
    """
    Example schema demonstrating custom validation types

    Usage:
        user_data = ExampleUserSchema(
            phone="9876543210",
            pin_code="560001",
            first_name="John",
            last_name="Doe"
        )
    """

    phone: IndianPhoneStr
    pin_code: IndianPinCodeStr | None = None
    first_name: PersonNameStr
    last_name: PersonNameStr
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v):
        return ValidationHelper.validate_email(v)


# ==================== Mixin for Common Validation ====================


class TimestampMixin(BaseModel):
    """Mixin for schemas that include timestamps"""

    created_at: Any | None = None
    updated_at: Any | None = None


class UserOwnershipMixin(BaseModel):
    """Mixin for schemas with user ownership"""

    user_id: int = Field(..., gt=0, description="User ID")


class PaginationMixin(BaseModel):
    """Mixin for pagination parameters"""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
