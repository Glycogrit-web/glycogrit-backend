import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Set up logging as early as possible
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Only log config loading once during import (reduced noise)
logger.debug("⚙️  Loading configuration from environment...")


class Settings(BaseSettings):
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv(
        "HOST", "0.0.0.0"
    )  # nosec B104 - Intentional for containerized deployment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database Configuration
    # Railway provides DATABASE_URL with internal hostname
    # Connection pooling and retry logic are configured in database.py
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/dbname"
    )

    # CORS - Allow all origins for testing
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    # Token expires after 7 days - balance between security and user convenience
    # Users won't need to re-login frequently for a fitness tracking app
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days (10,080 minutes)

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback"
    )

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

    # Redis Configuration for caching (optional - leave empty to disable caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Cache TTL settings (in seconds)
    CACHE_TTL_SHORT: int = 300      # 5 minutes - for frequently changing data
    CACHE_TTL_MEDIUM: int = 900     # 15 minutes - for moderate update frequency
    CACHE_TTL_LONG: int = 3600      # 1 hour - for rarely changing data

    @property
    def instagram_access_token(self) -> str:
        return self.INSTAGRAM_ACCESS_TOKEN

    @property
    def instagram_account_id(self) -> str:
        return self.INSTAGRAM_ACCOUNT_ID

    @property
    def admin_emails_list(self) -> list[str]:
        """Parse ADMIN_EMAILS string into a list."""
        if not self.ADMIN_EMAILS:
            return []
        return [email.strip().lower() for email in self.ADMIN_EMAILS.split(",") if email.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def normalized_frontend_url(self) -> str:
        """
        Return FRONTEND_URL without trailing slash for OAuth consistency.

        This ensures redirect URIs are consistent between authorization and token exchange.
        """
        return self.FRONTEND_URL.rstrip("/")

    @property
    def google_oauth_redirect_uri(self) -> str:
        """
        Construct OAuth redirect URI consistently.

        CRITICAL: This must match exactly with the redirect_uri sent by the frontend
        during OAuth authorization. Any mismatch will cause "invalid_grant" errors.
        """
        return f"{self.normalized_frontend_url}/auth/callback"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


# Create settings instance (logging deferred to main.py startup)
settings = Settings()
