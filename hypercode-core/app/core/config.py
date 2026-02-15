
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "HyperCode Core"
    ENVIRONMENT: str = "development" # development, staging, production
    OPENAI_API_KEY: str = Field(..., validation_alias="OPENAI_API_KEY")
    HYPERCODE_DB_URL: str
    HYPERCODE_REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    API_KEY: Optional[str] = None # If None, auth is disabled (Dev mode)
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    HYPERCODE_MEMORY_KEY: Optional[str] = None
    
    # Auth
    JWT_SECRET: str = Field("changethis", validation_alias="JWT_SECRET")
    # Also support HYPERCODE_JWT_SECRET for backward compatibility/env consistency
    HYPERCODE_JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @model_validator(mode='after')
    def validate_security_settings(self) -> 'Settings':
        # Sync secrets if needed
        if self.HYPERCODE_JWT_SECRET and self.JWT_SECRET == "changethis":
            self.JWT_SECRET = self.HYPERCODE_JWT_SECRET
            
        if self.ENVIRONMENT.lower() != "development":
            if self.JWT_SECRET == "changethis":
                raise ValueError(
                    "CRITICAL SECURITY ERROR: JWT_SECRET is set to unsafe default 'changethis' in non-development environment. "
                    "Please set a secure JWT_SECRET (or HYPERCODE_JWT_SECRET) environment variable."
                )
        return self

    # Rate Limiting
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100

    class Config:
        env_file = ".env"
        extra = "ignore" # Allow extra fields in .env

def get_settings():
    import os
    import sys
    s = Settings()
    if (os.getenv("PYTEST_CURRENT_TEST") or ("pytest" in sys.modules)) and not os.getenv("KEEP_API_KEY_FOR_TESTS"):
        try:
            s.API_KEY = None
        except Exception:
            pass
    return s
