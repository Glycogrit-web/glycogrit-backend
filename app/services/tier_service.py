"""
Tier Service - Business logic for event registration tiers
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.event import Event
from app.models.user import User
from app.models.event_registration_tier import EventRegistrationTier
from app.models.registration_tier import RegistrationTier
from app.schemas.tier import TierCreate, TierUpdate


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

    def increment_tier_registrations(self, tier_id: int):
        """
        Increment current_registrations count for a tier.

        Args:
            tier_id: Tier ID
        """
        tier = self.get_tier_by_id(tier_id)
        if tier:
            tier.current_registrations += 1
            self.db.commit()

    def decrement_tier_registrations(self, tier_id: int):
        """
        Decrement current_registrations count for a tier.

        Args:
            tier_id: Tier ID
        """
        tier = self.get_tier_by_id(tier_id)
        if tier and tier.current_registrations > 0:
            tier.current_registrations -= 1
            self.db.commit()

    def check_tier_capacity(self, tier_id: int) -> bool:
        """
        Check if tier has capacity for new registrations.

        Args:
            tier_id: Tier ID

        Returns:
            bool: True if capacity available, False if sold out
        """
        tier = self.get_tier_by_id(tier_id)
        if not tier:
            return False

        if not tier.is_active:
            return False

        if tier.max_registrations is None:
            return True  # Unlimited capacity

        return tier.current_registrations < tier.max_registrations
