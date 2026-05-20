"""
CQRS Queries for Activities Module

Queries represent read operations that don't change state.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class GetActivityQuery:
    """Query to get activity by ID"""
    activity_id: int


@dataclass
class GetUserActivitiesQuery:
    """Query to get all activities for a user"""
    user_id: int
    skip: int = 0
    limit: int = 100


@dataclass
class GetEventActivitiesQuery:
    """Query to get activities for user in specific event"""
    user_id: int
    event_id: int
    skip: int = 0
    limit: int = 100


@dataclass
class GetActivitiesByDateRangeQuery:
    """Query to get activities within date range"""
    user_id: int
    event_id: int
    start_date: date
    end_date: date


@dataclass
class GetProgressQuery:
    """Query to get progress by ID"""
    progress_id: int


@dataclass
class GetProgressByRegistrationQuery:
    """Query to get progress by registration ID"""
    registration_id: int


@dataclass
class GetUserProgressQuery:
    """Query to get progress for user in event"""
    user_id: int
    event_id: int


@dataclass
class GetUserProgressListQuery:
    """Query to get all progress records for user"""
    user_id: int
    skip: int = 0
    limit: int = 100


@dataclass
class GetEventLeaderboardQuery:
    """Query to get leaderboard for event"""
    event_id: int
    limit: int = 10


@dataclass
class GetActivityStatsQuery:
    """Query to get activity statistics"""
    user_id: int
    event_id: int
