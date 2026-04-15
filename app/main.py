from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import os

app = FastAPI(
    title="GlycoGrit Backend API",
    description="Backend API for GlycoGrit cycling community platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration - allow all for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "GlycoGrit Backend API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "port": settings.PORT,
        "environment": settings.ENVIRONMENT
    }


@app.get("/api/v1/test")
async def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {
        "message": "API is working!",
        "environment": settings.ENVIRONMENT,
        "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not set")
    }


@app.get("/api/v1/users/me")
async def get_current_user():
    """Mock user endpoint for testing"""
    return {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "message": "This is a test endpoint"
    }
