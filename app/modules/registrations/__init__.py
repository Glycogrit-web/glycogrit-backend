"""
Registrations Module

Domain-Driven Design module for event registrations and tier management.

Public API:
    Domain:
        - Registration: Registration ORM model
        - EventRegistrationTier: Event tier ORM model
        - RegistrationTier: Registration-tier junction model
        - RegistrationEntity: Registration business rules
        - TierEntity: Tier business rules

    Value Objects:
        - RegistrationNumber: Registration number value object
        - BibNumber: Bib number value object
        - ParticipantDetails: Participant details value object
        - UpgradePrice: Tier upgrade price calculator
        - TierCapacity: Tier capacity tracker

    Services:
        - RegistrationService: Main registration service

    Repositories:
        - RegistrationRepository: Data access layer

    Commands (CQRS):
        - RegisterForEventCommand
        - RegisterForTierCommand
        - UpgradeTierCommand
        - CancelRegistrationCommand
        - ConfirmRegistrationCommand
        - UpdateRegistrationCommand
        - AssignBibNumberCommand
        - BulkAssignBibNumbersCommand

    Queries (CQRS):
        - GetRegistrationByIdQuery
        - GetRegistrationByNumberQuery
        - GetUserRegistrationsQuery
        - GetEventRegistrationsQuery
        - GetEventRegistrationsWithProgressQuery
        - GetUserRegistrationForEventQuery
        - GetTierHistoryQuery
        - GetStaleRegistrationsQuery
        - GetRegistrationsByStatusQuery
        - GetTierRegistrationCountQuery
        - GetEventTierStatisticsQuery
        - SearchRegistrationsQuery

Usage:
    # Import domain models and entities
    from app.modules.registrations import Registration, RegistrationEntity
    from app.modules.registrations import EventRegistrationTier, TierEntity

    # Import value objects
    from app.modules.registrations import RegistrationNumber, UpgradePrice

    # Import service
    from app.modules.registrations import RegistrationService

    # Import commands and queries
    from app.modules.registrations import RegisterForTierCommand, GetUserRegistrationsQuery

    # Use entities with business rules
    registration_entity = RegistrationEntity(registration)
    if registration_entity.can_upgrade_to_tier(new_tier)[0]:
        upgrade_price = registration_entity.calculate_upgrade_price(new_tier)

    # Use value objects
    reg_number = RegistrationNumber("EVT123-ABC123")
    upgrade = UpgradePrice.calculate(old_price, new_price)
"""

# Domain models and entities
# API Router
from app.modules.registrations.api.registrations import router as registrations_router
from app.modules.registrations.domain.entities import RegistrationEntity, TierEntity
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration import Registration
from app.modules.registrations.domain.registration_tier import RegistrationTier

# Value objects
from app.modules.registrations.domain.value_objects import (
    BibNumber,
    ParticipantDetails,
    RegistrationNumber,
    TierCapacity,
    UpgradePrice,
)

# Repositories
from app.modules.registrations.repositories.registration_repository import RegistrationRepository

# Commands (Write operations)
from app.modules.registrations.services.commands import (
    AssignBibNumberCommand,
    BulkAssignBibNumbersCommand,
    CancelRegistrationCommand,
    ConfirmRegistrationCommand,
    RegisterForEventCommand,
    RegisterForTierCommand,
    UpdateRegistrationCommand,
    UpgradeTierCommand,
)

# Queries (Read operations)
from app.modules.registrations.services.queries import (
    GetEventRegistrationsQuery,
    GetEventRegistrationsWithProgressQuery,
    GetEventTierStatisticsQuery,
    GetRegistrationByIdQuery,
    GetRegistrationByNumberQuery,
    GetRegistrationsByStatusQuery,
    GetStaleRegistrationsQuery,
    GetTierHistoryQuery,
    GetTierRegistrationCountQuery,
    GetUserRegistrationForEventQuery,
    GetUserRegistrationsQuery,
    SearchRegistrationsQuery,
)

# Services
from app.modules.registrations.services.registration_service import RegistrationService

__all__ = [
    # Domain models
    'Registration',
    'EventRegistrationTier',
    'RegistrationTier',

    # Domain entities
    'RegistrationEntity',
    'TierEntity',

    # Value objects
    'RegistrationNumber',
    'BibNumber',
    'ParticipantDetails',
    'UpgradePrice',
    'TierCapacity',

    # Services
    'RegistrationService',

    # Repositories
    'RegistrationRepository',

    # Commands
    'RegisterForEventCommand',
    'RegisterForTierCommand',
    'UpgradeTierCommand',
    'CancelRegistrationCommand',
    'ConfirmRegistrationCommand',
    'UpdateRegistrationCommand',
    'AssignBibNumberCommand',
    'BulkAssignBibNumbersCommand',

    # Queries
    'GetRegistrationByIdQuery',
    'GetRegistrationByNumberQuery',
    'GetUserRegistrationsQuery',
    'GetEventRegistrationsQuery',
    'GetEventRegistrationsWithProgressQuery',
    'GetUserRegistrationForEventQuery',
    'GetTierHistoryQuery',
    'GetStaleRegistrationsQuery',
    'GetRegistrationsByStatusQuery',
    'GetTierRegistrationCountQuery',
    'GetEventTierStatisticsQuery',
    'SearchRegistrationsQuery',

    # API Router
    'registrations_router',
]
