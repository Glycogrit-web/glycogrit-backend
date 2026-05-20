"""
Statistics Service

Aggregates site-wide, user, and event statistics for dashboards.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from app.models.user import User
from app.models.event import Event
from app.modules.registrations.domain.registration import Registration
from app.modules.activities.domain.activity_log import UserActivityLog
from app.services.base import BaseService


class StatisticsService(BaseService):
    """Service for statistics aggregation"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_site_statistics(self) -> Dict[str, Any]:
        """
        Get site-wide statistics.

        Returns:
            Dict with total users, events, activities, registrations
        """
        # Total users (excluding deactivated)
        total_users = self.db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar()

        # Total events
        total_events = self.db.query(func.count(Event.id)).scalar()

        # Total registrations
        total_registrations = self.db.query(func.count(Registration.id)).scalar()

        # Total activities
        total_activities = self.db.query(func.count(UserActivityLog.id)).scalar()

        # Total distance (in km)
        total_distance = self.db.query(
            func.coalesce(func.sum(UserActivityLog.distance), 0)
        ).scalar()

        # New users (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_users = self.db.query(func.count(User.id)).filter(
            User.created_at >= thirty_days_ago
        ).scalar()

        return {
            "total_users": total_users or 0,
            "total_events": total_events or 0,
            "total_registrations": total_registrations or 0,
            "total_activities": total_activities or 0,
            "total_distance_km": float(total_distance or 0),
            "new_users_30_days": new_users or 0,
            "last_updated": datetime.utcnow(),
        }

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics for specific user.

        Args:
            user_id: User ID

        Returns:
            Dict with user's activity statistics
        """
        # Total activities
        total_activities = self.db.query(func.count(UserActivityLog.id)).filter(
            UserActivityLog.user_id == user_id
        ).scalar()

        # Total distance
        total_distance = self.db.query(
            func.coalesce(func.sum(UserActivityLog.distance), 0)
        ).filter(UserActivityLog.user_id == user_id).scalar()

        # Total duration (minutes)
        total_duration = self.db.query(
            func.coalesce(func.sum(UserActivityLog.duration), 0)
        ).filter(UserActivityLog.user_id == user_id).scalar()

        # Events participated
        events_count = self.db.query(
            func.count(func.distinct(Registration.event_id))
        ).filter(Registration.user_id == user_id).scalar()

        # Activities this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        activities_this_month = self.db.query(func.count(UserActivityLog.id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_date >= month_start
            )
        ).scalar()

        return {
            "total_activities": total_activities or 0,
            "total_distance_km": float(total_distance or 0),
            "total_duration_minutes": int(total_duration or 0),
            "events_participated": events_count or 0,
            "activities_this_month": activities_this_month or 0,
        }

    def get_event_statistics(self, event_id: int) -> Dict[str, Any]:
        """
        Get statistics for specific event.

        Args:
            event_id: Event ID

        Returns:
            Dict with event statistics
        """
        # Total participants
        total_participants = self.db.query(func.count(Registration.id)).filter(
            Registration.event_id == event_id
        ).scalar()

        # Total activities for this event
        total_activities = self.db.query(func.count(UserActivityLog.id)).filter(
            UserActivityLog.event_id == event_id
        ).scalar()

        # Total distance
        total_distance = self.db.query(
            func.coalesce(func.sum(UserActivityLog.distance), 0)
        ).filter(UserActivityLog.event_id == event_id).scalar()

        # Active participants (logged activity in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_participants = self.db.query(
            func.count(func.distinct(UserActivityLog.user_id))
        ).filter(
            and_(
                UserActivityLog.event_id == event_id,
                UserActivityLog.activity_date >= week_ago.date()
            )
        ).scalar()

        return {
            "total_participants": total_participants or 0,
            "total_activities": total_activities or 0,
            "total_distance_km": float(total_distance or 0),
            "active_participants_7_days": active_participants or 0,
        }
