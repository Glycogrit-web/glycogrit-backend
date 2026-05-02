"""
Domain entities for Registration module.

Entities encapsulate business rules and domain logic.
"""

from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from app.core.enums import RegistrationStatus

if TYPE_CHECKING:
    from app.modules.registrations.domain.registration import Registration
    from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier


class RegistrationEntity:
    """
    Domain entity for Registration with business rules.

    Encapsulates registration-related business logic including:
    - Status validation
    - Payment tracking
    - Tier management
    - Registration lifecycle
    """

    def __init__(self, registration: 'Registration'):
        """
        Initialize RegistrationEntity.

        Args:
            registration: Registration ORM model instance
        """
        self._registration = registration

    # ===== Status Properties =====

    @property
    def is_pending(self) -> bool:
        """Check if registration is pending"""
        return self._registration.status == RegistrationStatus.PENDING.value

    @property
    def is_confirmed(self) -> bool:
        """Check if registration is confirmed"""
        return self._registration.status == RegistrationStatus.CONFIRMED.value

    @property
    def is_payment_completed(self) -> bool:
        """Check if registration payment is completed"""
        return self._registration.status == RegistrationStatus.PAYMENT_COMPLETED.value

    @property
    def is_cancelled(self) -> bool:
        """Check if registration is cancelled"""
        return self._registration.status == RegistrationStatus.CANCELLED.value

    @property
    def is_active(self) -> bool:
        """Check if registration is active (confirmed or payment completed)"""
        return self._registration.status in [
            RegistrationStatus.CONFIRMED.value,
            RegistrationStatus.PAYMENT_COMPLETED.value
        ]

    # ===== Payment Properties =====

    @property
    def has_paid(self) -> bool:
        """Check if user has made any successful payment"""
        return (
            self._registration.successful_payments_count > 0 and
            self._registration.total_amount_paid > 0
        )

    @property
    def has_outstanding_balance(self) -> bool:
        """Check if there's an outstanding balance"""
        return self._registration.has_outstanding_balance

    @property
    def balance_owed(self) -> Decimal:
        """Get balance owed"""
        return Decimal(str(self._registration.balance_owed))

    @property
    def total_amount_paid(self) -> Decimal:
        """Get total amount paid"""
        return Decimal(str(self._registration.total_amount_paid or 0))

    # ===== Tier Properties =====

    @property
    def uses_tier_system(self) -> bool:
        """Check if registration uses tier system"""
        return self._registration.uses_tier_system

    @property
    def has_tier(self) -> bool:
        """Check if registration has a tier assigned"""
        return self._registration.current_tier_id is not None

    @property
    def current_tier(self) -> Optional['EventRegistrationTier']:
        """Get current tier"""
        return self._registration.current_tier

    # ===== Validation Methods =====

    def can_be_cancelled(self) -> tuple[bool, Optional[str]]:
        """
        Check if registration can be cancelled.

        Returns:
            Tuple of (can_cancel, reason_if_not)
        """
        if self.is_cancelled:
            return False, "Registration is already cancelled"

        # Cannot cancel if event has already started (business rule)
        if self._registration.event:
            event_start = self._registration.event.start_date
            if event_start and datetime.now() > event_start:
                return False, "Cannot cancel after event has started"

        return True, None

    def can_upgrade_to_tier(self, new_tier: 'EventRegistrationTier') -> tuple[bool, Optional[str]]:
        """
        Check if registration can be upgraded to a new tier.

        Args:
            new_tier: The tier to upgrade to

        Returns:
            Tuple of (can_upgrade, reason_if_not)
        """
        if not self.uses_tier_system:
            return False, "Registration does not use tier system"

        if not self.has_tier:
            return False, "Registration has no current tier"

        current_tier = self.current_tier
        if not current_tier:
            return False, "Current tier not found"

        # Validate tiers belong to same event
        if new_tier.event_id != current_tier.event_id:
            return False, "New tier does not belong to the same event"

        # Only allow upgrades (higher tier_order)
        if new_tier.tier_order <= current_tier.tier_order:
            return False, "Can only upgrade to higher tier"

        # Check if new tier is active
        if not new_tier.is_active:
            return False, "New tier is not active"

        # Check if new tier has capacity
        tier_entity = TierEntity(new_tier)
        if tier_entity.is_sold_out:
            return False, "New tier is sold out"

        return True, None

    def calculate_upgrade_price(self, new_tier: 'EventRegistrationTier') -> Decimal:
        """
        Calculate the price difference for tier upgrade.

        Args:
            new_tier: The tier to upgrade to

        Returns:
            Price difference (0 if downgrade or free)
        """
        if not self.has_tier:
            return Decimal("0")

        current_tier = self.current_tier
        if not current_tier:
            return Decimal("0")

        price_diff = Decimal(str(new_tier.price)) - Decimal(str(current_tier.price))
        return max(price_diff, Decimal("0"))

    def can_switch_tier(self, new_tier: 'EventRegistrationTier') -> tuple[bool, Optional[str]]:
        """
        Check if a pending registration can switch to a different tier.

        Only pending registrations can switch tiers freely.
        Confirmed registrations must use upgrade flow.

        Args:
            new_tier: The tier to switch to

        Returns:
            Tuple of (can_switch, reason_if_not)
        """
        if not self.is_pending:
            return False, "Only pending registrations can switch tiers"

        if not self.uses_tier_system:
            return False, "Registration does not use tier system"

        # Check if new tier is active
        if not new_tier.is_active:
            return False, "New tier is not active"

        # Check if new tier has capacity
        tier_entity = TierEntity(new_tier)
        if tier_entity.is_sold_out:
            return False, "New tier is sold out"

        return True, None

    # ===== Time-based Validation =====

    def is_stale(self, max_age_hours: int = 48) -> bool:
        """
        Check if a pending registration is stale (old and unpaid).

        Args:
            max_age_hours: Maximum age in hours before considering stale

        Returns:
            True if registration is stale
        """
        if not self.is_pending:
            return False

        if not self._registration.registered_at:
            return False

        age = datetime.now() - self._registration.registered_at
        return age > timedelta(hours=max_age_hours)

    # ===== Business Logic Methods =====

    def determine_status_after_payment(self, tier: 'EventRegistrationTier') -> str:
        """
        Determine registration status after payment based on tier requirements.

        Args:
            tier: The tier being registered for

        Returns:
            Registration status value
        """
        if tier.price == 0:
            return RegistrationStatus.CONFIRMED.value
        elif tier.requires_payment:
            return RegistrationStatus.PENDING.value
        else:
            return RegistrationStatus.CONFIRMED.value


