"""
Background Scheduler for Challenge Management
Runs periodic tasks for challenge lifecycle and activity syncing
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.challenge_scheduler import ChallengeSchedulerService
from app.services.activity_sync_service import ActivitySyncService
from app.services.challenge_evaluation_service import ChallengeEvaluationService
import logging

logger = logging.getLogger(__name__)


class ChallengeBackgroundScheduler:
    """
    Background scheduler for automatic challenge management

    Scheduled Jobs:
    - Process challenge starts (daily at 00:01)
    - Process challenge completions (daily at 23:00)
    - Sync activities for active challenges (every 6 hours)
    - Evaluate completed challenges (daily at 23:30)
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup scheduled jobs"""

        # Job 1: Process challenge starts - Daily at 00:01
        self.scheduler.add_job(
            func=self.process_challenge_starts,
            trigger=CronTrigger(hour=0, minute=1),
            id="process_challenge_starts",
            name="Process Challenge Starts",
            replace_existing=True
        )

        # Job 2: Process challenge completions - Daily at 23:00
        self.scheduler.add_job(
            func=self.process_challenge_completions,
            trigger=CronTrigger(hour=23, minute=0),
            id="process_challenge_completions",
            name="Process Challenge Completions",
            replace_existing=True
        )

        # Job 3: Sync activities for active challenges - Every 6 hours
        self.scheduler.add_job(
            func=self.sync_active_challenges,
            trigger=CronTrigger(hour="*/6"),
            id="sync_active_challenges",
            name="Sync Active Challenge Activities",
            replace_existing=True
        )

        # Job 4: Evaluate completed challenges - Daily at 23:30
        self.scheduler.add_job(
            func=self.evaluate_completed_challenges,
            trigger=CronTrigger(hour=23, minute=30),
            id="evaluate_completed_challenges",
            name="Evaluate Completed Challenges",
            replace_existing=True
        )

        logger.info("Scheduled jobs configured successfully")

    async def process_challenge_starts(self):
        """Process challenges that should start today"""
        logger.info("Running: Process Challenge Starts")

        db = SessionLocal()
        try:
            scheduler_service = ChallengeSchedulerService(db)
            started_ids = scheduler_service.process_challenge_starts()

            logger.info(f"Started {len(started_ids)} challenges: {started_ids}")

        except Exception as e:
            logger.error(f"Error processing challenge starts: {e}")
        finally:
            db.close()

    async def process_challenge_completions(self):
        """Process challenges that should complete today"""
        logger.info("Running: Process Challenge Completions")

        db = SessionLocal()
        try:
            scheduler_service = ChallengeSchedulerService(db)
            completed_ids = scheduler_service.process_challenge_completions()

            logger.info(f"Completed {len(completed_ids)} challenges: {completed_ids}")

        except Exception as e:
            logger.error(f"Error processing challenge completions: {e}")
        finally:
            db.close()

    async def sync_active_challenges(self):
        """Sync activities for all active challenges"""
        logger.info("Running: Sync Active Challenge Activities")

        db = SessionLocal()
        try:
            scheduler_service = ChallengeSchedulerService(db)
            active_challenges = scheduler_service.get_active_challenges()

            logger.info(f"Found {len(active_challenges)} active challenges to sync")

            sync_service = ActivitySyncService(db)

            for challenge in active_challenges:
                try:
                    results = await sync_service.sync_challenge_activities(challenge.id)
                    logger.info(
                        f"Synced challenge {challenge.id}: "
                        f"{results['total_activities']} activities for {results['synced_users']} users"
                    )
                except Exception as e:
                    logger.error(f"Error syncing challenge {challenge.id}: {e}")

        except Exception as e:
            logger.error(f"Error in sync active challenges job: {e}")
        finally:
            db.close()

    async def evaluate_completed_challenges(self):
        """Evaluate challenges that completed today"""
        logger.info("Running: Evaluate Completed Challenges")

        db = SessionLocal()
        try:
            from app.modules.events.domain.event import Event
            from datetime import date

            # Find challenges that completed today
            today = date.today()
            completed_today = db.query(Event).filter(
                Event.end_date == today,
                Event.status == 'completed'
            ).all()

            logger.info(f"Found {len(completed_today)} challenges to evaluate")

            evaluation_service = ChallengeEvaluationService(db)

            for challenge in completed_today:
                try:
                    results = evaluation_service.evaluate_challenge(challenge.id)
                    logger.info(
                        f"Evaluated challenge {challenge.id}: "
                        f"{results['evaluated']}/{results['total_participants']} participants"
                    )
                except Exception as e:
                    logger.error(f"Error evaluating challenge {challenge.id}: {e}")

        except Exception as e:
            logger.error(f"Error in evaluate completed challenges job: {e}")
        finally:
            db.close()

    def start(self):
        """Start the scheduler"""
        logger.info("Starting background scheduler...")
        self.scheduler.start()
        logger.info("Background scheduler started successfully")

    def shutdown(self):
        """Shutdown the scheduler"""
        logger.info("Shutting down background scheduler...")
        self.scheduler.shutdown()
        logger.info("Background scheduler shut down")

    def list_jobs(self):
        """List all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  - {job.id}: {job.name} | Next run: {job.next_run_time}")
        return jobs


# Global scheduler instance
challenge_scheduler = ChallengeBackgroundScheduler()
