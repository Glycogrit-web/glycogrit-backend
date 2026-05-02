"""
Value objects for Registration module.

Value objects are immutable and represent domain concepts.
"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass(frozen=True)
class RegistrationNumber:
    """
    Value object for registration number.

    Format: EVT{event_id}-{random_6_chars}
    Example: EVT123-A1B2C3
    """
    value: str

    def __post_init__(self):
        """Validate registration number"""
        if not self.value:
            raise ValueError("Registration number cannot be empty")

        if not self.value.startswith("EVT"):
            raise ValueError("Registration number must start with 'EVT'")

        if "-" not in self.value:
            raise ValueError("Registration number must contain '-' separator")

        parts = self.value.split("-")
        if len(parts) != 2:
            raise ValueError("Registration number must have format EVT{id}-{code}")

        # Validate event ID part
        event_part = parts[0][3:]  # Remove 'EVT' prefix
        if not event_part.isdigit():
            raise ValueError("Event ID part must be numeric")

        # Validate code part (6 alphanumeric characters)
        code_part = parts[1]
        if len(code_part) != 6:
            raise ValueError("Code part must be 6 characters")

        if not code_part.isalnum():
            raise ValueError("Code part must be alphanumeric")

    def __str__(self) -> str:
        return self.value

    @property
    def event_id(self) -> int:
        """Extract event ID from registration number"""
        event_part = self.value.split("-")[0][3:]  # Remove 'EVT' prefix
        return int(event_part)


@dataclass(frozen=True)
class BibNumber:
    """
    Value object for bib number (race number).

    Bib numbers are assigned to participants for identification during events.
    """
    value: str

    def __post_init__(self):
        """Validate bib number"""
        if not self.value:
            raise ValueError("Bib number cannot be empty")

        # Bib numbers are typically alphanumeric
        if not self.value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Bib number must be alphanumeric (hyphens and underscores allowed)")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ParticipantDetails:
    """
    Value object for participant personal details.

    Encapsulates participant information with validation.
    """
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    t_shirt_size: Optional[str] = None

    def __post_init__(self):
        """Validate participant details"""
        # Validate name
        if not self.name or len(self.name.strip()) < 2:
            raise ValueError("Participant name must be at least 2 characters")

        if len(self.name) > 255:
            raise ValueError("Participant name must not exceed 255 characters")

        # Validate age
        if self.age is not None:
            if self.age < 0 or self.age > 150:
                raise ValueError("Age must be between 0 and 150")

        # Validate gender
        if self.gender is not None:
            valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
            if self.gender.lower() not in valid_genders:
                raise ValueError(f"Gender must be one of: {', '.join(valid_genders)}")

        # Validate t-shirt size
        if self.t_shirt_size is not None:
            valid_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
            if self.t_shirt_size.upper() not in valid_sizes:
                raise ValueError(f"T-shirt size must be one of: {', '.join(valid_sizes)}")

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "participant_name": self.name,
            "age": self.age,
            "gender": self.gender,
            "t_shirt_size": self.t_shirt_size
        }


@dataclass(frozen=True)
class UpgradePrice:
    """
    Value object for tier upgrade price calculation.

    Represents the price difference when upgrading from one tier to another.
    """
    amount: Decimal
    currency: str = "INR"
    from_tier_price: Decimal = Decimal("0")
    to_tier_price: Decimal = Decimal("0")

    def __post_init__(self):
        """Validate upgrade price"""
        # Use object.__setattr__ for frozen dataclass validation
        if self.amount < 0:
            object.__setattr__(self, 'amount', Decimal("0"))

        if self.from_tier_price < 0:
            raise ValueError("From tier price cannot be negative")

        if self.to_tier_price < 0:
            raise ValueError("To tier price cannot be negative")

        if not self.currency:
            raise ValueError("Currency cannot be empty")

    @classmethod
    def calculate(
        cls,
        from_tier_price: Decimal,
        to_tier_price: Decimal,
        currency: str = "INR"
    ) -> 'UpgradePrice':
        """
        Calculate upgrade price from tier prices.

        Args:
            from_tier_price: Current tier price
            to_tier_price: New tier price
            currency: Currency code

        Returns:
            UpgradePrice instance
        """
        amount = max(to_tier_price - from_tier_price, Decimal("0"))
        return cls(
            amount=amount,
            currency=currency,
            from_tier_price=from_tier_price,
            to_tier_price=to_tier_price
        )

    @property
    def is_free(self) -> bool:
        """Check if upgrade is free"""
        return self.amount == 0

    @property
    def requires_payment(self) -> bool:
        """Check if upgrade requires payment"""
        return self.amount > 0

    def __str__(self) -> str:
        if self.is_free:
            return "Free upgrade"
        return f"{self.currency} {float(self.amount):.2f}"


@dataclass(frozen=True)
class TierCapacity:
    """
    Value object for tier capacity tracking.

    Encapsulates capacity logic for registration tiers.
    """
    max_registrations: Optional[int]
    current_registrations: int

    def __post_init__(self):
        """Validate tier capacity"""
        if self.current_registrations < 0:
            raise ValueError("Current registrations cannot be negative")

        if self.max_registrations is not None and self.max_registrations < 0:
            raise ValueError("Max registrations cannot be negative")

        # Allow current > max (for overbooking scenarios handled by business logic)

    @property
    def has_limit(self) -> bool:
        """Check if tier has a capacity limit"""
        return self.max_registrations is not None

    @property
    def is_unlimited(self) -> bool:
        """Check if tier has unlimited capacity"""
        return self.max_registrations is None

    @property
    def remaining(self) -> Optional[int]:
        """Get remaining capacity"""
        if self.is_unlimited:
            return None
        return max(0, self.max_registrations - self.current_registrations)

    @property
    def is_sold_out(self) -> bool:
        """Check if tier is sold out"""
        if self.is_unlimited:
            return False
        return self.current_registrations >= self.max_registrations

    @property
    def utilization_percentage(self) -> Optional[float]:
        """Calculate capacity utilization as percentage"""
        if self.is_unlimited:
            return None
        if self.max_registrations == 0:
            return 100.0
        return (self.current_registrations / self.max_registrations) * 100

    def __str__(self) -> str:
        if self.is_unlimited:
            return f"{self.current_registrations} registrations (unlimited)"
        return f"{self.current_registrations}/{self.max_registrations} registrations"
