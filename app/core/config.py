from pydantic_settings import BaseSettings, SettingsConfigDict
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
logger.info("🔄 Force reload: Syncing Razorpay live keys from Doppler")


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
    # SECURITY: Reduced from 7 days to 1 hour for better security
    # Short-lived tokens reduce risk if token is compromised
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (was 60 * 24 * 7 = 7 days)

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback")

    # Frontend URL for redirects after OAuth
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Payment Gateway Configuration
    DEFAULT_PAYMENT_GATEWAY: str = os.getenv("DEFAULT_PAYMENT_GATEWAY", "razorpay")

    # Razorpay Configuration
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # Stripe Configuration (for future use)
    # STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    # STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    # STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Cloudflare R2 Storage Configuration
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "glycogrit-events")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")  # Public bucket URL

    # Instagram Configuration
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

    # Admin Configuration - Comma-separated list of admin emails
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")

    @property
    def instagram_access_token(self) -> str:
        return self.INSTAGRAM_ACCESS_TOKEN

    @property
    def instagram_account_id(self) -> str:
        return self.INSTAGRAM_ACCOUNT_ID

    @property
    def admin_emails_list(self) -> List[str]:
        """Parse ADMIN_EMAILS string into a list."""
        if not self.ADMIN_EMAILS:
            return []
        return [email.strip().lower() for email in self.ADMIN_EMAILS.split(",") if email.strip()]

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


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
