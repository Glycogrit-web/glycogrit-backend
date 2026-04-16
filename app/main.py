from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db, engine
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 50)
    logger.info("🚀 GlycoGrit Backend Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"Host: {settings.HOST}")
    logger.info(f"ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")

    # Log database configuration (hide password)
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        # Extract and log hostname without password
        try:
            parts = db_url.split("@")
            host_part = parts[1] if len(parts) > 1 else "unknown"
            user_part = parts[0].split("://")[1].split(":")[0] if "://" in parts[0] else "unknown"
            logger.info(f"Database User: {user_part}")
            logger.info(f"Database Host: {host_part}")
        except Exception as e:
            logger.warning(f"Could not parse DATABASE_URL: {e}")
    else:
        logger.warning("DATABASE_URL format unexpected")

    # Test database connection on startup
    logger.info("Testing database connection...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("✅ Database connection successful!")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")

    logger.info("=" * 50)
    logger.info("✅ Startup Complete")
    logger.info("=" * 50)


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
    logger.info("🔍 /api/v1/db-test endpoint called")
    logger.info(f"DATABASE_URL environment variables:")
    logger.info(f"  - DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    logger.info(f"  - DATABASE_PRIVATE_URL: {'SET' if os.getenv('DATABASE_PRIVATE_URL') else 'NOT SET'}")

    try:
        logger.info("Attempting to execute test query...")
        # Execute a simple query to test connection
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        logger.info(f"✅ Query executed successfully, result: {row[0] if row else None}")

        response = {
            "status": "success",
            "message": "Database connection successful",
            "test_query_result": row[0] if row else None,
            "database_url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "local",
            "env_vars": {
                "DATABASE_URL": "SET" if os.getenv('DATABASE_URL') else "NOT SET",
                "DATABASE_PRIVATE_URL": "SET" if os.getenv('DATABASE_PRIVATE_URL') else "NOT SET"
            }
        }
        logger.info(f"Response: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ Database connection failed!")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "error_type": type(e).__name__
        }
