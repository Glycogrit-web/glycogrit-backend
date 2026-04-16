"""
Permission checker utilities for authorization across the application.

These helpers enforce access control rules for various resources.
"""

from app.core.exceptions import PermissionDeniedException
from app.models.event import Event
from app.models.registration import Registration
from app.models.activity import EventActivity


class PermissionChecker:
    """Centralized permission checking for all resources."""

    @staticmethod
    def is_owner(resource_user_id: int, current_user_id: int) -> bool:
        """Check if the current user owns the resource."""
        return resource_user_id == current_user_id

    @staticmethod
    def is_event_organizer(event: Event, current_user_id: int) -> bool:
        """Check if the current user is the organizer of the event."""
        return event.organizer_id == current_user_id

    @staticmethod
    def is_registration_owner(registration: Registration, current_user_id: int) -> bool:
        """Check if the current user owns the registration."""
        return registration.user_id == current_user_id

    @staticmethod
    def is_activity_owner(activity: EventActivity, current_user_id: int) -> bool:
        """Check if the current user owns the activity."""
        return activity.user_id == current_user_id

    @staticmethod
    def require_owner(resource_user_id: int, current_user_id: int, resource_name: str = "resource") -> None:
        """
        Require that the current user owns the resource.
        Raises PermissionDeniedException if not the owner.
        """
        if not PermissionChecker.is_owner(resource_user_id, current_user_id):
            raise PermissionDeniedException(f"You can only modify your own {resource_name}")

    @staticmethod
    def require_event_organizer(event: Event, current_user_id: int) -> None:
        """
        Require that the current user is the event organizer.
        Raises PermissionDeniedException if not the organizer.
        """
        if not PermissionChecker.is_event_organizer(event, current_user_id):
            raise PermissionDeniedException("Only the event organizer can perform this action")

    @staticmethod
    def require_registration_owner(registration: Registration, current_user_id: int) -> None:
        """
        Require that the current user owns the registration.
        Raises PermissionDeniedException if not the owner.
        """
        if not PermissionChecker.is_registration_owner(registration, current_user_id):
            raise PermissionDeniedException("You can only modify your own registrations")

    @staticmethod
    def require_activity_owner(activity: EventActivity, current_user_id: int) -> None:
        """
        Require that the current user owns the activity.
        Raises PermissionDeniedException if not the owner.
        """
        if not PermissionChecker.is_activity_owner(activity, current_user_id):
            raise PermissionDeniedException("You can only modify your own activities")

    @staticmethod
    def can_manage_category(event: Event, current_user_id: int) -> bool:
        """
        Check if the current user can manage event categories.
        Only event organizers can manage categories for their events.
        """
        return PermissionChecker.is_event_organizer(event, current_user_id)

    @staticmethod
    def require_category_management(event: Event, current_user_id: int) -> None:
        """
        Require that the current user can manage event categories.
        Raises PermissionDeniedException if not authorized.
        """
        if not PermissionChecker.can_manage_category(event, current_user_id):
            raise PermissionDeniedException("Only the event organizer can manage event categories")
