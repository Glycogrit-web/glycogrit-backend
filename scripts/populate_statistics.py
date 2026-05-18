#!/usr/bin/env python3
"""
Script to populate/refresh site statistics table with actual data from the database
"""
import sys
import os
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import (
    SiteStatistics,
    User,
    Event,
    Registration,
    UserReward,
    RewardStatus
)


def populate_statistics():
    """Calculate and populate site statistics from actual database data"""

    # Create database connection
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("Calculating site statistics...")

        # Calculate statistics from actual data
        total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        total_events = db.query(func.count(Event.id)).scalar() or 0
        total_registrations = db.query(func.count(Registration.id)).scalar() or 0

        # Count medals shipped (rewards with status 'shipped' or 'delivered')
        total_medals_shipped = db.query(func.count(UserReward.id)).filter(
            UserReward.status.in_([RewardStatus.SHIPPED, RewardStatus.DELIVERED])
        ).scalar() or 0

        print(f"\nCalculated Statistics:")
        print(f"  Active Users: {total_users}")
        print(f"  Total Events: {total_events}")
        print(f"  Total Registrations: {total_registrations}")
        print(f"  Medals Shipped: {total_medals_shipped}")

        # Check if statistics record exists
        stats = db.query(SiteStatistics).filter(SiteStatistics.id == 1).first()

        if stats:
            print(f"\nUpdating existing statistics record...")
            stats.total_users = total_users
            stats.total_events = total_events
            stats.total_registrations = total_registrations
            stats.total_medals_shipped = total_medals_shipped
            stats.updated_by = "populate_script"
        else:
            print(f"\nCreating new statistics record...")
            stats = SiteStatistics(
                id=1,
                total_users=total_users,
                total_events=total_events,
                total_registrations=total_registrations,
                total_medals_shipped=total_medals_shipped,
                updated_by="populate_script"
            )
            db.add(stats)

        db.commit()
        print("\n✅ Statistics successfully updated!")

    except Exception as e:
        print(f"\n❌ Error populating statistics: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_statistics()
