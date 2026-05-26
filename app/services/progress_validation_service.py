"""
Progress Validation Service
Implements "highest value wins" logic for progress tracking
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class ProgressValidationService:
    """
    Service for validating and applying highest-value-wins logic for progress updates.

    This ensures that progress always reflects the maximum distance reported across
    all sources (admin manual, Strava, Apple Health, Android, etc.)
    """

    # Human-readable display names for sources
    SOURCE_DISPLAY_NAMES = {
        "admin_manual": "Admin Manual Edit",
        "strava": "Strava",
        "apple_health": "Apple Health",
        "google_fit": "Google Fit",
        "manual": "Manual Entry",
        "fitness_tracker": "Fitness Tracker",
        "unknown": "Unknown",
    }

    @staticmethod
    def validate_and_update_progress(
        progress,  # ActivityProgress model instance
        new_distance_km: float,
        source: str,
        metadata: dict | None = None,
    ) -> dict:
        """
        Validates new distance against current highest and updates if higher.

        Args:
            progress: ActivityProgress model instance
            new_distance_km: New distance to validate (in kilometers)
            source: Source identifier (e.g., 'strava', 'admin_manual', 'apple_health')
            metadata: Optional metadata to store with this source's distance

        Returns:
            Dict with keys:
            - "updated": bool - whether distance was updated
            - "current_distance": float - current distance (highest)
            - "attempted_distance": float - distance that was attempted
            - "source": str - source that set the current highest
            - "message": str - explanation of what happened
            - "reason": str - reason for update/rejection
        """
        current_distance = float(progress.distance_completed)
        new_distance = round(float(new_distance_km), 2)
        sync_time = datetime.now(timezone.utc)

        # Initialize distance_by_source if None
        if progress.distance_by_source is None:
            progress.distance_by_source = {}

        # Update the source-specific distance (always track it)
        source_metadata = metadata or {}
        source_metadata.update({"distance_km": new_distance, "last_updated": sync_time.isoformat()})
        progress.distance_by_source[source] = source_metadata

        # Determine if we should update the main distance
        should_update = new_distance > current_distance

        if should_update:
            # New distance is higher - update!
            progress.distance_completed = Decimal(str(new_distance))
            progress.highest_distance_source = source
            progress.highest_distance_set_at = sync_time
            progress.sync_source = source  # Keep backwards compatibility
            progress.last_sync_at = sync_time
            progress.updated_at = sync_time

            # Set completed_at if just completed
            if progress.is_completed and not progress.completed_at:
                progress.completed_at = sync_time

            source_display = ProgressValidationService.get_source_display_name(source)
            message = (
                f"Progress updated to {new_distance}km from {source_display}. "
                f"Previous value was {current_distance}km."
            )

            logger.info(
                f"Progress updated for activity_progress_id={progress.id}: "
                f"{current_distance}km -> {new_distance}km (source: {source})"
            )

            return {
                "updated": True,
                "current_distance": new_distance,
                "attempted_distance": new_distance,
                "source": source,
                "source_display": source_display,
                "message": message,
                "reason": "higher_value",
            }

        elif new_distance == current_distance:
            # Same distance - keep existing source
            current_source = progress.highest_distance_source or "unknown"
            current_source_display = ProgressValidationService.get_source_display_name(
                current_source
            )
            source_display = ProgressValidationService.get_source_display_name(source)

            message = (
                f"Progress remains at {current_distance}km from {current_source_display}. "
                f"{source_display} reported the same distance."
            )

            logger.info(
                f"Progress unchanged for activity_progress_id={progress.id}: "
                f"{source} reported same distance {new_distance}km"
            )

            return {
                "updated": False,
                "current_distance": current_distance,
                "attempted_distance": new_distance,
                "source": current_source,
                "source_display": current_source_display,
                "message": message,
                "reason": "equal_value",
            }

        else:
            # New distance is lower - reject
            current_source = progress.highest_distance_source or "unknown"
            current_source_display = ProgressValidationService.get_source_display_name(
                current_source
            )
            source_display = ProgressValidationService.get_source_display_name(source)

            message = (
                f"Progress remains at {current_distance}km from {current_source_display}. "
                f"{source_display} reported {new_distance}km which is lower than the current value. "
                f"The system always keeps the highest reported distance."
            )

            logger.info(
                f"Progress not updated for activity_progress_id={progress.id}: "
                f"{source} reported lower distance {new_distance}km vs current {current_distance}km"
            )

            return {
                "updated": False,
                "current_distance": current_distance,
                "attempted_distance": new_distance,
                "source": current_source,
                "source_display": current_source_display,
                "message": message,
                "reason": "lower_value",
            }

    @staticmethod
    def get_source_display_name(source: str) -> str:
        """
        Returns human-readable display name for a source identifier.

        Args:
            source: Source identifier (e.g., 'strava', 'admin_manual')

        Returns:
            Human-readable name (e.g., 'Strava', 'Admin Manual Edit')
        """
        return ProgressValidationService.SOURCE_DISPLAY_NAMES.get(
            source, source.replace("_", " ").title()
        )

    @staticmethod
    def should_update_progress(current_distance: float, new_distance: float) -> bool:
        """
        Determines if new distance should replace current distance.

        Args:
            current_distance: Current distance in km
            new_distance: New distance in km

        Returns:
            True if new distance should replace current, False otherwise
        """
        return round(float(new_distance), 2) > round(float(current_distance), 2)

    @staticmethod
    def get_distance_from_source(progress, source: str) -> float | None:
        """
        Gets the distance reported by a specific source.

        Args:
            progress: ActivityProgress model instance
            source: Source identifier

        Returns:
            Distance in km from that source, or None if not found
        """
        if not progress.distance_by_source:
            return None

        source_data = progress.distance_by_source.get(source)
        if not source_data:
            return None

        return source_data.get("distance_km")

    @staticmethod
    def get_all_source_distances(progress) -> dict[str, float]:
        """
        Gets distances from all sources.

        Args:
            progress: ActivityProgress model instance

        Returns:
            Dict mapping source to distance in km
        """
        if not progress.distance_by_source:
            return {}

        return {
            source: data.get("distance_km")
            for source, data in progress.distance_by_source.items()
            if data.get("distance_km") is not None
        }
