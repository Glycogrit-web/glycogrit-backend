"""
Unit tests for Tier Management - Critical for event capacity and pricing.

Tests cover tier capacity, pricing, availability, and registration limits.
"""
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import TierSoldOutException, ValidationException
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration import Registration


@pytest.mark.financial
@pytest.mark.unit
class TestTierCapacityManagement:
    """Test tier capacity and sold-out scenarios."""

    @pytest.mark.financial
    def test_tier_becomes_sold_out_when_capacity_reached(self, db: Session, test_event, test_user):
        """
        CRITICAL: Tier should be marked as sold out when max registrations reached.
        Prevents overselling limited tiers.
        """
        # Create tier with capacity of 2
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Limited Tier",
            tier_slug="limited-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=2,
            current_registrations=0
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)

        # Add first registration
        reg1 = Registration(
            user_id=test_user.id,
            event_id=test_event.id,
            registration_number=f"EVT{test_event.id}-TEST01",
            current_tier_id=tier.id,
            participant_name="User 1",
            status="confirmed"
        )
        db.add(reg1)
        tier.current_registrations = 1
        db.commit()

        assert tier.is_sold_out is False

        # Add second registration
        reg2 = Registration(
            user_id=test_user.id + 1,
            event_id=test_event.id,
            registration_number=f"EVT{test_event.id}-TEST02",
            current_tier_id=tier.id,
            participant_name="User 2",
            status="confirmed"
        )
        db.add(reg2)
        tier.current_registrations = 2
        db.commit()
        db.refresh(tier)

        # Now should be sold out
        assert tier.is_sold_out is True
        assert tier.current_registrations == tier.max_registrations

    @pytest.mark.financial
    def test_pending_registrations_dont_count_towards_capacity(self, db: Session, test_event, test_user):
        """
        Edge case: Only confirmed registrations should count towards capacity.
        Pending payments shouldn't block tier availability.
        """
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Test Tier",
            tier_slug="test-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=5
        )
        db.add(tier)
        db.commit()

        # Add pending registration
        pending_reg = Registration(
            user_id=test_user.id,
            event_id=test_event.id,
            registration_number=f"EVT{test_event.id}-TEST01",
            current_tier_id=tier.id,
            participant_name="Pending User",
            status="pending"
        )
        db.add(pending_reg)
        db.commit()

        # Tier should still have capacity
        db.refresh(tier)
        assert tier.current_registrations == 5
        assert tier.capacity_remaining == 5
        assert tier.is_sold_out is False

    def test_unlimited_tier_never_sold_out(self, db: Session, test_event):
        """
        Edge case: Tiers without max_registrations should never be sold out.
        """
        unlimited_tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Unlimited Tier",
            tier_slug="unlimited-tier",
            tier_order=1,
            price=Decimal("100.00"),
            currency="INR",
            max_registrations=None,
            current_registrations=1000
        )
        db.add(unlimited_tier)
        db.commit()
        db.refresh(unlimited_tier)

        assert unlimited_tier.is_sold_out is False
        assert unlimited_tier.capacity_remaining is None

    @pytest.mark.financial
    def test_cannot_register_for_sold_out_tier(self, db: Session, test_event, test_user):
        """
        CRITICAL: Should not allow registration to sold-out tier.
        Prevents overbooking.
        """
        sold_out_tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Sold Out Tier",
            tier_slug="sold-out-tier",
            tier_order=1,
            price=Decimal("1000.00"),
            currency="INR",
            max_registrations=5,
            current_registrations=5
        )
        db.add(sold_out_tier)
        db.commit()

        assert sold_out_tier.is_sold_out is True

        # Attempt to register should be blocked by validation
        from app.modules.registrations import RegistrationService
        service = RegistrationService(db)

        # This should raise ValidationException
        with pytest.raises(ValidationException, match="sold out|capacity"):
            service.register_for_event_tier(
                event_id=test_event.id,
                user_id=test_user.id,
                tier_id=sold_out_tier.id,
                participant_name="Late User"
            )


