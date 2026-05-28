"""
Auto-cancel Pending Registrations Task

This task automatically cancels pending registrations that haven't been
paid within a certain timeframe.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.registrations.domain.registration import Registration


def cleanup_pending_registrations(db: Session, hours: int = 24):
    """
    Cancel pending registrations older than specified hours.

    Args:
        db: Database session
        hours: Number of hours after which to cancel pending registrations

    Returns:
        Number of registrations cancelled
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Find pending registrations older than cutoff
    pending_registrations = (
        db.query(Registration)
        .filter(
            Registration.status == 'pending',
            Registration.registered_at < cutoff_time
        )
        .all()
    )

    cancelled_count = 0
    for registration in pending_registrations:
        registration.status = 'cancelled'
        cancelled_count += 1

    if cancelled_count > 0:
        db.commit()

    return cancelled_count


# Example usage in a cron job or scheduler:
#
# from apscheduler.schedulers.background import BackgroundScheduler
#
# scheduler = BackgroundScheduler()
# scheduler.add_job(
#     func=lambda: cleanup_pending_registrations(next(get_db()), hours=24),
#     trigger="interval",
#     hours=1  # Run every hour
# )
# scheduler.start()
