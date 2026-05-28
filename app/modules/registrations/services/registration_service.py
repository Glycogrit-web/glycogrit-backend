"""
Registration service for business logic.
"""

import logging
import secrets
import string
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.enums import RegistrationStatus
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.permissions import PermissionChecker
from app.models.activity_progress import ActivityProgress
from app.models.user import User
from app.modules.events.domain.event import EventActivity
from app.modules.events.repositories.event_repository import EventRepository
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration import Registration
from app.modules.registrations.domain.registration_tier import RegistrationTier
from app.modules.registrations.repositories.registration_repository import RegistrationRepository
from app.services.base import BaseService
from app.modules.registrations.services.tier_service import TierService

logger = logging.getLogger(__name__)


class RegistrationService(BaseService):
    """Service for registration-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the RegistrationService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = RegistrationRepository(db)
        self.event_repository = EventRepository(db)

    def _generate_registration_number(self, event_id: int, max_attempts: int = 10) -> str:
        """
        Generate a unique registration number with retry limit.

        Args:
            event_id: Event ID
            max_attempts: Maximum number of generation attempts (default: 10)

        Returns:
            Unique registration number

        Raises:
            ValidationException: If unable to generate unique number after max_attempts
        """
        for attempt in range(max_attempts):
            # Generate format: EVT{event_id}-{random_6_chars}
            random_suffix = "".join(
                secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
            )
            reg_number = f"EVT{event_id}-{random_suffix}"

            if not self.repository.registration_number_exists(reg_number):
                return reg_number

            logger.warning(
                f"Registration number {reg_number} already exists, retry {attempt + 1}/{max_attempts}"
            )

        # If we reach here, all attempts failed
        raise ValidationException(
            f"Unable to generate unique registration number after {max_attempts} attempts. Please try again.",
            "registration_number_generation_failed",
        )

    def _update_user_profile_from_registration(
        self,
        user_id: int,
        age: int | None = None,
        gender: str | None = None,
        t_shirt_size: str | None = None,
    ) -> None:
        """
        Update user profile with registration data for future auto-fill.

        Only updates fields that are provided and not already set in the profile,
        or updates them if new values are provided during registration.

        Args:
            user_id: User ID
            age: Optional age
            gender: Optional gender
            t_shirt_size: Optional t-shirt size
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for profile update")
                return

            # Update fields if provided
            updated = False
            if age is not None and user.age != age:
                user.age = age
                updated = True
            if gender is not None and user.gender != gender:
                user.gender = gender
                updated = True
            if t_shirt_size is not None and user.t_shirt_size != t_shirt_size:
                user.t_shirt_size = t_shirt_size
                updated = True

            if updated:
                self.db.commit()
                logger.info(f"Updated user {user_id} profile from registration data")
        except Exception as e:
            logger.error(f"Failed to update user profile from registration: {e}")
            # Don't fail the registration if profile update fails
            self.db.rollback()

    def register_for_event(
        self,
        event_id: int,
        user_id: int,
        activity_id: int | None = None,
        participant_name: str = None,
        age: int | None = None,
        gender: str | None = None,
        t_shirt_size: str | None = None,
    ) -> Registration:
        """
        Register a user for an event.

        Args:
            event_id: Event ID
            user_id: User ID
            activity_id: Optional category ID
            participant_name: Participant name
            age: Optional age
            gender: Optional gender
            t_shirt_size: Optional t-shirt size

        Returns:
            Created Registration instance

        Raises:
            NotFoundException: If event not found
            AlreadyExistsException: If user already registered
            ValidationException: If event is full or not open for registration
        """
        from sqlalchemy.exc import IntegrityError

        from app.modules.events.domain.event import Event

        try:
            # CRITICAL FIX: Use row-level locking to prevent race conditions
            # Lock the event row to ensure capacity check and registration creation are atomic
            event = self.db.query(Event).filter(Event.id == event_id).with_for_update().first()
            if not event:
                raise NotFoundException("Event", event_id)

            # Check if event is open for registration with detailed error messages
            if event.status not in ["upcoming", "ongoing", "published"]:
                # Provide user-friendly error message based on status
                error_messages = {
                    "draft": "This event is still in draft and not yet published. Please contact the organizer.",
                    "completed": "This event has already ended and registration is closed.",
                    "cancelled": "This event has been cancelled. Registration is no longer available.",
                }

                error_message = error_messages.get(
                    event.status,
                    f"Event registration is currently not available (status: {event.status})"
                )

                logger.warning(
                    f"Registration blocked for event {event_id} (user {user_id}): status={event.status}"
                )
                raise ValidationException(error_message, "event_status")

            # Check if user is already registered
            # NOTE: get_by_user_and_event now returns LIST (after refactoring)
            existing_registrations = self.repository.get_by_user_and_event(user_id, event_id)

            # UPDATED BEHAVIOR: User can have multiple registrations (one per tier)
            # For non-tier events, block if ANY confirmed registration exists
            if existing_registrations:
                # Check if any registration is confirmed (non-tier events should only have one)
                confirmed_registrations = [r for r in existing_registrations if r.status == RegistrationStatus.CONFIRMED.value]
                if confirmed_registrations:
                    # For non-tier events, this means user is already registered
                    raise AlreadyExistsException(
                        "Registration", "user_event", f"user {user_id} in event {event_id}"
                    )

                # Check if there's a pending registration we can reuse
                pending_registrations = [r for r in existing_registrations if r.status == RegistrationStatus.PENDING.value]
                if pending_registrations:
                    # Return the most recent pending registration for payment recovery
                    existing = pending_registrations[0]  # Already ordered by registered_at DESC
                    logger.info(
                        f"Found existing pending registration {existing.id} for user {user_id} in event {event_id}"
                    )
                    return existing

                # Check if there's a cancelled registration we can reactivate
                cancelled_registrations = [r for r in existing_registrations if r.status == RegistrationStatus.CANCELLED.value]
                if cancelled_registrations:
                    # CRITICAL FIX: Reactivate cancelled registration instead of creating new one
                    existing = cancelled_registrations[0]  # Most recent cancelled
                    logger.info(
                        f"User {user_id} has cancelled registration {existing.id}, reactivating"
                    )

                    # Determine new status based on payment requirements
                    new_status = RegistrationStatus.CONFIRMED.value
                    if hasattr(event, "requires_payment") and event.requires_payment:
                        new_status = RegistrationStatus.PENDING.value
                    elif (
                        hasattr(event, "certificate_type") and event.certificate_type == "physical"
                    ):
                        new_status = RegistrationStatus.PENDING.value
                    elif event.registration_fee and event.registration_fee > 0:
                        new_status = RegistrationStatus.PENDING.value

                    # Reactivate registration with updated data
                    self.repository.update(
                        existing.id,
                        {
                            "status": new_status,
                            "event_activity_id": activity_id,
                            "participant_name": participant_name,
                            "age": age,
                            "gender": gender,
                            "t_shirt_size": t_shirt_size,
                        },
                    )

                    # Increment participant count if confirmed (event row still locked)
                    if new_status == RegistrationStatus.CONFIRMED.value:
                        event.current_participants += 1
                        self.db.flush()

                    # Update user profile
                    self._update_user_profile_from_registration(user_id, age, gender, t_shirt_size)

                    # Commit and return reactivated registration
                    self.db.commit()
                    return self.repository.get_by_id(existing.id)

            # Check max participants (now with row lock held)
            if event.max_participants and event.current_participants >= event.max_participants:
                raise ValidationException("Event is full", "max_participants")

            # Generate registration number
            registration_number = self._generate_registration_number(event_id)

            # Determine registration status based on payment requirements
            # For events with medals/physical certificates that require payment,
            # registration stays pending until payment is completed
            registration_status = RegistrationStatus.CONFIRMED.value

            # Check if event requires payment
            # Events with e-certificate only (certificate_type = 'e-certificate') don't require payment
            # Events with physical rewards (medals, physical certificates) require payment
            if hasattr(event, "requires_payment") and event.requires_payment:
                # If event explicitly requires payment, set status to pending
                registration_status = RegistrationStatus.PENDING.value
            elif hasattr(event, "certificate_type") and event.certificate_type == "physical":
                # If certificate is physical, payment is required
                registration_status = RegistrationStatus.PENDING.value
            elif event.registration_fee and event.registration_fee > 0:
                # If there's a registration fee and no explicit certificate type set,
                # assume payment is required for backward compatibility
                registration_status = RegistrationStatus.PENDING.value

            # Create registration
            registration_data = {
                "user_id": user_id,
                "event_id": event_id,
                "event_activity_id": activity_id,
                "registration_number": registration_number,
                "participant_name": participant_name,
                "age": age,
                "gender": gender,
                "t_shirt_size": t_shirt_size,
                "status": registration_status,
            }

            registration = self.repository.create(registration_data)

            # Create ActivityProgress record if activity_id is provided
            if activity_id:
                # Get the activity to fetch its distance
                activity = (
                    self.db.query(EventActivity).filter(EventActivity.id == activity_id).first()
                )
                if activity and activity.distance:
                    activity_progress = ActivityProgress(
                        user_id=user_id,
                        registration_id=registration.id,
                        event_id=event_id,
                        activity_id=activity_id,
                        target_distance=activity.distance,
                        distance_completed=Decimal("0.00"),
                        # progress_percentage and is_completed are hybrid_properties, computed automatically
                    )
                    self.db.add(activity_progress)
                    self.db.commit()
                    logger.info(
                        f"Created ActivityProgress for registration {registration.id} with target distance {activity.distance} km"
                    )

            # CRITICAL FIX: Increment participant count atomically (event row still locked)
            # Only increment if registration is confirmed
            # Pending registrations will increment count after payment completion
            if registration_status == RegistrationStatus.CONFIRMED.value:
                event.current_participants += 1
                self.db.flush()

            # Update user profile with registration data if provided
            # This saves the information for future registrations
            self._update_user_profile_from_registration(user_id, age, gender, t_shirt_size)

            # Commit all changes atomically
            self.db.commit()
            return registration

        except IntegrityError as e:
            # Rollback on database constraint violations (e.g., duplicate registration_number)
            self.db.rollback()
            logger.error(f"Registration failed due to integrity error: {e}")
            raise ValidationException(
                "Registration failed due to database constraint. Please try again."
            )
        except Exception as e:
            # Rollback on any error
            self.db.rollback()
            logger.error(f"Registration failed: {e}")
            raise

    def get_registration_by_id(self, registration_id: int) -> Registration:
        """
        Get a registration by ID.

        Args:
            registration_id: Registration ID

        Returns:
            Registration instance

        Raises:
            NotFoundException: If registration not found
        """
        return self.get_or_404(self.repository, registration_id, "Registration")

    def update_registration(
        self, registration_id: int, update_data: dict[str, Any], current_user_id: int
    ) -> Registration:
        """
        Update a registration.

        Args:
            registration_id: Registration ID
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request

        Returns:
            Updated Registration instance

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        PermissionChecker.require_registration_owner(registration, current_user_id)

        # Don't allow updating certain fields
        protected_fields = ["id", "user_id", "event_id", "registration_number", "registered_at"]
        for field in protected_fields:
            update_data.pop(field, None)

        # Update registration
        updated_registration = self.repository.update(registration_id, update_data)
        return updated_registration

    def cancel_registration(self, registration_id: int, current_user_id: int) -> bool:
        """
        Cancel a registration.

        Args:
            registration_id: Registration ID
            current_user_id: ID of the user making the request

        Returns:
            True if cancelled successfully

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
            ValidationException: If already cancelled
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        PermissionChecker.require_registration_owner(registration, current_user_id)

        # Check if already cancelled
        if registration.status == RegistrationStatus.CANCELLED.value:
            raise ValidationException("Registration is already cancelled", "status")

        # CRITICAL FIX: Check for active payment orders before cancelling
        from app.modules.payments.domain.payment import Payment

        active_payments = (
            self.db.query(Payment)
            .filter(
                Payment.registration_id == registration_id,
                Payment.status.in_(["pending", "created"]),
            )
            .count()
        )

        if active_payments > 0:
            raise ValidationException(
                "Cannot cancel registration with active payment. Please wait for payment to complete or expire.",
                "active_payment",
            )

        # Store current status before update
        was_confirmed = registration.status == RegistrationStatus.CONFIRMED.value

        # Update status to cancelled
        self.repository.update(registration_id, {"status": "cancelled"})

        # CRITICAL FIX: Only decrement counts if registration was previously confirmed
        if was_confirmed:
            # Decrement event participant count
            event = self.event_repository.get_by_id(registration.event_id)
            if event:
                if event.current_participants > 0:
                    self.event_repository.update(
                        registration.event_id,
                        {"current_participants": event.current_participants - 1},
                    )
                else:
                    logger.warning(
                        f"Event {registration.event_id} already has 0 participants, cannot decrement"
                    )

            # CRITICAL FIX: Decrement tier count if using tier system
            if registration.uses_tier_system and registration.current_tier_id:
                tier_service = TierService(self.db)
                tier_service.decrement_tier_registrations(registration.current_tier_id)
                logger.info(
                    f"Decremented tier {registration.current_tier_id} count for cancelled registration"
                )

        return True

    def get_registrations_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Registration]:
        """
        Get all registrations for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return self.repository.get_registrations_by_user(user_id, skip, limit)

    def get_registrations_by_event(
        self, event_id: int, skip: int = 0, limit: int = 100
    ) -> list[Registration]:
        """
        Get all registrations for an event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Registration instances
        """
        return self.repository.get_registrations_by_event(event_id, skip, limit)

    # ===== TIER-BASED REGISTRATION METHODS =====

    def register_for_event_tier(
        self,
        event_id: int,
        tier_id: int,
        user_id: int,
        participant_name: str,
        age: int | None = None,
        gender: str | None = None,
        t_shirt_size: str | None = None,
        activity_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Register a user for a specific event tier.

        Args:
            event_id: Event ID
            tier_id: Tier ID to register for
            user_id: User ID
            participant_name: Participant name
            age: Optional age
            gender: Optional gender
            t_shirt_size: Optional t-shirt size
            activity_id: Optional activity category ID

        Returns:
            Dict with registration details and payment order (if required)

        Raises:
            NotFoundException: If event or tier not found
            AlreadyExistsException: If user already registered
            ValidationException: If tier is sold out, inactive, or validation fails
        """
        # Get event
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event", event_id)

        # Check if event uses tier system
        if not event.uses_tier_system:
            raise ValidationException("Event does not use tier system", "event_tier_system")

        # Get tier
        tier_service = TierService(self.db)
        tier = tier_service.get_tier_by_id(tier_id)
        if not tier:
            raise NotFoundException("Tier", tier_id)

        # Validate tier belongs to event
        if tier.event_id != event_id:
            raise ValidationException("Tier does not belong to this event", "tier_event_mismatch")

        # Check if tier is active
        if not tier.is_active:
            raise ValidationException("Tier is not active", "tier_inactive")

        # Check tier capacity
        if not tier_service.check_tier_capacity(tier_id):
            raise ValidationException("Tier is sold out", "tier_sold_out")

        # Check if event is open for registration with detailed error messages
        if event.status not in ["upcoming", "ongoing", "published"]:
            # Provide user-friendly error message based on status
            error_messages = {
                "draft": "This event is still in draft and not yet published. Please contact the organizer.",
                "completed": "This event has already ended and registration is closed.",
                "cancelled": "This event has been cancelled. Registration is no longer available.",
            }

            error_message = error_messages.get(
                event.status,
                f"Event registration is currently not available (status: {event.status})"
            )

            logger.warning(
                f"Registration blocked for event {event_id} (user {user_id}): status={event.status}"
            )
            raise ValidationException(error_message, "event_status")

        # CRITICAL CHANGE: Check if user already registered for THIS SPECIFIC TIER
        # Users can now have multiple registrations per event (one per tier)
        existing_for_tier = self.repository.get_by_user_event_tier(user_id, event_id, tier_id)

        if existing_for_tier:
            # User already has registration for THIS tier
            if existing_for_tier.status == RegistrationStatus.PENDING.value:
                # Pending registration for this tier - return for payment recovery
                logger.info(
                    f"Found existing pending registration {existing_for_tier.id} for user {user_id} in event {event_id} tier {tier_id}"
                )
                from app.modules.registrations.schemas.registration import RegistrationResponse

                existing_response = RegistrationResponse.from_orm(existing_for_tier)
                return {
                    "registration": existing_response.dict(),
                    "requires_payment": tier.requires_payment and tier.price > 0,
                    "message": "Existing pending registration found for this tier",
                }
            elif existing_for_tier.status == RegistrationStatus.CONFIRMED.value:
                # Already confirmed for this tier - cannot register again
                logger.warning(
                    f"User {user_id} already confirmed for tier {tier_id} in event {event_id}"
                )
                raise AlreadyExistsException(
                    "Registration", "user_event_tier", f"user {user_id} in event {event_id} tier {tier_id}"
                )
            elif existing_for_tier.status == RegistrationStatus.CANCELLED.value:
                # Cancelled registration for this tier - reactivate it
                logger.info(
                    f"User {user_id} re-registering for cancelled tier {tier_id}, reactivating registration {existing_for_tier.id}"
                )

                # Determine new status
                new_status = (
                    RegistrationStatus.CONFIRMED.value
                    if tier.price == 0
                    else (
                        RegistrationStatus.PENDING.value
                        if tier.requires_payment
                        else RegistrationStatus.CONFIRMED.value
                    )
                )

                # Reactivate registration
                self.repository.update(
                    existing_for_tier.id,
                    {
                        "status": new_status,
                        "event_activity_id": activity_id,
                        "participant_name": participant_name,
                        "age": age,
                        "gender": gender,
                        "t_shirt_size": t_shirt_size,
                    },
                )

                # Update counts if confirmed
                if new_status == RegistrationStatus.CONFIRMED.value:
                    tier_service.increment_tier_registrations(tier_id)
                    event = self.event_repository.get_by_id(event_id)
                    if event:
                        self.event_repository.update(
                            event_id, {"current_participants": event.current_participants + 1}
                        )

                # Update user profile
                self._update_user_profile_from_registration(user_id, age, gender, t_shirt_size)

                # Commit and return
                self.db.commit()
                reactivated_reg = self.repository.get_by_id(existing_for_tier.id)
                from app.modules.registrations.schemas.registration import RegistrationResponse

                reactivated_response = RegistrationResponse.from_orm(reactivated_reg)
                return {
                    "registration": updated_response.dict(),
                    "requires_payment": tier.requires_payment and tier.price > 0,
                    "message": "Registration reactivated",
                }
            else:
                # Other unexpected status - reject duplicate
                logger.warning(
                    f"User {user_id} has registration {existing.id} with unexpected status {existing.status}"
                )
                raise AlreadyExistsException(
                    "Registration", "user_event", f"user {user_id} in event {event_id}"
                )

        # Generate registration number
        registration_number = self._generate_registration_number(event_id)

        # Determine registration status based on tier payment requirements
        # Free tier (price=0): Auto-confirm
        # Paid tier with requires_payment=True: Pending until payment
        # Paid tier with requires_payment=False: Auto-confirm
        if tier.price == 0:
            registration_status = RegistrationStatus.CONFIRMED.value
        elif tier.requires_payment:
            registration_status = RegistrationStatus.PENDING.value
        else:
            registration_status = RegistrationStatus.CONFIRMED.value

        # Create registration
        registration_data = {
            "user_id": user_id,
            "event_id": event_id,
            "event_activity_id": activity_id,  # Activity category
            "registration_number": registration_number,
            "participant_name": participant_name,
            "age": age,
            "gender": gender,
            "t_shirt_size": t_shirt_size,
            "status": registration_status,
            "uses_tier_system": True,
            "current_tier_id": tier_id,
        }

        registration = self.repository.create(registration_data)

        # Create registration_tier entry
        registration_tier = RegistrationTier(
            registration_id=registration.id, tier_id=tier_id, is_upgrade=False
        )
        self.db.add(registration_tier)

        # IMPORTANT: Flush to get registration.id but DON'T commit yet if payment required
        # This allows us to rollback if payment creation fails
        self.db.flush()

        # CRITICAL SECURITY: For paid tiers, create payment order BEFORE final commit
        # This ensures atomicity - if payment fails, registration is rolled back
        payment_order = None
        if tier.requires_payment and tier.price > 0:
            from app.modules.payments import PaymentService

            payment_service = PaymentService(self.db)
            try:
                payment_order = payment_service.create_payment_order(
                    registration_id=registration.id,
                    amount=tier.price,
                    currency=tier.currency,
                    tier_id=tier_id,
                    is_tier_upgrade=False,
                )
            except Exception as e:
                # If payment order creation fails, rollback registration
                self.db.rollback()
                logger.error(f"Payment order creation failed, rolling back registration: {str(e)}")
                raise ValidationException(f"Failed to create payment order: {str(e)}")

        # Now commit the registration (payment order already created successfully or not needed)
        self.db.commit()
        self.db.refresh(registration_tier)

        # Create ActivityProgress record if activity_id is provided
        if activity_id:
            # Get the activity to fetch its distance
            activity = self.db.query(EventActivity).filter(EventActivity.id == activity_id).first()
            if activity and activity.distance:
                activity_progress = ActivityProgress(
                    user_id=user_id,
                    registration_id=registration.id,
                    event_id=event_id,
                    activity_id=activity_id,
                    target_distance=activity.distance,
                    distance_completed=Decimal("0.00"),
                    # progress_percentage and is_completed are hybrid_properties, computed automatically
                )
                self.db.add(activity_progress)
                self.db.commit()
                logger.info(
                    f"Created ActivityProgress for registration {registration.id} with target distance {activity.distance} km"
                )

        # Update tier registration count and event participant count
        if registration_status == RegistrationStatus.CONFIRMED.value:
            tier_service.increment_tier_registrations(tier_id)
            self.event_repository.update(
                event_id, {"current_participants": event.current_participants + 1}
            )

        # Update user profile
        self._update_user_profile_from_registration(user_id, age, gender, t_shirt_size)

        # Prepare response (convert ORM models to dicts for JSON serialization)
        from app.modules.registrations.schemas.registration import RegistrationResponse
        from app.modules.registrations.schemas.tier import TierResponse

        registration_response = RegistrationResponse.from_orm(registration)
        tier_response = TierResponse.from_orm_with_computed(tier)

        result = {
            "registration": registration_response.dict(),
            "tier": tier_response.dict(),
            "requires_payment": tier.requires_payment and tier.price > 0,
            "message": (
                "Registration successful"
                if registration_status == RegistrationStatus.CONFIRMED.value
                else "Registration pending payment"
            ),
        }

        # Include payment order in response if it was created earlier
        if payment_order:
            result["payment_order"] = payment_order

        return result

    def upgrade_tier(
        self,
        registration_id: int,
        new_tier_id: int,
        user_id: int,
        activity_id: int | None = None,
        participant_name: str | None = None,
        age: int | None = None,
        gender: str | None = None,
        t_shirt_size: str | None = None,
    ) -> dict[str, Any]:
        """
        Upgrade registration to a higher tier.

        REFACTORED: Now creates a NEW registration for the higher tier instead of
        updating the existing registration. This simplifies logic and prevents bugs
        related to tier updates. The original registration remains unchanged.

        Args:
            registration_id: Original registration ID (for validation only)
            new_tier_id: New tier ID to upgrade to
            user_id: User ID (must own the registration)
            activity_id: Optional new activity category ID
            participant_name: Optional participant name (defaults to original)
            age: Optional age (defaults to original)
            gender: Optional gender (defaults to original)
            t_shirt_size: Optional t-shirt size (defaults to original)

        Returns:
            Dict with new registration details and payment order (if required)

        Raises:
            NotFoundException: If registration or tier not found
            PermissionDeniedException: If user doesn't own the registration
            ValidationException: If upgrade is invalid
        """
        # Get existing registration for validation
        existing_registration = self.get_registration_by_id(registration_id)

        # Check ownership
        if existing_registration.user_id != user_id:
            raise PermissionDeniedException(
                "You don't have permission to upgrade this registration"
            )

        # Check if registration uses tier system
        if not existing_registration.uses_tier_system:
            raise ValidationException(
                "Registration does not use tier system", "registration_tier_system"
            )

        # Get tier service for validation
        tier_service = TierService(self.db)

        # Get current tier
        current_tier = tier_service.get_tier_by_id(existing_registration.current_tier_id)
        if not current_tier:
            raise NotFoundException("Current tier", existing_registration.current_tier_id)

        # Get new tier
        new_tier = tier_service.get_tier_by_id(new_tier_id)
        if not new_tier:
            raise NotFoundException("New tier", new_tier_id)

        # Validate new tier belongs to same event
        if new_tier.event_id != current_tier.event_id:
            raise ValidationException(
                "New tier does not belong to the same event", "tier_event_mismatch"
            )

        # Validate upgrade is to higher tier (enforces upgrade-only, no downgrades)
        if new_tier.tier_order <= current_tier.tier_order:
            raise ValidationException("Can only upgrade to higher tier", "tier_order_invalid")

        # Check if new tier is active
        if not new_tier.is_active:
            raise ValidationException("New tier is not active", "tier_inactive")

        # Use existing registration data as defaults if not provided
        final_participant_name = participant_name or existing_registration.participant_name
        final_age = age if age is not None else existing_registration.age
        final_gender = gender or existing_registration.gender
        final_t_shirt_size = t_shirt_size or existing_registration.t_shirt_size
        final_activity_id = activity_id if activity_id is not None else existing_registration.event_activity_id

        # Call register_for_event_tier to create NEW registration
        # This handles all payment logic, capacity checks, and registration creation
        result = self.register_for_event_tier(
            event_id=existing_registration.event_id,
            tier_id=new_tier_id,
            user_id=user_id,
            participant_name=final_participant_name,
            age=final_age,
            gender=final_gender,
            t_shirt_size=final_t_shirt_size,
            activity_id=final_activity_id,
        )

        # Add upgrade context to response
        result["is_upgrade"] = True
        result["upgraded_from_registration_id"] = registration_id
        result["upgraded_from_tier_id"] = existing_registration.current_tier_id
        result["upgraded_from_tier_name"] = current_tier.tier_name

        return result

    def get_user_tiers(self, registration_id: int, user_id: int) -> list[RegistrationTier]:
        """
        Get tier history for a registration.

        Args:
            registration_id: Registration ID
            user_id: User ID (must own the registration)

        Returns:
            List of RegistrationTier entries

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        if registration.user_id != user_id:
            raise PermissionDeniedException(
                "You don't have permission to view this registration's tiers"
            )

        # Get all registration_tier entries
        tier_history = (
            self.db.query(RegistrationTier)
            .filter(RegistrationTier.registration_id == registration_id)
            .order_by(RegistrationTier.registered_at)
            .all()
        )

        return tier_history

    def get_effective_rewards(self, registration_id: int, user_id: int) -> dict[str, Any]:
        """
        Get effective rewards for a registration (additive from all tiers).

        Args:
            registration_id: Registration ID
            user_id: User ID (must own the registration)

        Returns:
            Dict with all rewards user is entitled to

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.get_registration_by_id(registration_id)

        # Check ownership
        if registration.user_id != user_id:
            raise PermissionDeniedException(
                "You don't have permission to view this registration's rewards"
            )

        # Get all tiers user has registered for, ordered by tier_order
        tier_entries = (
            self.db.query(RegistrationTier)
            .join(EventRegistrationTier, RegistrationTier.tier_id == EventRegistrationTier.id)
            .filter(RegistrationTier.registration_id == registration_id)
            .order_by(EventRegistrationTier.tier_order)
            .all()
        )

        # Collect all rewards (additive)
        all_rewards = []
        tier_names = []
        highest_tier = None

        for tier_entry in tier_entries:
            tier = tier_entry.tier
            tier_names.append(tier.tier_name)

            if tier.rewards:
                all_rewards.extend(tier.rewards)

            # Track highest tier
            if highest_tier is None or tier.tier_order > highest_tier.tier_order:
                highest_tier = tier

        # Remove duplicates while preserving order
        all_rewards = list(dict.fromkeys(all_rewards))

        return {
            "registration_id": registration_id,
            "tier_names": tier_names,
            "all_rewards": all_rewards,
            "highest_tier": highest_tier.tier_name if highest_tier else None,
        }

    def confirm_registration(
        self, registration_id: int, upgrade_to_tier_id: int | None = None
    ) -> bool:
        """
        Confirm a pending registration after successful payment.

        Updates registration status to 'confirmed' and increments event/tier participant counts.
        For tier upgrades, also updates current_tier_id to the paid tier.
        This method is idempotent - safe to call multiple times.

        CRITICAL: Uses row-level locking to prevent race conditions from duplicate webhook calls.

        Args:
            registration_id: Registration ID to confirm
            upgrade_to_tier_id: If provided, updates current_tier_id (for tier upgrades)

        Returns:
            bool: True if registration was confirmed, False if already confirmed

        Raises:
            NotFoundException: If registration not found
        """
        from app.modules.events.domain.event import Event

        # CRITICAL FIX: Use row-level locking to prevent race conditions
        # Lock registration row to prevent concurrent confirmations from duplicate webhooks
        registration = (
            self.db.query(Registration)
            .filter(Registration.id == registration_id)
            .with_for_update()
            .first()
        )

        if not registration:
            raise NotFoundException("Registration", registration_id)

        # Check if already confirmed (now with row lock held)
        if registration.status == RegistrationStatus.CONFIRMED.value:
            logger.info(f"Registration {registration_id} already confirmed (idempotent)")
            return False

        # Update registration status and tier if applicable
        registration.status = RegistrationStatus.CONFIRMED.value
        if upgrade_to_tier_id is not None:
            registration.current_tier_id = upgrade_to_tier_id
            logger.info(f"Upgrading registration {registration_id} to tier {upgrade_to_tier_id}")

        # CRITICAL FIX: Lock event row and increment participant count atomically
        event = (
            self.db.query(Event).filter(Event.id == registration.event_id).with_for_update().first()
        )
        if event:
            event.current_participants += 1
            logger.info(f"Incremented event {event.id} participants: {event.current_participants}")
        else:
            logger.warning(f"Event {registration.event_id} not found, cannot increment count")

        # CRITICAL FIX: Lock tier row and increment count atomically (if using tier system)
        if registration.uses_tier_system and registration.current_tier_id:
            tier = (
                self.db.query(EventRegistrationTier)
                .filter(EventRegistrationTier.id == registration.current_tier_id)
                .with_for_update()
                .first()
            )

            if tier:
                tier.current_registrations += 1
                logger.info(
                    f"Incremented tier {tier.id} registrations: {tier.current_registrations}"
                )
            else:
                logger.warning(
                    f"Tier {registration.current_tier_id} not found, cannot increment count"
                )

        # Commit all changes atomically
        self.db.commit()
        logger.info(f"Registration {registration_id} confirmed successfully")
        return True
