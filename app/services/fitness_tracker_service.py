"""
Fitness Tracker Integration Service
Handles OAuth connections and activity syncing for multiple fitness providers
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import httpx
import logging

from app.models.fitness_tracker import FitnessTrackerConnection
from app.models.strava_connection import StravaConnection, ChallengeActivity
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.core.config import settings

logger = logging.getLogger(__name__)


class FitnessTrackerService:
    """Service to manage fitness tracker connections and activity syncing"""

    # Provider OAuth endpoints
    PROVIDER_CONFIG = {
        "strava": {
            "auth_url": "https://www.strava.com/oauth/authorize",
            "token_url": "https://www.strava.com/oauth/token",
            "api_base": "https://www.strava.com/api/v3",
            "scopes": ["activity:read_all"]
        },
        "google_fit": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "api_base": "https://www.googleapis.com/fitness/v1",
            "scopes": ["https://www.googleapis.com/auth/fitness.activity.read"]
        },
        "apple_health": {
            # Apple Health uses HealthKit SDK on iOS - requires app-based authentication
            "note": "Requires iOS app with HealthKit integration",
            "api_base": None  # Direct device API only
        },
        "nike_run_club": {
            # Nike Run Club API (unofficial - may require web scraping)
            "note": "Limited public API - may require special access",
            "api_base": "https://api.nike.com/sport"
        }
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== CONNECTION MANAGEMENT ====================

    async def connect_provider(
        self,
        user_id: int,
        provider: str,
        auth_code: str
    ) -> FitnessTrackerConnection:
        """
        Connect a fitness tracker provider using OAuth authorization code
        """
        if provider not in self.PROVIDER_CONFIG:
            raise ValueError(f"Unsupported provider: {provider}")

        # Exchange auth code for access token
        tokens = await self._exchange_auth_code(provider, auth_code)

        # Check if connection already exists
        existing = self.db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == user_id,
                FitnessTrackerConnection.provider == provider
            )
        ).first()

        if existing:
            # Update existing connection
            existing.access_token = tokens["access_token"]
            existing.refresh_token = tokens.get("refresh_token")
            existing.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
            existing.is_active = True
            existing.last_sync_at = None  # Reset sync
            self.db.commit()
            return existing

        # Create new connection
        connection = FitnessTrackerConnection(
            user_id=user_id,
            provider=provider,
            provider_user_id=tokens.get("athlete_id") or tokens.get("user_id"),
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600)),
            scope=tokens.get("scope"),
            is_active=True
        )

        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        logger.info(f"Connected {provider} for user {user_id}")
        return connection

    async def disconnect_provider(self, user_id: int, provider: str) -> bool:
        """Disconnect a fitness tracker provider"""
        connection = self.db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == user_id,
                FitnessTrackerConnection.provider == provider
            )
        ).first()

        if connection:
            connection.is_active = False
            self.db.commit()
            logger.info(f"Disconnected {provider} for user {user_id}")
            return True

        return False

    async def get_user_connections(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active connections for a user"""
        connections = self.db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == user_id,
                FitnessTrackerConnection.is_active == True
            )
        ).all()

        # Also check Strava connection (legacy)
        strava_conn = self.db.query(StravaConnection).filter(
            and_(
                StravaConnection.user_id == user_id,
                StravaConnection.is_active == True
            )
        ).first()

        result = [
            {
                "provider": conn.provider,
                "connected_at": conn.created_at,
                "last_sync": conn.last_sync_at,
                "is_active": conn.is_active
            }
            for conn in connections
        ]

        if strava_conn:
            result.append({
                "provider": "strava",
                "connected_at": strava_conn.created_at,
                "last_sync": strava_conn.last_sync_at,
                "is_active": strava_conn.is_active
            })

        return result

    # ==================== TOKEN MANAGEMENT ====================

    async def _exchange_auth_code(self, provider: str, auth_code: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for access tokens"""
        config = self.PROVIDER_CONFIG[provider]

        if provider == "strava":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data={
                        "client_id": settings.STRAVA_CLIENT_ID,
                        "client_secret": settings.STRAVA_CLIENT_SECRET,
                        "code": auth_code,
                        "grant_type": "authorization_code"
                    }
                )
                response.raise_for_status()
                return response.json()

        elif provider == "google_fit":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data={
                        "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                        "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                        "code": auth_code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.GOOGLE_FIT_REDIRECT_URI
                    }
                )
                response.raise_for_status()
                return response.json()

        else:
            raise NotImplementedError(f"Token exchange not implemented for {provider}")

    async def _refresh_access_token(self, connection: FitnessTrackerConnection) -> str:
        """Refresh expired access token"""
        config = self.PROVIDER_CONFIG[connection.provider]

        if connection.provider == "strava":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data={
                        "client_id": settings.STRAVA_CLIENT_ID,
                        "client_secret": settings.STRAVA_CLIENT_SECRET,
                        "refresh_token": connection.refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                tokens = response.json()

                connection.access_token = tokens["access_token"]
                connection.refresh_token = tokens.get("refresh_token", connection.refresh_token)
                connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
                self.db.commit()

                return tokens["access_token"]

        elif connection.provider == "google_fit":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data={
                        "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                        "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                        "refresh_token": connection.refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                tokens = response.json()

                connection.access_token = tokens["access_token"]
                connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
                self.db.commit()

                return tokens["access_token"]

        raise NotImplementedError(f"Token refresh not implemented for {connection.provider}")

    async def _ensure_valid_token(self, connection: FitnessTrackerConnection) -> str:
        """Ensure token is valid, refresh if needed"""
        if connection.token_expires_at and connection.token_expires_at <= datetime.now(timezone.utc):
            return await self._refresh_access_token(connection)
        return connection.access_token

    # ==================== ACTIVITY SYNCING ====================

    async def sync_activities_for_challenge(
        self,
        user_id: int,
        challenge_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[ChallengeActivity]:
        """
        Sync activities from all connected providers for a specific challenge period
        """
        all_activities = []

        # Get all active connections for user
        connections = self.db.query(FitnessTrackerConnection).filter(
            and_(
                FitnessTrackerConnection.user_id == user_id,
                FitnessTrackerConnection.is_active == True
            )
        ).all()

        # Also check Strava connection (legacy)
        strava_conn = self.db.query(StravaConnection).filter(
            and_(
                StravaConnection.user_id == user_id,
                StravaConnection.is_active == True
            )
        ).first()

        # Sync from each provider
        for conn in connections:
            try:
                activities = await self._fetch_activities_from_provider(
                    conn, start_date, end_date
                )
                saved_activities = self._save_activities(
                    activities, user_id, challenge_id, conn.id
                )
                all_activities.extend(saved_activities)

                conn.last_sync_at = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Error syncing {conn.provider} for user {user_id}: {str(e)}")

        # Sync from legacy Strava connection
        if strava_conn:
            try:
                activities = await self._fetch_strava_activities_legacy(
                    strava_conn, start_date, end_date
                )
                saved_activities = self._save_activities(
                    activities, user_id, challenge_id, strava_conn.id, is_strava=True
                )
                all_activities.extend(saved_activities)

                strava_conn.last_sync_at = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Error syncing Strava (legacy) for user {user_id}: {str(e)}")

        self.db.commit()

        logger.info(f"Synced {len(all_activities)} activities for user {user_id} challenge {challenge_id}")
        return all_activities

    async def _fetch_activities_from_provider(
        self,
        connection: FitnessTrackerConnection,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch activities from a specific provider"""
        token = await self._ensure_valid_token(connection)
        config = self.PROVIDER_CONFIG[connection.provider]

        if connection.provider == "strava":
            return await self._fetch_strava_activities(token, start_date, end_date)

        elif connection.provider == "google_fit":
            return await self._fetch_google_fit_activities(token, start_date, end_date)

        elif connection.provider == "apple_health":
            # Apple Health requires iOS app integration
            raise NotImplementedError("Apple Health requires native iOS integration")

        elif connection.provider == "nike_run_club":
            return await self._fetch_nike_activities(token, start_date, end_date)

        return []

    async def _fetch_strava_activities(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch activities from Strava API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.PROVIDER_CONFIG['strava']['api_base']}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "after": int(start_date.timestamp()),
                    "before": int(end_date.timestamp()),
                    "per_page": 100
                }
            )
            response.raise_for_status()
            activities = response.json()

            # Normalize to common format
            return [
                {
                    "provider": "strava",
                    "external_id": str(act["id"]),
                    "activity_type": act["type"],
                    "activity_name": act["name"],
                    "distance_meters": act["distance"],
                    "duration_seconds": act["moving_time"],
                    "elevation_gain_meters": act.get("total_elevation_gain", 0),
                    "average_speed": act.get("average_speed", 0),
                    "max_speed": act.get("max_speed", 0),
                    "activity_date": datetime.fromisoformat(act["start_date"].replace("Z", "+00:00"))
                }
                for act in activities
            ]

    async def _fetch_strava_activities_legacy(
        self,
        connection: StravaConnection,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch activities from legacy Strava connection"""
        # Ensure token is valid
        if connection.expires_at <= datetime.now(timezone.utc):
            # Refresh token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.strava.com/oauth/token",
                    data={
                        "client_id": settings.STRAVA_CLIENT_ID,
                        "client_secret": settings.STRAVA_CLIENT_SECRET,
                        "refresh_token": connection.refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                tokens = response.json()

                connection.access_token = tokens["access_token"]
                connection.refresh_token = tokens.get("refresh_token", connection.refresh_token)
                connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
                self.db.commit()

        return await self._fetch_strava_activities(connection.access_token, start_date, end_date)

    async def _fetch_google_fit_activities(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch activities from Google Fit API"""
        async with httpx.AsyncClient() as client:
            # Google Fit uses aggregated data from DataSources
            response = await client.post(
                f"{self.PROVIDER_CONFIG['google_fit']['api_base']}/users/me/dataset:aggregate",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "aggregateBy": [
                        {"dataTypeName": "com.google.distance.delta"},
                        {"dataTypeName": "com.google.activity.segment"},
                        {"dataTypeName": "com.google.speed"}
                    ],
                    "bucketByActivitySegment": {"minDurationMillis": 600000},  # 10 min minimum
                    "startTimeMillis": int(start_date.timestamp() * 1000),
                    "endTimeMillis": int(end_date.timestamp() * 1000)
                }
            )
            response.raise_for_status()
            data = response.json()

            # Parse and normalize activities
            activities = []
            for bucket in data.get("bucket", []):
                if "activitySegment" in bucket:
                    activity_type = bucket["activitySegment"].get("activityType", 0)
                    distance = 0
                    duration = 0

                    for dataset in bucket.get("dataset", []):
                        for point in dataset.get("point", []):
                            if "distance" in point.get("dataTypeName", ""):
                                distance += sum(v.get("fpVal", 0) for v in point.get("value", []))
                            duration = int(point.get("endTimeNanos", 0)) - int(point.get("startTimeNanos", 0))

                    activities.append({
                        "provider": "google_fit",
                        "external_id": f"gfit_{bucket['startTimeMillis']}",
                        "activity_type": self._map_google_fit_activity_type(activity_type),
                        "activity_name": f"Google Fit Activity",
                        "distance_meters": distance,
                        "duration_seconds": duration // 1_000_000_000,  # Convert nanoseconds
                        "elevation_gain_meters": 0,
                        "average_speed": distance / (duration / 1_000_000_000) if duration > 0 else 0,
                        "max_speed": 0,
                        "activity_date": datetime.fromtimestamp(bucket["startTimeMillis"] / 1000)
                    })

            return activities

    async def _fetch_nike_activities(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch activities from Nike Run Club (unofficial API)"""
        # Note: Nike Run Club API is not officially public
        # This is a placeholder for potential integration
        logger.warning("Nike Run Club integration not fully implemented")
        return []

    def _save_activities(
        self,
        activities: List[Dict[str, Any]],
        user_id: int,
        challenge_id: int,
        connection_id: int,
        is_strava: bool = False
    ) -> List[ChallengeActivity]:
        """Save fetched activities to database, avoiding duplicates"""
        saved = []

        for act_data in activities:
            # Check if activity already exists
            existing = self.db.query(ChallengeActivity).filter(
                and_(
                    ChallengeActivity.user_id == user_id,
                    ChallengeActivity.challenge_id == challenge_id,
                    ChallengeActivity.source_provider == act_data["provider"],
                    ChallengeActivity.external_activity_id == act_data["external_id"]
                )
            ).first()

            if existing:
                continue  # Skip duplicate

            # Create new activity record
            activity = ChallengeActivity(
                challenge_id=challenge_id,
                user_id=user_id,
                strava_connection_id=connection_id if is_strava else None,
                source_provider=act_data["provider"],
                external_activity_id=act_data["external_id"],
                activity_type=act_data["activity_type"],
                activity_name=act_data["activity_name"],
                distance_meters=act_data["distance_meters"],
                duration_seconds=act_data["duration_seconds"],
                elevation_gain_meters=act_data.get("elevation_gain_meters", 0),
                average_speed=act_data.get("average_speed", 0),
                max_speed=act_data.get("max_speed", 0),
                activity_date=act_data["activity_date"],
                is_verified=True  # Auto-verified from provider
            )

            self.db.add(activity)
            saved.append(activity)

        return saved

    def _map_google_fit_activity_type(self, activity_type: int) -> str:
        """Map Google Fit activity type codes to readable names"""
        mapping = {
            7: "Walking",
            8: "Running",
            1: "Cycling",
            93: "Hiking",
            # Add more mappings as needed
        }
        return mapping.get(activity_type, "Other")
