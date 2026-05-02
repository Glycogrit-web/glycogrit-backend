"""
Site Statistics API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models import (
    SiteStatistics,
    User,
    Event,
    Registration,
    UserReward,
    RewardStatus
)
from app.schemas.site_statistics import SiteStatisticsResponse
from typing import Optional

router = APIRouter()


@router.get("/statistics", response_model=SiteStatisticsResponse)
async def get_site_statistics(db: Session = Depends(get_db)):
    """
    Get site-wide statistics for the home page.
    Returns cached statistics from the database, or calculates them if not available.
    """
    # Try to get cached statistics
    stats = db.query(SiteStatistics).filter(SiteStatistics.id == 1).first()

    if stats:
        return stats

    # If no cached stats exist, calculate them
    return await calculate_and_store_statistics(db)


@router.post("/statistics/refresh", response_model=SiteStatisticsResponse)
async def refresh_site_statistics(db: Session = Depends(get_db)):
    """
    Manually refresh site statistics by recalculating from the database.
    Admin endpoint to force a statistics update.
    """
    return await calculate_and_store_statistics(db)


async def calculate_and_store_statistics(db: Session) -> SiteStatistics:
    """
    Calculate real-time statistics from the database and store them.

    - Total Users: Count of all active users
    - Total Events: Count of all events (challenges)
    - Total Registrations: Count of all event registrations
    - Total Medals Shipped: Count of rewards that have been shipped/delivered
    """
    # Calculate statistics
    total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_events = db.query(func.count(Event.id)).scalar() or 0
    total_registrations = db.query(func.count(Registration.id)).scalar() or 0

    # Count medals shipped (rewards with status 'shipped' or 'delivered')
    total_medals_shipped = db.query(func.count(UserReward.id)).filter(
        UserReward.status.in_([RewardStatus.SHIPPED, RewardStatus.DELIVERED])
    ).scalar() or 0

    # Check if statistics record exists
    stats = db.query(SiteStatistics).filter(SiteStatistics.id == 1).first()

    if stats:
        # Update existing record
        stats.total_users = total_users
        stats.total_events = total_events
        stats.total_registrations = total_registrations
        stats.total_medals_shipped = total_medals_shipped
        stats.updated_by = "system"
    else:
        # Create new record
        stats = SiteStatistics(
            id=1,
            total_users=total_users,
            total_events=total_events,
            total_registrations=total_registrations,
            total_medals_shipped=total_medals_shipped,
            updated_by="system"
        )
        db.add(stats)

    db.commit()
    db.refresh(stats)

    return stats
