from pydantic_settings import BaseSettings
from typing import List
import os
import logging

# Set up logging as early as possible
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("⚙️  LOADING CONFIGURATION")
logger.info("=" * 60)


class Settings(BaseSettings):
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database Configuration
    # Railway provides DATABASE_URL with internal hostname
    # Connection pooling and retry logic are configured in database.py
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/dbname"
    )

    # CORS - Allow all origins for testing
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create settings instance and log configuration
logger.info("Creating Settings instance...")
settings = Settings()

logger.info(f"✅ Settings loaded:")
logger.info(f"  PORT: {settings.PORT}")
logger.info(f"  HOST: {settings.HOST}")
logger.info(f"  ENVIRONMENT: {settings.ENVIRONMENT}")
logger.info(f"  ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")

# Log database URL (hide password)
db_url = settings.DATABASE_URL
if db_url and "@" in db_url:
    try:
        protocol = db_url.split("://")[0]
        rest = db_url.split("://")[1]
        user_pass = rest.split("@")[0]
        user = user_pass.split(":")[0]
        host_and_db = rest.split("@")[1]
        logger.info(f"  DATABASE_URL: {protocol}://{user}:***@{host_and_db}")
    except:
        logger.info(f"  DATABASE_URL: {db_url[:30]}...")
else:
    logger.info(f"  DATABASE_URL: {db_url[:30] if db_url else 'NOT SET'}")

logger.info("=" * 60)
