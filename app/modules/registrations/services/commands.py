"""
Command objects for Registration Service.

Commands represent write operations that modify state.
"""

from dataclasses import dataclass


@dataclass
class RegisterForEventCommand:
    """
    DEPRECATED: Legacy command for non-tier event registration.

    All new registrations must use RegisterForTierCommand with tier-based pricing.
    This command is kept for backward compatibility only.
    """

    user_id: int
    event_id: int
    participant_name: str
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None
    activity_id: int | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if not self.participant_name or len(self.participant_name.strip()) < 2:
            raise ValueError("participant_name must be at least 2 characters")
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError("age must be between 0 and 150")
        if self.activity_id is not None and self.activity_id <= 0:
            raise ValueError("activity_id must be positive if provided")


@dataclass
class RegisterForTierCommand:
    """
    Command to register a user for a specific event tier.

    Used for tier-based events with different pricing levels.
    """

    user_id: int
    event_id: int
    tier_id: int
    participant_name: str
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None
    activity_id: int | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if self.tier_id <= 0:
            raise ValueError("tier_id must be positive")
        if not self.participant_name or len(self.participant_name.strip()) < 2:
            raise ValueError("participant_name must be at least 2 characters")
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError("age must be between 0 and 150")
        if self.activity_id is not None and self.activity_id <= 0:
            raise ValueError("activity_id must be positive if provided")


@dataclass
class UpgradeTierCommand:
    """
    Command to upgrade a registration to a higher tier.

    Calculates price difference and creates payment order if required.
    """

    registration_id: int
    new_tier_id: int
    user_id: int
    activity_id: int | None = None
    participant_name: str | None = None
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.new_tier_id <= 0:
            raise ValueError("new_tier_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.activity_id is not None and self.activity_id <= 0:
            raise ValueError("activity_id must be positive if provided")
        if self.participant_name is not None and len(self.participant_name.strip()) < 2:
            raise ValueError("participant_name must be at least 2 characters if provided")
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError("age must be between 0 and 150")


@dataclass
class CancelRegistrationCommand:
    """
    Command to cancel a registration.

    May trigger refund process if payment was made.
    """

    registration_id: int
    user_id: int
    reason: str | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class ConfirmRegistrationCommand:
    """
    Command to confirm a pending registration.

    Used after successful payment verification.
    """

    registration_id: int
    payment_id: int | None = None
    tier_id: int | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.payment_id is not None and self.payment_id <= 0:
            raise ValueError("payment_id must be positive if provided")
        if self.tier_id is not None and self.tier_id <= 0:
            raise ValueError("tier_id must be positive if provided")


@dataclass
class UpdateRegistrationCommand:
    """
    Command to update registration participant details.

    Allows updating participant information after registration.
    """

    registration_id: int
    user_id: int
    participant_name: str | None = None
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None
    activity_id: int | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.participant_name is not None and len(self.participant_name.strip()) < 2:
            raise ValueError("participant_name must be at least 2 characters if provided")
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError("age must be between 0 and 150")
        if self.activity_id is not None and self.activity_id <= 0:
            raise ValueError("activity_id must be positive if provided")

        # At least one field must be provided
        if all(
            field is None
            for field in [
                self.participant_name,
                self.age,
                self.gender,
                self.t_shirt_size,
                self.activity_id,
            ]
        ):
            raise ValueError("At least one field must be provided for update")


@dataclass
class AssignBibNumberCommand:
    """
    Command to assign a bib number to a registration.

    Bib numbers are typically assigned before the event starts.
    """

    registration_id: int
    bib_number: str

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if not self.bib_number or not self.bib_number.strip():
            raise ValueError("bib_number cannot be empty")


@dataclass
class BulkAssignBibNumbersCommand:
    """
    Command to assign bib numbers to multiple registrations.

    Used for batch bib number assignment before events.
    """

    event_id: int
    registrations: list[tuple[int, str]]  # List of (registration_id, bib_number)

    def __post_init__(self):
        """Validate command data"""
        if self.event_id <= 0:
            raise ValueError("event_id must be positive")
        if not self.registrations:
            raise ValueError("registrations list cannot be empty")

        for reg_id, bib_num in self.registrations:
            if reg_id <= 0:
                raise ValueError(f"Invalid registration_id: {reg_id}")
            if not bib_num or not bib_num.strip():
                raise ValueError(f"Invalid bib_number for registration {reg_id}")