class TierEntity:
    """
    Domain entity for EventRegistrationTier with business rules.

    Encapsulates tier-related business logic including:
    - Capacity management
    - Availability checks
    - Pricing logic
    """

    def __init__(self, tier: 'EventRegistrationTier'):
        """
        Initialize TierEntity.

        Args:
            tier: EventRegistrationTier ORM model instance
        """
        self._tier = tier

    # ===== Capacity Properties =====

    @property
    def has_capacity_limit(self) -> bool:
        """Check if tier has a capacity limit"""
        return self._tier.max_registrations is not None

    @property
    def capacity_remaining(self) -> Optional[int]:
        """Get remaining capacity"""
        return self._tier.capacity_remaining

    @property
    def is_sold_out(self) -> bool:
        """Check if tier is sold out"""
        return self._tier.is_sold_out

    @property
    def is_available(self) -> bool:
        """Check if tier is available for registration"""
        return self._tier.is_active and not self.is_sold_out

    # ===== Pricing Properties =====

    @property
    def is_free(self) -> bool:
        """Check if tier is free"""
        return self._tier.is_free

    @property
    def requires_payment(self) -> bool:
        """Check if tier requires payment"""
        return self._tier.requires_payment and self._tier.price > 0

    @property
    def price(self) -> Decimal:
        """Get tier price"""
        return Decimal(str(self._tier.price or 0))

    # ===== Validation Methods =====

    def can_accept_registration(self) -> tuple[bool, Optional[str]]:
        """
        Check if tier can accept new registrations.

        Returns:
            Tuple of (can_accept, reason_if_not)
        """
        if not self._tier.is_active:
            return False, "Tier is not active"

        if self.is_sold_out:
            return False, "Tier is sold out"

        return True, None

    def calculate_price_difference(self, other_tier: 'EventRegistrationTier') -> Decimal:
        """
        Calculate price difference with another tier.

        Args:
            other_tier: The tier to compare with

        Returns:
            Price difference (positive if this tier is more expensive)
        """
        return self.price - Decimal(str(other_tier.price or 0))

    def is_higher_than(self, other_tier: 'EventRegistrationTier') -> bool:
        """
        Check if this tier is higher than another tier.

        Args:
            other_tier: The tier to compare with

        Returns:
            True if this tier has higher tier_order
        """
        return self._tier.tier_order > other_tier.tier_order

    def is_same_tier(self, other_tier: 'EventRegistrationTier') -> bool:
        """
        Check if this is the same tier as another.

        Args:
            other_tier: The tier to compare with

        Returns:
            True if same tier_order
        """
        return self._tier.tier_order == other_tier.tier_order

    def can_increment_count(self) -> tuple[bool, Optional[str]]:
        """
        Check if registration count can be incremented.

        Returns:
            Tuple of (can_increment, reason_if_not)
        """
        if not self.has_capacity_limit:
            return True, None

        if self.is_sold_out:
            return False, "Tier is at maximum capacity"

        return True, None
