"""
Application configuration and registration deadline settings.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel

# Standard Indian Standard Timezone (Asia/Kolkata)
IST = ZoneInfo("Asia/Kolkata")

# Registration Deadline: 29/10/2026 16:00:00 IST (29 October 4:00 PM)
DEFAULT_DEADLINE_ISO = "2026-10-29T16:00:00+05:30"


class Settings(BaseModel):
    PROJECT_NAME: str = "MAHAVEERA FEST 2K26 Registration API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database URL: defaults to local SQLite file, can be set to PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./mahaveera_fest_2k26.db"
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """SQLAlchemy 2.0 requires postgresql:// instead of postgres://."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    # Registration Deadline in IST
    REGISTRATION_DEADLINE_STR: str = os.getenv("REGISTRATION_DEADLINE", DEFAULT_DEADLINE_ISO)
    
    # Secret Key for Administrator Dashboard access
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "Mahaveera2026Secure")
    
    # JWT Secret Key for authenticating college sessions
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mahaveera-fest-2k26-super-secure-production-secret-key-9876543210")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days valid through fest


    @property
    def deadline_datetime(self) -> datetime:
        """Parses the configured deadline into an IST timezone-aware datetime."""
        dt = datetime.fromisoformat(self.REGISTRATION_DEADLINE_STR)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)


settings = Settings()