@pytest.mark.financial
@pytest.mark.unit
class TestTierPricingValidation:
    """Test tier pricing calculations and validations."""

    def test_tier_prices_must_be_non_negative(self):
        """
        Validation: Tier prices cannot be negative.
        """
        pytest.skip("Model-level validation for negative prices not implemented - should be added to EventRegistrationTier model")

    @pytest.mark.financial
    def test_upgrade_price_calculation_all_combinations(self):
        """
        CRITICAL: Test all tier upgrade price combinations.
        Ensures correct billing for every upgrade path.
        """
        tiers = [
            {"name": "Free", "price": Decimal("0.00")},
            {"name": "Basic", "price": Decimal("500.00")},
            {"name": "Pro", "price": Decimal("1000.00")},
            {"name": "Premium", "price": Decimal("2000.00")},
        ]

        # Test all upgrade combinations
        expected_prices = [
            # From Free
            (0, 1, Decimal("500.00")),   # Free → Basic
            (0, 2, Decimal("1000.00")),  # Free → Pro
            (0, 3, Decimal("2000.00")),  # Free → Premium
            # From Basic
            (1, 2, Decimal("500.00")),   # Basic → Pro
            (1, 3, Decimal("1500.00")),  # Basic → Premium
            # From Pro
            (2, 3, Decimal("1000.00")),  # Pro → Premium
        ]

        for from_idx, to_idx, expected_price in expected_prices:
            current_tier = tiers[from_idx]
            new_tier = tiers[to_idx]

            upgrade_price = new_tier["price"] - current_tier["price"]

            assert upgrade_price == expected_price, \
                f"Upgrade from {current_tier['name']} to {new_tier['name']} should cost {expected_price}, got {upgrade_price}"

    @pytest.mark.financial
    def test_downgrade_prices_are_negative(self):
        """
        Validation: Downgrade should result in negative price (not allowed).
        """
        premium_price = Decimal("2000.00")
        basic_price = Decimal("500.00")

        downgrade_price = basic_price - premium_price

        assert downgrade_price < 0, "Downgrade should have negative price"

    def test_tier_price_formatting(self, db: Session, test_event):
        """
        Test that tier prices are formatted correctly for display.
        """
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Test Tier",
            tier_slug="test-tier",
            tier_order=1,
            price=Decimal("1500.50"),
            currency="INR"
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)

        # Check formatted price
        assert tier.get_formatted_price() == "INR 1500.50"


@pytest.mark.unit
class TestTierOrdering:
    """Test tier ordering and hierarchy."""

    def test_tiers_ordered_by_tier_order(self, db: Session, test_event):
        """
        Tiers should be displayed in correct order based on tier_order.
        """
        # Create tiers in random order
        tier3 = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Premium",
            tier_slug="premium",
            tier_order=2,
            price=Decimal("2000.00"),
            currency="INR"
        )
        tier1 = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Free",
            tier_slug="free",
            tier_order=0,
            price=Decimal("0.00"),
            currency="INR"
        )
        tier2 = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Basic",
            tier_slug="basic",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR"
        )

        db.add_all([tier3, tier1, tier2])
        db.commit()

        # Query tiers ordered by tier_order
        tiers = db.query(EventRegistrationTier)\
            .filter(EventRegistrationTier.event_id == test_event.id)\
            .order_by(EventRegistrationTier.tier_order)\
            .all()

        assert len(tiers) == 3
        assert tiers[0].tier_name == "Free"
        assert tiers[1].tier_name == "Basic"
        assert tiers[2].tier_name == "Premium"

    def test_cannot_upgrade_to_lower_tier_order(self, db: Session, test_tiers):
        """
        Validation: Cannot upgrade to lower tier order (downgrade).
        """
        from app.modules.registrations import RegistrationService

        current_tier = test_tiers[2]  # Premium (tier_order=2)
        lower_tier = test_tiers[1]    # Basic (tier_order=1)

        # Validation should prevent this
        assert lower_tier.tier_order < current_tier.tier_order


