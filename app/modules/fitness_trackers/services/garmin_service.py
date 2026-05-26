"""
Garmin Connect API Service
Handles OAuth 1.0a authentication and activity data fetching from Garmin
"""

import os
from datetime import datetime

from requests_oauthlib import OAuth1Session

from app.models.garmin_connection import GarminConnection


class GarminService:
    """Service for interacting with Garmin Connect API"""

    # Garmin API endpoints
    REQUEST_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
    AUTHORIZE_URL = "https://connect.garmin.com/oauthConfirm"
    ACCESS_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    USER_PROFILE_URL = "https://apis.garmin.com/wellness-api/rest/user/id"
    ACTIVITIES_URL = "https://apis.garmin.com/wellness-api/rest/activities"

    def __init__(self):
        self.consumer_key = os.getenv("GARMIN_CONSUMER_KEY")
        self.consumer_secret = os.getenv("GARMIN_CONSUMER_SECRET")
        self.callback_uri = os.getenv(
            "GARMIN_REDIRECT_URI", "http://localhost:5173/auth/garmin/callback"
        )

        if not self.consumer_key or not self.consumer_secret:
            raise ValueError(
                "Garmin credentials not configured. Set GARMIN_CONSUMER_KEY and GARMIN_CONSUMER_SECRET"
            )

    def get_authorization_url(self) -> dict[str, str]:
        """
        Step 1: Get request token and authorization URL
        Returns dict with 'authorization_url', 'oauth_token', 'oauth_token_secret'
        """
        oauth = OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=self.callback_uri,
        )

        try:
            # Get request token
            request_token = oauth.fetch_request_token(self.REQUEST_TOKEN_URL)

            # Generate authorization URL
            authorization_url = oauth.authorization_url(self.AUTHORIZE_URL)

            return {
                "authorization_url": authorization_url,
                "oauth_token": request_token.get("oauth_token"),
                "oauth_token_secret": request_token.get("oauth_token_secret"),
            }
        except Exception as e:
            raise Exception(f"Failed to get Garmin authorization URL: {str(e)}")

    def exchange_token(
        self, oauth_token: str, oauth_token_secret: str, oauth_verifier: str
    ) -> dict:
        """
        Step 2: Exchange request token for access token
        """
        oauth = OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier,
        )

        try:
            # Exchange for access token
            access_token = oauth.fetch_access_token(self.ACCESS_TOKEN_URL)

            return {
                "access_token": access_token.get("oauth_token"),
                "access_token_secret": access_token.get("oauth_token_secret"),
            }
        except Exception as e:
            raise Exception(f"Failed to exchange Garmin token: {str(e)}")

    def get_user_profile(self, access_token: str, access_token_secret: str) -> dict:
        """
        Get Garmin user profile information
        """
        oauth = OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        try:
            response = oauth.get(self.USER_PROFILE_URL)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get Garmin user profile: {str(e)}")

    def get_activities(
        self, access_token: str, access_token_secret: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """
        Fetch activities from Garmin within date range

        Args:
            access_token: User's access token
            access_token_secret: User's access token secret
            start_date: Start date for activities
            end_date: End date for activities

        Returns:
            List of activity dictionaries
        """
        oauth = OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        # Format dates for Garmin API (YYYY-MM-DD)
        start_date.strftime("%Y-%m-%d")
        end_date.strftime("%Y-%m-%d")

        try:
            response = oauth.get(
                self.ACTIVITIES_URL,
                params={
                    "uploadStartTimeInSeconds": int(start_date.timestamp()),
                    "uploadEndTimeInSeconds": int(end_date.timestamp()),
                },
            )
            response.raise_for_status()

            activities = response.json()
            return self._process_activities(activities)

        except Exception as e:
            raise Exception(f"Failed to fetch Garmin activities: {str(e)}")

    def _process_activities(self, activities: list[dict]) -> list[dict]:
        """
        Process and normalize Garmin activity data
        """
        processed = []

        for activity in activities:
            # Extract relevant fields
            processed_activity = {
                "id": activity.get("activityId"),
                "name": activity.get("activityName", "Garmin Activity"),
                "type": activity.get("activityType", {}).get("typeKey", "unknown"),
                "start_date": activity.get("startTimeLocal"),
                "distance_meters": activity.get("distance", 0),
                "duration_seconds": activity.get("duration", 0),
                "elevation_gain": activity.get("elevationGain", 0),
                "average_speed": activity.get("averageSpeed", 0),
                "max_speed": activity.get("maxSpeed", 0),
                "calories": activity.get("calories", 0),
                "average_hr": activity.get("averageHR"),
                "max_hr": activity.get("maxHR"),
            }
            processed.append(processed_activity)

        return processed

    def validate_connection(self, connection: GarminConnection) -> bool:
        """
        Validate that a Garmin connection is still active
        """
        try:
            self.get_user_profile(connection.access_token, connection.access_token_secret)
            return True
        except Exception:
            return False


def get_garmin_service() -> GarminService:
    """Dependency injection for GarminService"""
    return GarminService()
