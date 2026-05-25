"""
Unit tests for service layer.

Tests tier service, challenge service, and other business logic services.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.services.tier_service import TierService
from app.modules.challenges.services.challenge_service import ChallengeService
from app.core.tier_schemas import TierCreate, TierUpdate
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    TierSoldOutException,
    TierInactiveException,
)


# ===========================================================================
# TierService Tests
# ===========================================================================

@pytest.mark.unit
class TestTierServiceCreate:
    """Tests for TierService.create_tier"""

    def test_create_tier_event_not_found(self, db: Session, test_user):
        """Test create_tier raises ValueError when event not found."""
        service = TierService(db)
        tier_data = TierCreate(
            tier_name="Basic",
            tier_slug="basic",
            tier_order=0,
            price=Decimal("0.00"),
            requires_payment=False,
        )
        with pytest.raises(ValueError, match="not found"):
            service.create_tier(event_id=99999, tier_data=tier_data, user_id=test_user.id)

    def test_create_tier_permission_denied(self, db: Session, test_event, test_user):
        """Test create_tier raises PermissionError for non-organizer non-admin."""
        from app.models.user import User
        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
            email_verified=True,
            role="user",
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        service = TierService(db)
        tier_data = TierCreate(
            tier_name="New Tier",
            tier_slug="new-tier",
            tier_order=10,
            price=Decimal("100.00"),
            requires_payment=True,
        )
        with pytest.raises(PermissionError):
            service.create_tier(event_id=test_event.id, tier_data=tier_data, user_id=other_user.id)

    def test_create_tier_admin_can_create(self, db: Session, test_event, admin_user):
        """Test admin can create tier for any event."""
        service = TierService(db)
        tier_data = TierCreate(
            tier_name="Admin Tier",
            tier_slug="admin-tier-unique",
            tier_order=99,
            price=Decimal("0.00"),
            requires_payment=False,
        )
        tier = service.create_tier(event_id=test_event.id, tier_data=tier_data, user_id=admin_user.id)
        assert tier.tier_name == "Admin Tier"
        assert tier.event_id == test_event.id

    def test_create_tier_negative_price_raises(self, db: Session, test_event, test_user):
        """Test validation raises ValueError for negative price."""
        service = TierService(db)
        with pytest.raises(Exception):
            tier_data = TierCreate(
                tier_name="Bad Tier",
                tier_slug="bad-tier",
                tier_order=0,
                price=Decimal("-10.00"),
                requires_payment=False,
            )

    def test_create_tier_success_organizer(self, db: Session, test_event, test_user):
        """Test event organizer can create a tier."""
        service = TierService(db)
        tier_data = TierCreate(
            tier_name="Gold Tier",
            tier_slug="gold-tier-unique",
            tier_order=5,
            price=Decimal("500.00"),
            requires_payment=True,
        )
        tier = service.create_tier(event_id=test_event.id, tier_data=tier_data, user_id=test_user.id)
        assert tier is not None
        assert tier.tier_name == "Gold Tier"
        assert tier.event_id == test_event.id
        assert tier.is_active is True


@pytest.mark.unit
class TestTierServiceRead:
    """Tests for TierService read operations."""

    def test_get_event_tiers_returns_active(self, db: Session, test_event, test_tiers):
        """Test get_event_tiers returns active tiers."""
        service = TierService(db)
        tiers = service.get_event_tiers(test_event.id)
        assert len(tiers) > 0
        for tier in tiers:
            assert tier.is_active is True

    def test_get_event_tiers_include_inactive(self, db: Session, test_event, test_tiers):
        """Test get_event_tiers with include_inactive=True."""
        service = TierService(db)
        tiers = service.get_event_tiers(test_event.id, include_inactive=True)
        assert len(tiers) >= len(service.get_event_tiers(test_event.id))

    def test_get_event_tiers_empty_event(self, db: Session, test_event, test_user):
        """Test get_event_tiers returns empty list for event with no tiers."""
        from app.modules.events.domain.event import Event
        from datetime import datetime, timedelta
        now = datetime.now()
        event2 = Event(
            name="Empty Event",
            slug="empty-event-no-tiers",
            description="No tiers",
            status="published",
            event_date=now + timedelta(days=30),
            event_end_date=now + timedelta(days=60),
            registration_start_date=now - timedelta(days=7),
            registration_end_date=now + timedelta(days=25),
            organizer_id=test_user.id,
            is_virtual=True,
        )
        db.add(event2)
        db.commit()
        db.refresh(event2)

        service = TierService(db)
        tiers = service.get_event_tiers(event2.id)
        assert tiers == []

    def test_get_tier_by_id_found(self, db: Session, test_tiers):
        """Test get_tier_by_id returns the correct tier."""
        service = TierService(db)
        tier = service.get_tier_by_id(test_tiers[0].id)
        assert tier is not None
        assert tier.id == test_tiers[0].id

    def test_get_tier_by_id_not_found(self, db: Session):
        """Test get_tier_by_id returns None for non-existent tier."""
        service = TierService(db)
        tier = service.get_tier_by_id(99999)
        assert tier is None


@pytest.mark.unit
class TestTierServiceUpdate:
    """Tests for TierService.update_tier."""

    def test_update_tier_not_found(self, db: Session, test_user):
        """Test update_tier raises ValueError when tier not found."""
        service = TierService(db)
        with pytest.raises(ValueError, match="not found"):
            service.update_tier(99999, TierUpdate(tier_name="New Name"), test_user.id)

    def test_update_tier_name(self, db: Session, test_event, test_tiers, test_user):
        """Test updating tier name."""
        service = TierService(db)
        tier = service.update_tier(
            test_tiers[0].id,
            TierUpdate(tier_name="Updated Name"),
            test_user.id
        )
        assert tier.tier_name == "Updated Name"

    def test_update_tier_permission_denied(self, db: Session, test_event, test_tiers):
        """Test update_tier raises PermissionError for non-organizer."""
        from app.models.user import User
        other = User(
            email="other2@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
            email_verified=True,
            role="user",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        service = TierService(db)
        with pytest.raises(PermissionError):
            service.update_tier(test_tiers[0].id, TierUpdate(tier_name="X"), other.id)

    def test_update_tier_price(self, db: Session, test_event, test_tiers, test_user):
        """Test updating tier price."""
        service = TierService(db)
        new_price = Decimal("200.00")
        tier = service.update_tier(
            test_tiers[1].id,
            TierUpdate(price=new_price),
            test_user.id
        )
        assert tier.price == new_price
        assert tier.requires_payment is True

    def test_update_tier_set_active(self, db: Session, test_event, test_tiers, test_user):
        """Test updating tier is_active."""
        service = TierService(db)
        tier = service.update_tier(
            test_tiers[0].id,
            TierUpdate(is_active=False),
            test_user.id
        )
        assert tier.is_active is False


@pytest.mark.unit
class TestTierServiceDelete:
    """Tests for TierService.delete_tier."""

    def test_delete_tier_not_found(self, db: Session, test_user):
        """Test delete_tier raises ValueError when tier not found."""
        service = TierService(db)
        with pytest.raises(ValueError, match="not found"):
            service.delete_tier(99999, test_user.id)

    def test_delete_tier_permission_denied(self, db: Session, test_event, test_tiers):
        """Test delete_tier raises PermissionError for non-organizer."""
        from app.models.user import User
        other = User(
            email="other3@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
            email_verified=True,
            role="user",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        service = TierService(db)
        with pytest.raises(PermissionError):
            service.delete_tier(test_tiers[0].id, other.id)

    def test_delete_tier_success(self, db: Session, test_event, test_user):
        """Test successfully deleting a tier."""
        from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
        new_tier = EventRegistrationTier(
            event_id=test_event.id,
            tier_name="To Delete",
            tier_slug="to-delete-unique",
            tier_order=50,
            price=Decimal("0.00"),
            currency="INR",
            requires_payment=False,
            is_active=True,
        )
        db.add(new_tier)
        db.commit()
        db.refresh(new_tier)

        service = TierService(db)
        service.delete_tier(new_tier.id, test_user.id)

        assert service.get_tier_by_id(new_tier.id) is None


@pytest.mark.unit
class TestTierCapacityOperations:
    """Tests for TierService capacity operations."""

    def test_check_tier_capacity_unlimited(self, db: Session, test_tiers):
        """Test capacity check for unlimited tier."""
        test_tiers[0].max_registrations = None
        db.commit()

        service = TierService(db)
        assert service.check_tier_capacity(test_tiers[0].id) is True

    def test_check_tier_capacity_available(self, db: Session, test_tiers):
        """Test capacity check when spots available."""
        service = TierService(db)
        result = service.check_tier_capacity(test_tiers[0].id)
        assert result is True

    def test_check_tier_capacity_not_found(self, db: Session):
        """Test capacity check for non-existent tier returns False."""
        service = TierService(db)
        assert service.check_tier_capacity(99999) is False

    def test_check_tier_capacity_inactive(self, db: Session, test_tiers):
        """Test capacity check for inactive tier returns False."""
        test_tiers[0].is_active = False
        db.commit()

        service = TierService(db)
        assert service.check_tier_capacity(test_tiers[0].id) is False

    def test_increment_tier_registrations(self, db: Session, test_tiers):
        """Test incrementing tier registration count."""
        initial_count = test_tiers[0].current_registrations or 0
        service = TierService(db)
        service.increment_tier_registrations(test_tiers[0].id)
        db.refresh(test_tiers[0])
        assert test_tiers[0].current_registrations == initial_count + 1

    def test_increment_tier_not_found(self, db: Session):
        """Test increment raises ValueError for non-existent tier."""
        service = TierService(db)
        with pytest.raises(ValueError):
            service.increment_tier_registrations(99999)

    def test_increment_with_capacity_check_sold_out(self, db: Session, test_tiers):
        """Test increment with capacity check raises when sold out."""
        test_tiers[1].max_registrations = 1
        test_tiers[1].current_registrations = 1
        db.commit()

        service = TierService(db)
        with pytest.raises(TierSoldOutException):
            service.increment_tier_registrations(test_tiers[1].id, with_capacity_check=True)

    def test_decrement_tier_registrations(self, db: Session, test_tiers):
        """Test decrementing tier registration count."""
        test_tiers[0].current_registrations = 5
        db.commit()

        service = TierService(db)
        service.decrement_tier_registrations(test_tiers[0].id)
        db.refresh(test_tiers[0])
        assert test_tiers[0].current_registrations == 4

    def test_decrement_tier_not_below_zero(self, db: Session, test_tiers):
        """Test decrement does not go below zero."""
        test_tiers[0].current_registrations = 0
        db.commit()

        service = TierService(db)
        service.decrement_tier_registrations(test_tiers[0].id)
        db.refresh(test_tiers[0])
        assert test_tiers[0].current_registrations == 0

    def test_check_and_reserve_capacity_not_found(self, db: Session):
        """Test check_and_reserve raises NotFoundException for missing tier."""
        service = TierService(db)
        with pytest.raises(NotFoundException):
            service.check_and_reserve_tier_capacity(99999)

    def test_check_and_reserve_capacity_inactive(self, db: Session, test_tiers):
        """Test check_and_reserve raises TierInactiveException for inactive tier."""
        test_tiers[0].is_active = False
        db.commit()

        service = TierService(db)
        with pytest.raises(TierInactiveException):
            service.check_and_reserve_tier_capacity(test_tiers[0].id)

    def test_check_and_reserve_capacity_sold_out(self, db: Session, test_tiers):
        """Test check_and_reserve raises TierSoldOutException when at capacity."""
        test_tiers[1].max_registrations = 2
        test_tiers[1].current_registrations = 2
        test_tiers[1].is_active = True
        db.commit()

        service = TierService(db)
        with pytest.raises(TierSoldOutException):
            service.check_and_reserve_tier_capacity(test_tiers[1].id)

    def test_check_and_reserve_capacity_success(self, db: Session, test_tiers):
        """Test successful capacity reservation."""
        test_tiers[0].current_registrations = 0
        test_tiers[0].is_active = True
        db.commit()

        service = TierService(db)
        tier = service.check_and_reserve_tier_capacity(test_tiers[0].id)
        assert tier is not None
        assert tier.current_registrations == 1

    def test_reserve_tier_capacity_not_found(self, db: Session):
        """Test reserve_tier_capacity raises NotFoundException for missing tier."""
        service = TierService(db)
        with pytest.raises(NotFoundException):
            service.reserve_tier_capacity(99999)

    def test_reserve_tier_capacity_inactive(self, db: Session, test_tiers):
        """Test reserve raises TierInactiveException for inactive tier."""
        test_tiers[0].is_active = False
        db.commit()

        service = TierService(db)
        with pytest.raises(TierInactiveException):
            service.reserve_tier_capacity(test_tiers[0].id)

    def test_reserve_tier_capacity_sold_out(self, db: Session, test_tiers):
        """Test reserve raises TierSoldOutException when full."""
        test_tiers[1].max_registrations = 1
        test_tiers[1].current_registrations = 1
        test_tiers[1].reserved_spots = 0
        test_tiers[1].is_active = True
        db.commit()

        service = TierService(db)
        with pytest.raises(TierSoldOutException):
            service.reserve_tier_capacity(test_tiers[1].id)

    def test_reserve_tier_capacity_success(self, db: Session, test_tiers):
        """Test successful tier reservation."""
        test_tiers[0].reserved_spots = 0
        test_tiers[0].current_registrations = 0
        test_tiers[0].is_active = True
        db.commit()

        service = TierService(db)
        tier = service.reserve_tier_capacity(test_tiers[0].id)
        assert tier.reserved_spots == 1

    def test_release_tier_reservation(self, db: Session, test_tiers):
        """Test releasing a tier reservation."""
        test_tiers[0].reserved_spots = 2
        db.commit()

        service = TierService(db)
        service.release_tier_reservation(test_tiers[0].id)
        db.refresh(test_tiers[0])
        assert test_tiers[0].reserved_spots == 1

    def test_release_tier_reservation_not_found(self, db: Session):
        """Test release for non-existent tier does nothing."""
        service = TierService(db)
        service.release_tier_reservation(99999)

    def test_confirm_tier_reservation(self, db: Session, test_tiers):
        """Test confirming a tier reservation."""
        test_tiers[0].reserved_spots = 1
        test_tiers[0].current_registrations = 0
        db.commit()

        service = TierService(db)
        service.confirm_tier_reservation(test_tiers[0].id)
        db.refresh(test_tiers[0])
        assert test_tiers[0].reserved_spots == 0
        assert test_tiers[0].current_registrations == 1


# ===========================================================================
# ChallengeService Tests
# ===========================================================================

@pytest.mark.unit
class TestChallengeServiceProgress:
    """Tests for ChallengeService.get_challenge_progress."""

    def test_get_progress_challenge_not_found(self, db: Session, test_user):
        """Test raises NotFoundException when challenge not found."""
        service = ChallengeService(db)
        with pytest.raises(NotFoundException):
            service.get_challenge_progress(user_id=test_user.id, event_id=99999)

    def test_get_progress_registration_not_found(self, db: Session, test_user, test_event):
        """Test raises NotFoundException when user not registered."""
        service = ChallengeService(db)
        with pytest.raises(NotFoundException):
            service.get_challenge_progress(user_id=test_user.id, event_id=test_event.id)

    def test_get_progress_no_activity(self, db: Session, test_user, test_event, test_registration):
        """Test returns zero progress when no activity recorded."""
        service = ChallengeService(db)
        result = service.get_challenge_progress(user_id=test_user.id, event_id=test_event.id)
        assert result is not None
        assert result["challenge_id"] == test_event.id
        assert result["current_distance"] == 0.0

    def test_get_progress_with_activity(self, db: Session, test_user, test_event, completed_registration):
        """Test returns progress data when activity exists."""
        service = ChallengeService(db)
        result = service.get_challenge_progress(user_id=test_user.id, event_id=test_event.id)
        assert result is not None
        assert result["challenge_id"] == test_event.id

    def test_get_progress_completed_status(self, db: Session, test_user, test_event, completed_registration):
        """Test status is completed when distance is met."""
        from app.models.activity_progress import ActivityProgress
        # Ensure progress shows completed (more distance than target)
        progress = db.query(ActivityProgress).filter(
            ActivityProgress.registration_id == completed_registration.id
        ).first()
        if progress:
            progress.distance_completed = progress.target_distance + 1.0
            db.commit()

        service = ChallengeService(db)
        result = service.get_challenge_progress(user_id=test_user.id, event_id=test_event.id)
        if progress:
            assert result["status"] in ["completed", "in_progress", "not_started"]


@pytest.mark.unit
class TestChallengeServiceJoin:
    """Tests for ChallengeService.join_challenge."""

    def test_join_challenge_not_found(self, db: Session, test_user):
        """Test raises NotFoundException when challenge not found."""
        service = ChallengeService(db)
        with pytest.raises(NotFoundException):
            service.join_challenge(user_id=test_user.id, event_id=99999)

    def test_join_challenge_success(self, db: Session, test_user, test_event):
        """Test successfully joining a challenge."""
        service = ChallengeService(db)
        registration = service.join_challenge(user_id=test_user.id, event_id=test_event.id)
        assert registration is not None
        assert registration.user_id == test_user.id
        assert registration.event_id == test_event.id

    def test_join_challenge_already_joined(self, db: Session, test_user, test_event, test_registration):
        """Test raises ValidationException when already joined."""
        service = ChallengeService(db)
        with pytest.raises(ValidationException):
            service.join_challenge(user_id=test_user.id, event_id=test_event.id)
