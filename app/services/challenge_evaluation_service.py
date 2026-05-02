"""
Challenge Evaluation Service
Evaluates user performance and awards completion status/badges
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.event import Event
from app.models.strava_connection import UserChallengeProgress
from app.models.user_reward import UserReward
from app.schemas.reward import RewardStatus
from typing import Dict, List
import logging
import uuid

logger = logging.getLogger(__name__)


class ChallengeEvaluationService:
    """
    Service for evaluating challenge completion and awarding badges

    Completion Levels:
    - failed: Did not meet minimum requirements
    - completed: Met the goal
    - exceeded: Surpassed the goal (101-150%)
    - outstanding: Exceptional performance (>150%)
    """

    def __init__(self, db: Session):
        self.db = db

    def evaluate_challenge(self, challenge_id: int) -> Dict:
        """
        Evaluate all participants in a challenge

        Args:
            challenge_id: Challenge ID

        Returns:
            Dict with evaluation summary
        """
        challenge = self.db.query(Event).filter(Event.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        if not challenge.completion_criteria:
            raise ValueError(f"Challenge {challenge_id} has no completion criteria defined")

        # Get all progress records
        progress_records = self.db.query(UserChallengeProgress).filter(
            UserChallengeProgress.challenge_id == challenge_id
        ).all()

        results = {
            "challenge_id": challenge_id,
            "challenge_name": challenge.name,
            "total_participants": len(progress_records),
            "evaluated": 0,
            "completion_breakdown": {
                "failed": 0,
                "completed": 0,
                "exceeded": 0,
                "outstanding": 0
            }
        }

        evaluation_time = datetime.now(timezone.utc)

        for progress in progress_records:
            try:
                completion_status, badge = self._evaluate_user_progress(
                    progress,
                    challenge.completion_criteria
                )

                # Update progress record
                progress.completion_status = completion_status
                progress.evaluation_date = evaluation_time
                progress.badge_earned = badge

                # Award rewards if eligible
                if completion_status in ["completed", "exceeded", "outstanding"]:
                    self._award_goodies(progress.user_id, challenge, badge)

                results["evaluated"] += 1
                results["completion_breakdown"][completion_status] += 1

                logger.info(
                    f"User {progress.user_id} in challenge {challenge_id}: "
                    f"{completion_status} ({progress.total_distance_km}km / {progress.goal_distance_km}km)"
                )

            except Exception as e:
                logger.error(f"Error evaluating user {progress.user_id}: {e}")

        self.db.commit()
        return results

    def evaluate_user(self, user_id: int, challenge_id: int) -> Dict:
        """
        Evaluate a specific user's performance in a challenge

        Args:
            user_id: User ID
            challenge_id: Challenge ID

        Returns:
            Dict with evaluation results
        """
        challenge = self.db.query(Event).filter(Event.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        if not challenge.completion_criteria:
            raise ValueError(f"Challenge {challenge_id} has no completion criteria")

        progress = self.db.query(UserChallengeProgress).filter(
            and_(
                UserChallengeProgress.user_id == user_id,
                UserChallengeProgress.challenge_id == challenge_id
            )
        ).first()

        if not progress:
            raise ValueError(f"No progress record found for user {user_id} in challenge {challenge_id}")

        completion_status, badge = self._evaluate_user_progress(
            progress,
            challenge.completion_criteria
        )

        # Update progress
        progress.completion_status = completion_status
        progress.evaluation_date = datetime.now(timezone.utc)
        progress.badge_earned = badge

        # Award rewards if eligible
        if completion_status in ["completed", "exceeded", "outstanding"]:
            self._award_goodies(user_id, challenge, badge)

        self.db.commit()

        return {
            "user_id": user_id,
            "challenge_id": challenge_id,
            "completion_status": completion_status,
            "badge_earned": badge,
            "distance_completed": progress.total_distance_km,
            "goal_distance": progress.goal_distance_km,
            "completion_percentage": progress.completion_percentage,
            "total_activities": progress.total_activities
        }

    def _evaluate_user_progress(
        self,
        progress: UserChallengeProgress,
        criteria: Dict
    ) -> tuple[str, str]:
        """
        Evaluate user progress against completion criteria

        Args:
            progress: UserChallengeProgress record
            criteria: Completion criteria dict

        Returns:
            Tuple of (completion_status, badge_name)
        """
        # Extract criteria
        min_distance_km = criteria.get("min_distance_km", 0)
        min_activities = criteria.get("min_activities", 0)
        min_days = criteria.get("min_days", 0)

        # Update goal if not set
        if progress.goal_distance_km == 0 and min_distance_km > 0:
            progress.goal_distance_km = min_distance_km

        # Calculate completion percentage
        distance_percentage = 0
        if min_distance_km > 0:
            distance_percentage = (progress.total_distance_km / min_distance_km) * 100

        # Update completion percentage
        progress.completion_percentage = int(distance_percentage)

        # Evaluate completion status
        completion_status = "failed"
        badge = None

        # Check if meets minimum requirements
        meets_distance = progress.total_distance_km >= min_distance_km
        meets_activities = progress.total_activities >= min_activities if min_activities > 0 else True
        meets_days = progress.current_streak_days >= min_days if min_days > 0 else True

        if meets_distance and meets_activities and meets_days:
            # Determine level based on distance completion
            if distance_percentage >= 150:
                completion_status = "outstanding"
                badge = "🏆 Outstanding Performer"
            elif distance_percentage >= 101:
                completion_status = "exceeded"
                badge = "⭐ Goal Crusher"
            else:
                completion_status = "completed"
                badge = "✅ Challenge Completed"
        else:
            completion_status = "failed"
            badge = "💪 Keep Training"

        return completion_status, badge

    def get_leaderboard(self, challenge_id: int, limit: int = 10) -> List[Dict]:
        """
        Get leaderboard for a challenge with user details

        Args:
            challenge_id: Challenge ID
            limit: Number of top performers to return

        Returns:
            List of top performers with their stats and user information
        """
        from app.models.user import User

        progress_records = self.db.query(UserChallengeProgress).filter(
            UserChallengeProgress.challenge_id == challenge_id
        ).order_by(
            UserChallengeProgress.total_distance_km.desc()
        ).limit(limit).all()

        leaderboard = []
        for rank, progress in enumerate(progress_records, start=1):
            # Get user details
            user = self.db.query(User).filter(User.id == progress.user_id).first()

            # Calculate time since last activity
            last_activity_time = None
            if progress.last_activity_date:
                now = datetime.now(timezone.utc)
                delta = now - progress.last_activity_date.replace(tzinfo=timezone.utc)

                if delta.days > 0:
                    last_activity_time = f"{delta.days}d ago"
                elif delta.seconds >= 3600:
                    hours = delta.seconds // 3600
                    last_activity_time = f"{hours}h ago"
                else:
                    minutes = delta.seconds // 60
                    last_activity_time = f"{minutes}m ago" if minutes > 0 else "Just now"

            leaderboard.append({
                "rank": rank,
                "user_id": progress.user_id,
                "user_name": user.full_name if user else "Unknown User",
                "user_city": user.city if user else None,
                "user_profile_picture": user.profile_picture_url if user else None,
                "total_distance_km": progress.total_distance_km,
                "total_activities": progress.total_activities,
                "completion_percentage": progress.completion_percentage,
                "completion_status": progress.completion_status or "in_progress",
                "badge_earned": progress.badge_earned,
                "last_activity_date": progress.last_activity_date.isoformat() if progress.last_activity_date else None,
                "last_activity_time": last_activity_time
            })

        return leaderboard

    def get_completion_statistics(self, challenge_id: int) -> Dict:
        """
        Get completion statistics for a challenge

        Args:
            challenge_id: Challenge ID

        Returns:
            Dict with statistics
        """
        progress_records = self.db.query(UserChallengeProgress).filter(
            UserChallengeProgress.challenge_id == challenge_id
        ).all()

        if not progress_records:
            return {
                "total_participants": 0,
                "completion_breakdown": {},
                "average_distance": 0,
                "total_distance": 0,
                "total_activities": 0
            }

        # Count by status
        status_counts = {
            "failed": 0,
            "completed": 0,
            "exceeded": 0,
            "outstanding": 0
        }

        total_distance = 0
        total_activities = 0

        for progress in progress_records:
            if progress.completion_status:
                status_counts[progress.completion_status] = status_counts.get(progress.completion_status, 0) + 1
            total_distance += progress.total_distance_km
            total_activities += progress.total_activities

        return {
            "total_participants": len(progress_records),
            "completion_breakdown": status_counts,
            "average_distance_km": total_distance // len(progress_records) if progress_records else 0,
            "total_distance_km": total_distance,
            "total_activities": total_activities,
            "completion_rate": (
                (status_counts["completed"] + status_counts["exceeded"] + status_counts["outstanding"]) /
                len(progress_records) * 100
            ) if progress_records else 0
        }

    def _award_goodies(self, user_id: int, challenge: Event, badge_earned: str) -> None:
        """
        Award rewards to user based on challenge completion and eligibility criteria

        Args:
            user_id: User ID
            challenge: Event/Challenge object
            badge_earned: Badge earned by user
        """
        if not challenge.rewards:
            return

        # Check if rewards already awarded to prevent duplicates
        existing_rewards = self.db.query(UserGoodie).filter(
            and_(
                UserGoodie.user_id == user_id,
                UserGoodie.challenge_id == challenge.id
            )
        ).count()

        if existing_rewards > 0:
            logger.info(f"Rewards already awarded to user {user_id} for challenge {challenge.id}")
            return

        # Process each reward definition
        for goodie_def in challenge.rewards:
            try:
                # Check eligibility criteria
                eligibility = goodie_def.get("eligibility_criteria", {})
                required_badges = eligibility.get("required_badges", [])

                # Check if user's badge qualifies
                if badge_earned.replace("🏆 ", "").replace("⭐ ", "").replace("✅ ", "") in [
                    b.replace("🏆 ", "").replace("⭐ ", "").replace("✅ ", "") for b in required_badges
                ]:
                    # Create reward record
                    user_reward = UserGoodie(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        challenge_id=challenge.id,
                        reward_id=goodie_def.get("id"),
                        reward_name=goodie_def.get("name"),
                        reward_description=goodie_def.get("description"),
                        reward_type=goodie_def.get("type", "custom"),
                        reward_image_url=goodie_def.get("image_url"),
                        requires_shipping='true' if goodie_def.get("requires_shipping", True) else 'false',
                        status=RewardStatus.PENDING_DETAILS,
                        awarded_at=datetime.now(timezone.utc)
                    )

                    self.db.add(user_goodie)
                    logger.info(
                        f"Awarded reward '{goodie_def.get('name')}' to user {user_id} "
                        f"for completing challenge {challenge.id}"
                    )
                else:
                    logger.info(
                        f"User {user_id} badge '{badge_earned}' does not qualify for reward "
                        f"'{goodie_def.get('name')}' (requires: {required_badges})"
                    )

            except Exception as e:
                logger.error(f"Error awarding reward to user {user_id}: {e}")
                continue
