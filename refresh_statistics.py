"""
Script to refresh site statistics in the database.
This calculates and updates statistics based on real data from events, registrations, and medals shipped.

Usage:
    python refresh_statistics.py
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
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
from sqlalchemy import func


def refresh_statistics():
    """Calculate and update site statistics from database"""

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("🔄 Refreshing site statistics...")

        # Calculate statistics
        print("📊 Calculating statistics from database...")

        total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        print(f"   ✓ Total Active Users: {total_users}")

        total_events = db.query(func.count(Event.id)).scalar() or 0
        print(f"   ✓ Total Events/Challenges: {total_events}")

        total_registrations = db.query(func.count(Registration.id)).scalar() or 0
        print(f"   ✓ Total Registrations: {total_registrations}")

        # Count medals shipped (rewards with status 'shipped' or 'delivered')
        total_medals_shipped = db.query(func.count(UserReward.id)).filter(
            UserReward.status.in_([RewardStatus.SHIPPED, RewardStatus.DELIVERED])
        ).scalar() or 0
        print(f"   ✓ Total Medals Shipped: {total_medals_shipped}")

        # Check if statistics record exists
        stats = db.query(SiteStatistics).filter(SiteStatistics.id == 1).first()

        if stats:
            print("\n📝 Updating existing statistics record...")
            stats.total_users = total_users
            stats.total_events = total_events
            stats.total_registrations = total_registrations
            stats.total_medals_shipped = total_medals_shipped
            stats.updated_by = "script"
        else:
            print("\n📝 Creating new statistics record...")
            stats = SiteStatistics(
                id=1,
                total_users=total_users,
                total_events=total_events,
                total_registrations=total_registrations,
                total_medals_shipped=total_medals_shipped,
                updated_by="script"
            )
            db.add(stats)

        db.commit()

        print("\n✅ Statistics refreshed successfully!")
        print(f"\n📈 Current Statistics:")
        print(f"   • Active Users: {total_users:,}")
        print(f"   • Challenges: {total_events:,}")
        print(f"   • Registrations: {total_registrations:,}")
        print(f"   • Medals Shipped: {total_medals_shipped:,}")
        print(f"\n💡 Tip: You can set up a cron job to run this script periodically to keep statistics up to date.")

    except Exception as e:
        print(f"\n❌ Error refreshing statistics: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    refresh_statistics()
