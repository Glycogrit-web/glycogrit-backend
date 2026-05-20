"""
API package for Activities module

Exports FastAPI routers for activities and progress endpoints.
"""

from app.modules.activities.api.activities import router as activities_router
from app.modules.activities.api.progress import router as progress_router

__all__ = [
    "activities_router",
    "progress_router",
]
