"""
Statistics API Endpoints
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.modules.statistics.services.statistics_service import StatisticsService
from app.core.rate_limit import limiter, RateLimits

router = APIRouter(prefix="/api/v1/statistics", tags=["Statistics"])


class SiteStatsResponse(BaseModel):
    total_users: int
    total_events: int
    total_registrations: int
    total_activities: int
    total_distance_km: float
    new_users_30_days: int
    last_updated: datetime


class UserStatsResponse(BaseModel):
    total_activities: int
    total_distance_km: float
    total_duration_minutes: int
    events_participated: int
    activities_this_month: int


class EventStatsResponse(BaseModel):
    total_participants: int
    total_activities: int
    total_distance_km: float
    active_participants_7_days: int


@router.get("/site", response_model=SiteStatsResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_site_statistics(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Get site-wide statistics for home page."""
    service = StatisticsService(db)
    stats = service.get_site_statistics()
    return SiteStatsResponse(**stats)


@router.get("/user/me", response_model=UserStatsResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_my_statistics(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for current user."""
    service = StatisticsService(db)
    stats = service.get_user_statistics(current_user.id)
    return UserStatsResponse(**stats)


@router.get("/event/{event_id}", response_model=EventStatsResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_event_statistics(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics for specific event."""
    service = StatisticsService(db)
    stats = service.get_event_statistics(event_id)
    return EventStatsResponse(**stats)
