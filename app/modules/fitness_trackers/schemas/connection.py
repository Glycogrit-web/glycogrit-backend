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
    polar = "polar"


class ConnectRequest(BaseModel):
    """Schema for connecting a provider"""
    code: str = Field(..., description="Authorization code from OAuth callback")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "abc123xyz789"
            }
        }


class AuthorizationUrlResponse(BaseModel):
    """Schema for authorization URL response"""
    authorization_url: str = Field(..., description="OAuth authorization URL")
    provider: str = Field(..., description="Provider name")

    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://www.strava.com/oauth/authorize?client_id=...",
                "provider": "strava"
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
                "athlete_name": "John Doe"
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
                "last_error": None
            }
        }


class SyncResponse(BaseModel):
    """Schema for sync operation response"""
    success: bool
    activities_synced: int
    error_message: str | None = None
    provider: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "activities_synced": 25,
                "error_message": None,
                "provider": "strava"
            }
        }


class ProviderInfo(BaseModel):
    """Schema for provider information"""
    provider: str
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "strava",
                "name": "Strava"
            }
        }


class ProvidersListResponse(BaseModel):
    """Schema for available providers list"""
    providers: list[ProviderInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "providers": [
                    {"provider": "strava", "name": "Strava"},
                    {"provider": "garmin", "name": "Garmin"}
                ]
            }
        }
