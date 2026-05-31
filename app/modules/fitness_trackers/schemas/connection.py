"""
Fitness Tracker Connection Schemas

Pydantic schemas for API validation and serialization.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProviderEnum(str, Enum):
    """Provider enumeration for schemas"""

    strava = "strava"
    garmin = "garmin"
    fitbit = "fitbit"
    wahoo = "wahoo"
    google_fit = "google_fit"
    google_health = "google_health"
    polar = "polar"


class ConnectRequest(BaseModel):
    """Schema for connecting a provider"""

    code: str = Field(..., description="Authorization code from OAuth callback")

    class Config:
        json_schema_extra = {"example": {"code": "abc123xyz789"}}


class AuthorizationUrlResponse(BaseModel):
    """Schema for authorization URL response"""

    authorization_url: str = Field(..., description="OAuth authorization URL")
    provider: str = Field(..., description="Provider name")

    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://www.strava.com/oauth/authorize?client_id=...",
                "provider": "strava",
            }
        }


class ConnectionResponse(BaseModel):
    """Schema for connection response"""

    id: int
    provider: str
    athlete_id: str
    is_active: bool
    sync_enabled: bool
    last_sync_at: datetime | None
    error_count: int
    last_error: str | None
    created_at: datetime

    # Optional athlete data
    athlete_name: str | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "provider": "strava",
                "athlete_id": "12345",
                "is_active": True,
                "sync_enabled": True,
                "last_sync_at": "2024-01-15T10:30:00",
                "error_count": 0,
                "last_error": None,
                "created_at": "2024-01-01T00:00:00",
                "athlete_name": "John Doe",
            }
        }


class ConnectionStatusResponse(BaseModel):
    """Schema for connection status"""

    connected: bool
    provider: str
    is_active: bool | None = None
    sync_enabled: bool | None = None
    token_valid: bool | None = None
    last_sync_at: datetime | None = None
    error_count: int | None = None
    last_error: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "connected": True,
                "provider": "strava",
                "is_active": True,
                "sync_enabled": True,
                "token_valid": True,
                "last_sync_at": "2024-01-15T10:30:00",
                "error_count": 0,
                "last_error": None,
            }
        }


class SyncResponse(BaseModel):
    """Schema for sync operation response"""

    success: bool
    activities_synced: int
    error_message: str | None = None
    provider: str
    sync_metadata: dict | None = Field(
        None,
        description="Detailed sync metadata including time period, distance, and data points"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "activities_synced": 25,
                "error_message": None,
                "provider": "strava",
                "sync_metadata": {
                    "time_period": {
                        "start": "2026-05-01T00:00:00Z",
                        "end": "2026-05-31T23:59:59Z",
                        "days": 30,
                        "hours": 720.0
                    },
                    "distance": {
                        "meters": 18313.90,
                        "kilometers": 18.31
                    },
                    "activity_count": 1,
                    "data_points": 160
                }
            }
        }


class ProviderInfo(BaseModel):
    """Schema for provider information"""

    provider: str
    name: str

    class Config:
        json_schema_extra = {"example": {"provider": "strava", "name": "Strava"}}


class ProvidersListResponse(BaseModel):
    """Schema for available providers list"""

    providers: list[ProviderInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "providers": [
                    {"provider": "strava", "name": "Strava"},
                    {"provider": "garmin", "name": "Garmin"},
                ]
            }
        }


class ConnectionListItemResponse(BaseModel):
    """
    Schema for listing all available providers with connection status.

    This schema returns ALL available fitness providers (OAuth + manual upload)
    with their connection status, metadata, and primary source flag.
    Used by the dashboard to display fitness sync options.
    """

    provider: str = Field(..., description="Provider identifier (e.g., 'strava', 'google_fit')")
    display_name: str = Field(..., description="Human-readable provider name")
    connected: bool = Field(..., description="Whether user has active connection")
    connection_id: int | None = Field(None, description="Database connection ID if connected")
    last_sync_at: datetime | None = Field(None, description="Last sync timestamp")
    last_sync_status: str | None = Field(None, description="Last sync status: 'success', 'error', or None")
    requires_file_upload: bool = Field(..., description="True for manual upload, False for OAuth")
    supports_oauth: bool = Field(..., description="True for OAuth providers")
    is_primary: bool = Field(..., description="True if this is the primary auto-sync source")
    same_account_as_login: bool = Field(
        ..., description="True if Google Fit uses same Google account as login"
    )

    # Additional fields for connected providers
    error_count: int = Field(0, description="Number of sync errors")
    last_error: str | None = Field(None, description="Last error message if any")
    athlete_name: str | None = Field(None, description="Athlete name from provider")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "provider": "strava",
                "display_name": "Strava",
                "connected": True,
                "connection_id": 123,
                "last_sync_at": "2024-01-15T10:30:00",
                "last_sync_status": "success",
                "requires_file_upload": False,
                "supports_oauth": True,
                "is_primary": True,
                "same_account_as_login": False,
                "error_count": 0,
                "last_error": None,
                "athlete_name": "John Doe",
            }
        }


class ChallengeProgressResponse(BaseModel):
    """
    Schema for challenge progress response.

    This schema matches the frontend's ChallengeProgress interface
    for backwards compatibility with the Strava progress endpoint.
    """

    challenge_id: int = Field(..., description="Event/Challenge ID")
    total_distance_km: float = Field(..., description="Total distance completed in kilometers")
    total_activities: int = Field(0, description="Total number of activities")
    progress_percentage: float = Field(..., description="Progress percentage (0-100)")
    goal_distance_km: float | None = Field(None, description="Target/goal distance in kilometers")
    last_activity_date: str | None = Field(None, description="Date of last activity (ISO format)")
    current_streak_days: int = Field(0, description="Current streak in days")
    proof_image_url: str | None = Field(None, description="URL to proof image")
    last_sync_source: str | None = Field(None, description="Source of last sync")
    last_sync_at: str | None = Field(None, description="Timestamp of last sync (ISO format)")

    class Config:
        json_schema_extra = {
            "example": {
                "challenge_id": 31,
                "total_distance_km": 125.5,
                "total_activities": 20,
                "progress_percentage": 62.75,
                "goal_distance_km": 200.0,
                "last_activity_date": "2024-01-15T10:30:00",
                "current_streak_days": 5,
                "proof_image_url": "https://example.com/proof.jpg",
                "last_sync_source": "strava",
                "last_sync_at": "2024-01-15T10:30:00",
            }
        }
