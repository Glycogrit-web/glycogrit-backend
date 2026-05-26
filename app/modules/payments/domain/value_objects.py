"""
Value Objects for Payment Domain

Value objects are immutable objects that represent concepts in the domain
through their attributes rather than identity.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """
    Value object for monetary amounts.

    Immutable representation of money with currency.
    """

    amount: Decimal
    currency: str = "INR"

    def __post_init__(self):
        """Validate money constraints"""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency is required")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")

    def to_smallest_unit(self) -> int:
        """
        Convert to smallest currency unit (paise for INR, cents for USD).

        Returns:
            Amount in smallest unit (e.g., 100.50 INR -> 10050 paise)
        """
        return int(self.amount * 100)

    @classmethod
    def from_smallest_unit(cls, amount: int, currency: str = "INR") -> "Money":
        """
        Create Money from smallest currency unit.

        Args:
            amount: Amount in smallest unit (e.g., paise, cents)
            currency: Currency code (default: INR)

        Returns:
            Money instance
        """
        return cls(Decimal(amount) / 100, currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "INR") -> "Money":
        """
        Create Money from float value.

        Args:
            amount: Amount as float
            currency: Currency code (default: INR)

        Returns:
            Money instance
        """
        return cls(Decimal(str(amount)), currency)

    def add(self, other: "Money") -> "Money":
        """
        Add two Money objects (must have same currency).

        Args:
            other: Another Money instance

        Returns:
            New Money instance with sum

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """
        Subtract two Money objects (must have same currency).

        Args:
            other: Another Money instance

        Returns:
            New Money instance with difference

        Raises:
            ValueError: If currencies don't match or result is negative
        """
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Money(result, self.currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"


@dataclass(frozen=True)
class GatewayOrderId:
    """
    Value object for payment gateway order IDs.

    Ensures order IDs are valid and immutable.
    """

    value: str
    gateway: str

    def __post_init__(self):
        """Validate order ID constraints"""
        if not self.value:
            raise ValueError("Order ID cannot be empty")
        if not self.gateway:
            raise ValueError("Gateway name is required")
        if len(self.value) > 100:
            raise ValueError("Order ID too long (max 100 characters)")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"GatewayOrderId(value='{self.value}', gateway='{self.gateway}')"


@dataclass(frozen=True)
class GatewayPaymentId:
    """
    Value object for payment gateway payment IDs.

    Represents the unique payment ID from the gateway after successful payment.
    """

    value: str
    gateway: str

    def __post_init__(self):
        """Validate payment ID constraints"""
        if not self.value:
            raise ValueError("Payment ID cannot be empty")
        if not self.gateway:
            raise ValueError("Gateway name is required")
        if len(self.value) > 100:
            raise ValueError("Payment ID too long (max 100 characters)")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"GatewayPaymentId(value='{self.value}', gateway='{self.gateway}')"


@dataclass(frozen=True)
class RefundAmount:
    """
    Value object for refund amounts.

    Ensures refund amount is valid and within payment amount.
    """

    amount: Decimal
    currency: str
    original_payment_amount: Decimal

    def __post_init__(self):
        """Validate refund constraints"""
        if self.amount <= 0:
            raise ValueError("Refund amount must be positive")
        if self.amount > self.original_payment_amount:
            raise ValueError(
                f"Refund amount ({self.amount}) cannot exceed "
                f"original payment amount ({self.original_payment_amount})"
            )
        if not self.currency:
            raise ValueError("Currency is required")

    def is_full_refund(self) -> bool:
        """Check if this is a full refund"""
        return self.amount == self.original_payment_amount

    def is_partial_refund(self) -> bool:
        """Check if this is a partial refund"""
        return self.amount < self.original_payment_amount

    def __str__(self) -> str:
        refund_type = "full" if self.is_full_refund() else "partial"
        return f"{self.amount} {self.currency} ({refund_type} refund)"

    def __repr__(self) -> str:
        return (
            f"RefundAmount(amount={self.amount}, currency='{self.currency}', "
            f"original_payment_amount={self.original_payment_amount})"
        )
