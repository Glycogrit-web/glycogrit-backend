from fastapi import APIRouter
from app.api.v1.endpoints import users, rides, events, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(rides.router, prefix="/rides", tags=["rides"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
