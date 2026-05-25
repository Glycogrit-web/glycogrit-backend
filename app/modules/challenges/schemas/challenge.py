"""
Challenge Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChallengeProgressResponse(BaseModel):
    """Challenge progress response"""
    challenge_id: int
    challenge_name: str
    status: str = Field(..., description="not_started, in_progress, completed, failed")
    current_distance: float = Field(..., description="Distance completed in km")
    target_distance: float = Field(..., description="Target distance in km")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    remaining_distance: float = Field(..., ge=0, description="Remaining distance in km")
    activity_count: int = Field(..., ge=0, description="Number of activities logged")
    streak_days: int = Field(..., ge=0, description="Current streak in days")
    last_activity_date: datetime | None = Field(None, description="Last activity date")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "challenge_id": 10,
                "challenge_name": "100 Miles in May",
                "status": "in_progress",
                "current_distance": 65.5,
                "target_distance": 160.93,
                "progress_percentage": 40.7,
                "remaining_distance": 95.43,
                "activity_count": 12,
                "streak_days": 5,
                "last_activity_date": "2026-05-20T10:30:00"
            }
        }


class ChallengeJoinRequest(BaseModel):
    """Challenge join request"""
    pass  # No body needed, user_id from auth, event_id from path


class ChallengeJoinResponse(BaseModel):
    """Challenge join response"""
    registration_id: int
    event_id: int
    user_id: int
    status: str
    message: str = "Successfully joined the challenge!"

    class Config:
        from_attributes = True


class ChallengeListItem(BaseModel):
    """Challenge list item"""
    id: int
    name: str
    description: str | None
    start_date: datetime
    end_date: datetime
    target_distance: float
    status: str
    is_joined: bool = False
    participant_count: int = 0

    class Config:
        from_attributes = True
