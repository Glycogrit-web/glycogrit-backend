"""
Tier Service - Business logic for event registration tiers
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.modules.events.domain.event import Event
from app.models.user import User
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration_tier import RegistrationTier
from app.core.tier_schemas import TierCreate, TierUpdate


class TierService:
    """Service for managing event registration tiers"""

    def __init__(self, db: Session):
        self.db = db

    def create_tier(self, event_id: int, tier_data: TierCreate, user_id: int) -> EventRegistrationTier:
        """
        Create a new registration tier for an event.

        Args:
            event_id: Event ID
            tier_data: Tier creation data
            user_id: User ID (must be event organizer)

        Returns:
            EventRegistrationTier: Created tier

        Raises:
            PermissionError: If user is not event organizer
            ValueError: If event not found or validation fails
            IntegrityError: If duplicate slug or order
        """
        # Check event exists and user has permission
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event with ID {event_id} not found")

        # Get user to check if they're admin
        user = self.db.query(User).filter(User.id == user_id).first()
        is_admin = user and user.role in ['admin', 'super_admin']

        # Allow event organizer OR admins
        if event.organizer_id != user_id and not is_admin:
            raise PermissionError("Only event organizer or admin can create tiers")

        # Validate tier data
        self._validate_tier_data(tier_data)

        # Create tier
        tier = EventRegistrationTier(
            event_id=event_id,
            tier_name=tier_data.tier_name,
            tier_slug=tier_data.tier_slug,
            tier_order=tier_data.tier_order,
            description=tier_data.description,
            price=tier_data.price,
            currency=tier_data.currency,
            requires_payment=tier_data.requires_payment,
            max_registrations=tier_data.max_registrations,
            rewards=tier_data.rewards,
            is_active=True
        )

        self.db.add(tier)
        self.db.commit()
        self.db.refresh(tier)

        return tier

    def get_event_tiers(self, event_id: int, include_inactive: bool = False) -> List[EventRegistrationTier]:
        """
        Get all tiers for an event.

        Args:
            event_id: Event ID
            include_inactive: Include inactive tiers

        Returns:
            List[EventRegistrationTier]: List of tiers ordered by tier_order
        """
        query = self.db.query(EventRegistrationTier).filter(
            EventRegistrationTier.event_id == event_id
        )

        if not include_inactive:
            query = query.filter(EventRegistrationTier.is_active == True)

        return query.order_by(EventRegistrationTier.tier_order).all()

    def get_tier_by_id(self, tier_id: int) -> Optional[EventRegistrationTier]:
        """
        Get tier by ID.

        Args:
            tier_id: Tier ID

        Returns:
            EventRegistrationTier or None
        """
        return self.db.query(EventRegistrationTier).filter(
            EventRegistrationTier.id == tier_id
        ).first()

    def update_tier(self, tier_id: int, tier_data: TierUpdate, user_id: int) -> EventRegistrationTier:
        """
        Update a tier.

        Args:
            tier_id: Tier ID
            tier_data: Updated tier data
            user_id: User ID (must be event organizer)

        Returns:
            EventRegistrationTier: Updated tier

        Raises:
            PermissionError: If user is not event organizer
            ValueError: If tier not found or validation fails
        """
        tier = self.get_tier_by_id(tier_id)
        if not tier:
            raise ValueError(f"Tier with ID {tier_id} not found")

        # Check permission
        event = self.db.query(Event).filter(Event.id == tier.event_id).first()

        # Get user to check if they're admin
        user = self.db.query(User).filter(User.id == user_id).first()
        is_admin = user and user.role in ['admin', 'super_admin']

        # Allow event organizer OR admins
        if event.organizer_id != user_id and not is_admin:
            raise PermissionError("Only event organizer or admin can update tiers")

        # Check if tier has registrations (some fields cannot be changed)
        has_registrations = self.db.query(RegistrationTier).filter(
            RegistrationTier.tier_id == tier_id
        ).first() is not None

        if has_registrations and tier_data.price is not None:
            # Cannot reduce price if registrations exist
            if tier_data.price < tier.price:
                raise ValueError("Cannot reduce tier price when registrations exist")

        # Update fields
        if tier_data.tier_name is not None:
            tier.tier_name = tier_data.tier_name

        if tier_data.description is not None:
            tier.description = tier_data.description

        if tier_data.price is not None:
            tier.price = tier_data.price
            # Auto-update requires_payment based on price
            tier.requires_payment = tier_data.price > 0

        if tier_data.is_active is not None:
            tier.is_active = tier_data.is_active

        if tier_data.max_registrations is not None:
            # Cannot set below current registrations
            if tier_data.max_registrations < tier.current_registrations:
                raise ValueError("Cannot set max_registrations below current registration count")
            tier.max_registrations = tier_data.max_registrations

        if tier_data.rewards is not None:
            tier.rewards = tier_data.rewards

        self.db.commit()
        self.db.refresh(tier)

        return tier

    def delete_tier(self, tier_id: int, user_id: int):
        """
        Delete a tier.

        Args:
            tier_id: Tier ID
            user_id: User ID (must be event organizer)

        Raises:
            PermissionError: If user is not event organizer
            ValueError: If tier not found or has registrations
        """
        tier = self.get_tier_by_id(tier_id)
        if not tier:
            raise ValueError(f"Tier with ID {tier_id} not found")

        # Check permission
        event = self.db.query(Event).filter(Event.id == tier.event_id).first()

        # Get user to check if they're admin
        user = self.db.query(User).filter(User.id == user_id).first()
        is_admin = user and user.role in ['admin', 'super_admin']

        # Allow event organizer OR admins
        if event.organizer_id != user_id and not is_admin:
            raise PermissionError("Only event organizer or admin can delete tiers")

        # Check if tier has registrations
        has_registrations = self.db.query(RegistrationTier).filter(
            RegistrationTier.tier_id == tier_id
        ).first() is not None

        if has_registrations:
            raise ValueError("Cannot delete tier with existing registrations")

        # Check if this is the default tier
        if event.default_tier_id == tier_id:
            raise ValueError("Cannot delete default tier. Set a new default tier first.")

        self.db.delete(tier)
        self.db.commit()

    def _validate_tier_data(self, tier_data: TierCreate):
        """
        Validate tier creation data.

        Args:
            tier_data: Tier data to validate

        Raises:
            ValueError: If validation fails
        """
        # Ensure price >= 0
        if tier_data.price < 0:
            raise ValueError("Price cannot be negative")

        # If price is 0, requires_payment must be False
        if tier_data.price == 0 and tier_data.requires_payment:
            raise ValueError("Free tiers (price=0) cannot require payment")

        # Ensure tier_order >= 0
        if tier_data.tier_order < 0:
            raise ValueError("Tier order cannot be negative")

    def increment_tier_registrations(self, tier_id: int, with_capacity_check: bool = False):
        """
        Increment current_registrations count for a tier.

        Uses atomic database update to prevent race conditions.

        Args:
            tier_id: Tier ID
            with_capacity_check: If True, raises exception if capacity exceeded

        Raises:
            ValueError: If tier not found
            TierSoldOutException: If with_capacity_check=True and capacity exceeded
        """
        from sqlalchemy import update
        from app.core.exceptions import TierSoldOutException

        # Use atomic update with pessimistic locking
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if not tier:
            raise ValueError(f"Tier {tier_id} not found")

        # Check capacity if requested
        if with_capacity_check:
            if tier.max_registrations is not None:
                if tier.current_registrations >= tier.max_registrations:
                    raise TierSoldOutException(
                        tier_id=tier.id,
                        tier_name=tier.tier_name,
                        current_count=tier.current_registrations,
                        max_capacity=tier.max_registrations
                    )

        # Atomic increment
        tier.current_registrations += 1
        self.db.commit()

    def decrement_tier_registrations(self, tier_id: int):
        """
        Decrement current_registrations count for a tier.

        Uses atomic database update to prevent race conditions.

        Args:
            tier_id: Tier ID
        """
        # Use atomic update with pessimistic locking
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if tier and tier.current_registrations > 0:
            tier.current_registrations -= 1
            self.db.commit()

    def check_tier_capacity(self, tier_id: int) -> bool:
        """
        Check if tier has capacity for new registrations.

        NOTE: This method has a TOCTOU (Time-of-Check-Time-of-Use) race condition.
        For reliable capacity checking, use check_and_reserve_tier_capacity() instead.

        Args:
            tier_id: Tier ID

        Returns:
            bool: True if capacity available, False if sold out

        Deprecated: Use check_and_reserve_tier_capacity() for atomic check+reserve
        """
        tier = self.get_tier_by_id(tier_id)
        if not tier:
            return False

        if not tier.is_active:
            return False

        if tier.max_registrations is None:
            return True  # Unlimited capacity

        return tier.current_registrations < tier.max_registrations

    def check_and_reserve_tier_capacity(self, tier_id: int) -> EventRegistrationTier:
        """
        Atomically check tier capacity and reserve a spot (increment count).

        This method uses SELECT FOR UPDATE to prevent race conditions.
        If capacity is available, it increments the count in the same transaction.

        Args:
            tier_id: Tier ID

        Returns:
            EventRegistrationTier: The tier with reserved spot

        Raises:
            NotFoundException: If tier not found
            TierInactiveException: If tier is not active
            TierSoldOutException: If tier is at max capacity
        """
        from app.core.exceptions import (
            NotFoundException,
            TierInactiveException,
            TierSoldOutException
        )

        # Acquire pessimistic lock on tier row
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if not tier:
            raise NotFoundException("Tier", tier_id)

        if not tier.is_active:
            raise TierInactiveException(tier_id=tier.id, tier_name=tier.tier_name)

        # Check capacity (with lock held, safe from race conditions)
        if tier.max_registrations is not None:
            if tier.current_registrations >= tier.max_registrations:
                raise TierSoldOutException(
                    tier_id=tier.id,
                    tier_name=tier.tier_name,
                    current_count=tier.current_registrations,
                    max_capacity=tier.max_registrations
                )

        # Reserve spot (increment count)
        tier.current_registrations += 1
        # Note: Don't commit here - caller should commit after creating registration
        self.db.flush()  # Flush to detect constraint violations

        return tier

    def reserve_tier_capacity(self, tier_id: int) -> EventRegistrationTier:
        """
        Reserve a spot in a tier before payment processing.

        This is a critical security fix to prevent race conditions where:
        1. User initiates tier upgrade
        2. Payment order is created
        3. During payment flow, tier fills up
        4. User completes payment but tier is now full

        By reserving capacity BEFORE payment, we ensure the spot is held
        during the payment process.

        Args:
            tier_id: Tier ID to reserve capacity in

        Returns:
            EventRegistrationTier: The tier with reserved spot

        Raises:
            NotFoundException: If tier not found
            TierInactiveException: If tier is not active
            TierSoldOutException: If tier is at max capacity (including reservations)
        """
        from app.core.exceptions import (
            NotFoundException,
            TierInactiveException,
            TierSoldOutException
        )

        # Acquire pessimistic lock on tier row
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if not tier:
            raise NotFoundException("Tier", tier_id)

        if not tier.is_active:
            raise TierInactiveException(tier_id=tier.id, tier_name=tier.tier_name)

        # Check capacity INCLUDING reserved spots (with lock held, safe from race conditions)
        if tier.max_registrations is not None:
            total_used = tier.current_registrations + tier.reserved_spots
            if total_used >= tier.max_registrations:
                raise TierSoldOutException(
                    tier_id=tier.id,
                    tier_name=tier.tier_name,
                    current_count=total_used,
                    max_capacity=tier.max_registrations
                )

        # Reserve spot by incrementing reserved_spots
        tier.reserved_spots += 1
        self.db.flush()  # Flush to detect constraint violations

        return tier

    def release_tier_reservation(self, tier_id: int) -> None:
        """
        Release a reserved spot in a tier (on payment failure/expiry).

        This decrements the reserved_spots count, freeing up the capacity
        for other users.

        Args:
            tier_id: Tier ID to release reservation from
        """
        # Acquire pessimistic lock
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if tier and tier.reserved_spots > 0:
            tier.reserved_spots -= 1
            self.db.flush()

    def confirm_tier_reservation(self, tier_id: int) -> None:
        """
        Convert a tier reservation to a confirmed registration.

        This is called after successful payment verification.
        It decrements reserved_spots and increments current_registrations atomically.

        Args:
            tier_id: Tier ID to confirm reservation for
        """
        # Acquire pessimistic lock
        tier = self.db.query(EventRegistrationTier).with_for_update().filter(
            EventRegistrationTier.id == tier_id
        ).first()

        if tier:
            # Move from reservation to confirmed
            if tier.reserved_spots > 0:
                tier.reserved_spots -= 1
            tier.current_registrations += 1
            self.db.flush()
