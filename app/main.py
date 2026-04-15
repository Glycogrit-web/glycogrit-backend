from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db, engine
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


@app.get("/api/v1/db-test")
async def test_database(db: Session = Depends(get_db)):
    """Test database connection"""
    try:
        # Execute a simple query to test connection
        result = db.execute("SELECT 1 as test")
        row = result.fetchone()
        return {
            "status": "success",
            "message": "Database connection successful",
            "test_query_result": row[0] if row else None,
            "database_url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "local"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }
