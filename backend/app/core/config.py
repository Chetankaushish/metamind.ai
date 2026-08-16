import os
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MetaMind AI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "metamind_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL: Optional[str] = None

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        pwd = self.POSTGRES_PASSWORD or "postgres_password"
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        pwd = self.POSTGRES_PASSWORD or "postgres_password"
        return f"postgresql://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/2")

    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET", ""))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = os.getenv(
        "CORS_ORIGINS", 
        os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000")
    )
    
    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:3000", "http://localhost:8000"]

    # Meta API
        # Meta API
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")

    META_REDIRECT_URI: str = os.getenv(
        "META_REDIRECT_URI",
        "https://adsmind.online/api/v1/auth/meta/callback"
    )

    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")

    META_WEBHOOK_VERIFY_TOKEN: str = os.getenv(
        "META_WEBHOOK_VERIFY_TOKEN",
        os.getenv("META_VERIFY_TOKEN", "")
    )

    META_GRAPH_API_VERSION: str = os.getenv(
        "META_API_VERSION",
        "v23.0"
    )

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """Strict mandatory .env validation for production deployments."""
        if self.ENVIRONMENT == "production":
            insecure_defaults = [
                "CHANGE_ME",
                "CHANGE_ME_META_SECRET",
                "CHANGE_ME_WEBHOOK_SECRET",
                "CHANGE_ME_DB_PASSWORD",
            ]
            if not self.SECRET_KEY or self.SECRET_KEY in insecure_defaults:
                raise ValueError("CRITICAL: SECRET_KEY / JWT_SECRET must be securely set in .env for production")
            if not self.POSTGRES_PASSWORD or self.POSTGRES_PASSWORD in insecure_defaults:
                raise ValueError("CRITICAL: POSTGRES_PASSWORD must be explicitly set in .env for production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
