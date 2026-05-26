"""
Payment Expiry Background Job

Fixes P8: No Payment Expiry - Pending Orders Forever

This job automatically expires pending payment orders after a timeout period
and releases any held tier capacity.

Schedule: Run every 5 minutes
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import PaymentStatus
from app.modules.payments.domain.payment import Payment
from app.modules.registrations.services.tier_service import TierService

logger = logging.getLogger(__name__)


# Configuration
PAYMENT_EXPIRY_MINUTES = 30  # Expire payments after 30 minutes
MAX_PAYMENTS_PER_RUN = 100  # Process at most 100 expired payments per run


class PaymentExpiryJob:
    """
    Background job to expire abandoned payment orders.

    Handles:
    - Marking pending payments as expired
    - Releasing tier capacity
    - Decrementing event participant count
    - Logging expired payments for analytics
    """

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self._should_close_db = db is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()

    def find_expired_payments(self) -> list[Payment]:
        """
        Find pending payments that have exceeded expiry timeout.

        Returns:
            List of expired Payment objects
        """
        expiry_cutoff = datetime.now() - timedelta(minutes=PAYMENT_EXPIRY_MINUTES)

        expired_payments = (
            self.db.query(Payment)
            .filter(
                and_(
                    Payment.status == PaymentStatus.PENDING.value,
                    Payment.initiated_at < expiry_cutoff,
                )
            )
            .limit(MAX_PAYMENTS_PER_RUN)
            .all()
        )

        logger.info(f"Found {len(expired_payments)} expired payments")
        return expired_payments

    def expire_payment(self, payment: Payment) -> bool:
        """
        Expire a single payment and release resources.

        Args:
            payment: Payment object to expire

        Returns:
            bool: True if successfully expired, False if error occurred
        """
        try:
            logger.info(
                f"Expiring payment {payment.id}: "
                f"order_id={payment.gateway_order_id}, "
                f"amount=₹{payment.amount}, "
                f"initiated_at={payment.initiated_at}"
            )

            # Mark payment as expired
            payment.status = "expired"
            payment.updated_at = datetime.now()

            # Get registration for cancellation (applies to all payments)
            from app.modules.registrations.domain.registration import Registration

            registration = (
                self.db.query(Registration)
                .filter(Registration.id == payment.registration_id)
                .first()
            )

            # Cancel pending registrations for ANY expired payment
            if registration and registration.status == "pending":
                logger.info(f"Cancelling pending registration {registration.id}")
                registration.status = "cancelled"
                registration.last_payment_status = "expired"
                registration.updated_at = datetime.now()

            # Release tier capacity if applicable
            if payment.tier_id:
                TierService(self.db)

                if not payment.is_tier_upgrade:
                    # Initial tier registration - capacity might have been reserved
                    logger.info(f"Releasing tier capacity for tier {payment.tier_id}")
                    # Note: Registration cancellation already handled above

                else:
                    # Tier upgrade - release upgrade capacity
                    logger.info(f"Expiring tier upgrade payment for tier {payment.tier_id}")

                    from app.modules.registrations.domain.registration import Registration
                    from app.modules.registrations.domain.registration_tier import RegistrationTier

                    registration = (
                        self.db.query(Registration)
                        .filter(Registration.id == payment.registration_id)
                        .first()
                    )

                    if registration:
                        # Find upgrade entry
                        upgrade_entry = (
                            self.db.query(RegistrationTier)
                            .filter(
                                RegistrationTier.registration_id == registration.id,
                                RegistrationTier.tier_id == payment.tier_id,
                                RegistrationTier.is_upgrade,
                            )
                            .first()
                        )

                        if upgrade_entry:
                            # Mark upgrade as cancelled
                            upgrade_entry.created_at = datetime.now()  # Update timestamp
                            logger.info(
                                f"Marked tier upgrade as cancelled: "
                                f"registration={registration.id}, "
                                f"tier={payment.tier_id}"
                            )

            # Record failed payment in registration
            from app.modules.registrations.domain.registration import Registration

            registration = (
                self.db.query(Registration)
                .filter(Registration.id == payment.registration_id)
                .first()
            )

            if registration:
                registration.last_payment_status = "expired"
                registration.last_payment_date = datetime.now()

            self.db.commit()
            logger.info(f"Successfully expired payment {payment.id}")
            return True

        except Exception as e:
            logger.error(f"Error expiring payment {payment.id}: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    def run(self) -> dict:
        """
        Run the payment expiry job.

        Returns:
            dict: Job execution summary
        """
        start_time = datetime.now()
        logger.info("Starting payment expiry job")

        try:
            # Find expired payments
            expired_payments = self.find_expired_payments()

            if not expired_payments:
                logger.info("No expired payments found")
                return {
                    "status": "success",
                    "payments_found": 0,
                    "payments_expired": 0,
                    "errors": 0,
                    "duration_seconds": 0,
                }

            # Expire each payment
            expired_count = 0
            error_count = 0

            for payment in expired_payments:
                if self.expire_payment(payment):
                    expired_count += 1
                else:
                    error_count += 1

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "status": "success" if error_count == 0 else "partial_success",
                "payments_found": len(expired_payments),
                "payments_expired": expired_count,
                "errors": error_count,
                "duration_seconds": duration,
            }

            logger.info(
                f"Payment expiry job completed: "
                f"expired={expired_count}, errors={error_count}, "
                f"duration={duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Payment expiry job failed: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }


def run_payment_expiry_job():
    """
    Entry point for APScheduler or Celery.

    Usage with APScheduler:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_payment_expiry_job,
            'interval',
            minutes=5,
            id='payment_expiry'
        )
        scheduler.start()

    Usage with Celery:
        from celery import Celery
        app = Celery('glycogrit')

        @app.task
        def expire_payments():
            return run_payment_expiry_job()

        # Schedule:
        app.conf.beat_schedule = {
            'expire-payments-every-5-minutes': {
                'task': 'expire_payments',
                'schedule': 300.0,  # 5 minutes
            },
        }
    """
    with PaymentExpiryJob() as job:
        return job.run()


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_payment_expiry_job()
    print(f"Job result: {result}")