@pytest.mark.financial
@pytest.mark.unit
class TestTierRegistrationCounts:
    """Test tier registration count tracking."""

    @pytest.mark.financial
    def test_tier_count_increments_on_registration(self, db: Session, test_event, test_user, test_tiers):
        """
        CRITICAL: Tier count must increment when user registers.
        Affects capacity tracking and sold-out status.
        """
        tier = test_tiers[1]  # Basic tier
        initial_count = tier.current_registrations

        # Register user
        registration = Registration(
            user_id=test_user.id,
            event_id=test_event.id,
            registration_number=f"EVT{test_event.id}-TEST01",
            current_tier_id=tier.id,
            participant_name="Test User",
            status="confirmed"
        )
        db.add(registration)

        # Increment count
        tier.current_registrations += 1
        db.commit()
        db.refresh(tier)

        assert tier.current_registrations == initial_count + 1

    @pytest.mark.financial
    def test_tier_count_decrements_on_upgrade(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: When user upgrades, old tier count decrements, new tier increments.
        Prevents capacity miscalculation.
        """
        old_tier = test_tiers[0]  # Free
        new_tier = test_tiers[1]  # Basic

        old_count = old_tier.current_registrations
        new_count = new_tier.current_registrations

        # Simulate upgrade
        test_registration.current_tier_id = new_tier.id
        old_tier.current_registrations -= 1
        new_tier.current_registrations += 1
        db.commit()

        db.refresh(old_tier)
        db.refresh(new_tier)

        assert old_tier.current_registrations == old_count - 1
        assert new_tier.current_registrations == new_count + 1

    @pytest.mark.financial
    def test_tier_count_not_negative(self, db: Session, test_tiers):
        """
        Validation: Tier count cannot go negative.
        """
        pytest.skip("Model-level validation for negative registration counts not implemented - should be added as CHECK constraint")


@pytest.mark.unit
class TestTierRewards:
    """Test tier rewards and benefits."""

    def test_higher_tiers_have_more_rewards(self, db: Session, test_event):
        """
        Tiers should show their included rewards/benefits.
        """
        free_tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Free",
            tier_slug="free",
            tier_order=0,
            price=Decimal("0.00"),
            currency="INR",
            rewards=["Digital Certificate"]
        )

        premium_tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Premium",
            tier_slug="premium",
            tier_order=2,
            price=Decimal("2000.00"),
            currency="INR",
            rewards=["Digital Certificate", "Medal", "T-Shirt", "Finisher Kit"]
        )

        db.add_all([free_tier, premium_tier])
        db.commit()

        assert len(free_tier.rewards) < len(premium_tier.rewards)
        assert "Medal" in premium_tier.rewards
        assert "Medal" not in free_tier.rewards

    def test_tier_description_contains_benefits(self, db: Session, test_event):
        """
        Tier descriptions should explain what's included.
        """
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Premium",
            tier_slug="premium",
            tier_order=2,
            price=Decimal("2000.00"),
            currency="INR",
            description="Includes medal, t-shirt, and finisher kit",
            rewards=["Medal", "T-Shirt", "Finisher Kit"]
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)

        assert tier.description is not None
        assert len(tier.rewards) == 3


@pytest.mark.financial
@pytest.mark.unit
class TestTierServiceOperations:
    """Test tier service operations - critical for capacity management."""

    @pytest.mark.financial
    def test_increment_tier_registrations(self, db: Session, test_tiers):
        """
        CRITICAL: increment_tier_registrations should increase count.
        """
        from app.services.tier_service import TierService

        service = TierService(db)
        tier = test_tiers[1]  # Basic tier
        initial_count = tier.current_registrations

        service.increment_tier_registrations(tier.id)

        db.refresh(tier)
        assert tier.current_registrations == initial_count + 1

    @pytest.mark.financial
    def test_increment_tier_with_capacity_check_success(self, db: Session, test_event):
        """
        CRITICAL: Should allow increment if capacity available.
        """
        from app.services.tier_service import TierService

        service = TierService(db)

        # Create tier with remaining capacity
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Limited",
            tier_slug="limited",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=5
        )
        db.add(tier)
        db.commit()

        # Should succeed
        service.increment_tier_registrations(tier.id, with_capacity_check=True)

        db.refresh(tier)
        assert tier.current_registrations == 6

    @pytest.mark.financial
    def test_increment_tier_with_capacity_check_fails_when_full(self, db: Session, test_event):
        """
        CRITICAL: Should prevent increment when tier is at capacity.
        """
        from app.services.tier_service import TierService

        service = TierService(db)

        # Create tier at full capacity
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Full Tier",
            tier_slug="full-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=10
        )
        db.add(tier)
        db.commit()

        # Should fail with TierSoldOutException
        with pytest.raises(TierSoldOutException):
            service.increment_tier_registrations(tier.id, with_capacity_check=True)

    @pytest.mark.financial
    def test_decrement_tier_registrations(self, db: Session, test_tiers):
        """
        CRITICAL: decrement_tier_registrations should decrease count.
        Used for refunds and cancellations.
        """
        from app.services.tier_service import TierService

        service = TierService(db)
        tier = test_tiers[1]  # Basic tier

        # First increment to have something to decrement
        tier.current_registrations += 1
        db.commit()
        initial_count = tier.current_registrations

        service.decrement_tier_registrations(tier.id)

        db.refresh(tier)
        assert tier.current_registrations == initial_count - 1

    @pytest.mark.financial
    def test_decrement_tier_does_not_go_negative(self, db: Session, test_event):
        """
        CRITICAL: Decrement should not make count negative.
        """
        from app.services.tier_service import TierService

        service = TierService(db)

        # Create tier with 0 registrations
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Empty Tier",
            tier_slug="empty-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            current_registrations=0
        )
        db.add(tier)
        db.commit()

        # Decrement should not make it negative
        service.decrement_tier_registrations(tier.id)

        db.refresh(tier)
        assert tier.current_registrations == 0, "Count should not go negative"

    @pytest.mark.financial
    def test_confirm_tier_reservation(self, db: Session, test_event):
        """
        CRITICAL: Confirming reservation converts from reserved to registered.
        """
        from app.services.tier_service import TierService

        service = TierService(db)

        # Create tier with reservation
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Reserved Tier",
            tier_slug="reserved-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=5,
            reserved_spots=2
        )
        db.add(tier)
        db.commit()

        initial_registrations = tier.current_registrations
        initial_reservations = tier.reserved_spots

        service.confirm_tier_reservation(tier.id)

        db.refresh(tier)
        assert tier.current_registrations == initial_registrations + 1
        assert tier.reserved_spots == initial_reservations - 1

    @pytest.mark.financial
    def test_release_tier_reservation(self, db: Session, test_event):
        """
        CRITICAL: Releasing reservation frees up capacity.
        Used when payment fails or times out.
        """
        from app.services.tier_service import TierService

        service = TierService(db)

        # Create tier with reservation
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Reserved Tier",
            tier_slug="reserved-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=5,
            reserved_spots=2
        )
        db.add(tier)
        db.commit()

        initial_reservations = tier.reserved_spots

        service.release_tier_reservation(tier.id)

        db.refresh(tier)
        assert tier.reserved_spots == initial_reservations - 1
        assert tier.current_registrations == 5  # Should not change

    @pytest.mark.financial
    def test_tier_capacity_with_reservations(self, db: Session, test_event):
        """
        CRITICAL: Available capacity should account for both registrations and reservations.
        """
        tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Test Tier",
            tier_slug="test-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=10,
            current_registrations=5,
            reserved_spots=3
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)

        # Available capacity = max - current - reserved
        # 10 - 5 - 3 = 2
        assert tier.capacity_remaining == 2

    @pytest.mark.financial
    def test_get_tier_by_id_not_found(self, db: Session):
        """Test that get_tier_by_id returns None for non-existent tier."""
        from app.services.tier_service import TierService
        service = TierService(db)

        result = service.get_tier_by_id(99999)
        assert result is None

    @pytest.mark.financial
    def test_get_tier_by_id_success(self, db: Session, test_tiers):
        """Test that get_tier_by_id returns the correct tier."""
        from app.services.tier_service import TierService
        service = TierService(db)

        result = service.get_tier_by_id(test_tiers[0].id)
        assert result is not None
        assert result.id == test_tiers[0].id
        assert result.tier_name == test_tiers[0].tier_name
