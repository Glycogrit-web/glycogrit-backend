from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Deployment Platform Detection
    DEPLOYMENT_PLATFORM: str = "local"  # local, railway

    # Database
    # Railway provides DATABASE_URL automatically
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://glycogrit:glycogrit123@localhost:5432/glycogrit"
    )

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    # For Railway, can use FIREBASE_CREDENTIALS env var with JSON string
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # Environment
    ENVIRONMENT: str = "development"

    # Railway-specific
    RAILWAY_ENVIRONMENT: Optional[str] = None
    RAILWAY_PROJECT_ID: Optional[str] = None
    RAILWAY_SERVICE_ID: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_railway(self) -> bool:
        """Check if running on Railway."""
        return self.RAILWAY_ENVIRONMENT is not None or \
               os.getenv("RAILWAY_ENVIRONMENT") is not None

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production" or \
               self.RAILWAY_ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
