from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Log database configuration
logger.info("=" * 50)
logger.info("📊 Database Configuration")
logger.info("=" * 50)
db_url = settings.DATABASE_URL
if "@" in db_url:
    # Hide password in logs
    safe_url = db_url.split("@")[0].split(":")[0:-1]
    host_part = db_url.split("@")[1] if len(db_url.split("@")) > 1 else "unknown"
    logger.info(f"Connecting to: {host_part}")
else:
    logger.info(f"DATABASE_URL: {db_url[:30]}...")

# Create database engine
logger.info("Creating database engine...")
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False  # Set to True for SQL query logging
)
logger.info("✅ Database engine created")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("✅ Session factory created")

# Create base class for models
Base = declarative_base()
logger.info("=" * 50)


def get_db():
    """Dependency to get database session"""
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()
