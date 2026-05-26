"""
Events Module

Domain-Driven Design module for event management and lifecycle.

Public API:
    Domain:
        - Event: Event ORM model
        - EventActivity: Event activity ORM model
        - EventEntity: Event business rules
        - ActivityEntity: Activity business rules

    Value Objects:
        - EventSlug: Event slug value object
        - EventLocation: Location value object
        - RegistrationPeriod: Registration period tracker
        - EventCapacity: Capacity tracker
        - EventDateRange: Date range validator

    Services:
        - EventService: Main event service

    Repositories:
        - EventRepository: Data access for events
        - EventActivityRepository: Data access for activities

    Commands (CQRS):
        - CreateEventCommand
        - UpdateEventCommand
        - PublishEventCommand
        - CancelEventCommand
        - DeleteEventCommand
        - CreateActivityCommand
        - UpdateActivityCommand
        - DeleteActivityCommand

    Queries (CQRS):
        - GetEventByIdQuery
        - GetEventBySlugQuery
        - ListEventsQuery
        - GetUpcomingEventsQuery
        - GetFeaturedEventsQuery
        - GetEventsByOrganizerQuery
        - GetEventActivitiesQuery
        - GetActivityByIdQuery
        - SearchEventsQuery
        - GetEventsRequiringStatusUpdateQuery
        - GetEventStatisticsQuery

Usage:
    # Import domain models and entities
    from app.modules.events import Event, EventEntity
    from app.modules.events import EventActivity, ActivityEntity

    # Import value objects
    from app.modules.events import EventSlug, EventLocation, RegistrationPeriod

    # Import service
    from app.modules.events import EventService

    # Import commands and queries
    from app.modules.events import CreateEventCommand, ListEventsQuery

    # Use entities with business rules
    event_entity = EventEntity(event)
    can_accept, reason = event_entity.can_accept_registrations()
    if can_accept:
        # Allow registration
        pass

    # Use value objects
    slug = EventSlug.from_name("Mumbai Marathon 2026")
    location = EventLocation("MMRDA Grounds", "Mumbai", "Maharashtra", "India")
"""

# Domain models and entities
# API Router
from app.modules.events.api.events import router as events_router
from app.modules.events.domain.entities import ActivityEntity, EventEntity
from app.modules.events.domain.event import Event, EventActivity

# Value objects
from app.modules.events.domain.value_objects import (
    EventCapacity,
    EventDateRange,
    EventLocation,
    EventSlug,
    RegistrationPeriod,
)

# Repositories
from app.modules.events.repositories.event_repository import (
    EventActivityRepository,
    EventRepository,
)

# Commands (Write operations)
from app.modules.events.services.commands import (
    CancelEventCommand,
    CreateActivityCommand,
    CreateEventCommand,
    DeleteActivityCommand,
    DeleteEventCommand,
    PublishEventCommand,
    UpdateActivityCommand,
    UpdateEventCommand,
)

# Services
from app.modules.events.services.event_service import ActivityService, EventService

# Queries (Read operations)
from app.modules.events.services.queries import (
    GetActivityByIdQuery,
    GetEventActivitiesQuery,
    GetEventByIdQuery,
    GetEventBySlugQuery,
    GetEventsByOrganizerQuery,
    GetEventsRequiringStatusUpdateQuery,
    GetEventStatisticsQuery,
    GetFeaturedEventsQuery,
    GetUpcomingEventsQuery,
    ListEventsQuery,
    SearchEventsQuery,
)

__all__ = [
    # Domain models
    "Event",
    "EventActivity",
    # Domain entities
    "EventEntity",
    "ActivityEntity",
    # Value objects
    "EventSlug",
    "EventLocation",
    "RegistrationPeriod",
    "EventCapacity",
    "EventDateRange",
    # Services
    "EventService",
    "ActivityService",
    # Repositories
    "EventRepository",
    "EventActivityRepository",
    # Commands
    "CreateEventCommand",
    "UpdateEventCommand",
    "PublishEventCommand",
    "CancelEventCommand",
    "DeleteEventCommand",
    "CreateActivityCommand",
    "UpdateActivityCommand",
    "DeleteActivityCommand",
    # Queries
    "GetEventByIdQuery",
    "GetEventBySlugQuery",
    "ListEventsQuery",
    "GetUpcomingEventsQuery",
    "GetFeaturedEventsQuery",
    "GetEventsByOrganizerQuery",
    "GetEventActivitiesQuery",
    "GetActivityByIdQuery",
    "SearchEventsQuery",
    "GetEventsRequiringStatusUpdateQuery",
    "GetEventStatisticsQuery",
    # API Router
    "events_router",
]
