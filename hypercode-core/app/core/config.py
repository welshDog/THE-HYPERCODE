
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "HyperCode Core"
    ENVIRONMENT: str = "development" # development, staging, production
    OPENAI_API_KEY: str = "sk-placeholder-key" # Default for dev/test
    HYPERCODE_DB_URL: str
    HYPERCODE_REDIS_URL: str = "redis://localhost:6379/0"
    API_KEY: Optional[str] = None # If None, auth is disabled (Dev mode)
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    HYPERCODE_MEMORY_KEY: Optional[str] = None
    HYPERCODE_JWT_SECRET: Optional[str] = None
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    @model_validator(mode='after')
    def check_production_security(self) -> 'Settings':
        """Enforces security requirements for prod/staging"""
        self.validate_security()
        return self

    def validate_security(self):
        # Allow dev/test bypass
        if self.ENVIRONMENT.lower() in ("development", "test", "local"):
            return
        
        if not self.API_KEY:
            raise ValueError("API_KEY is missing in production/staging!")
        
        if not self.HYPERCODE_JWT_SECRET:
            raise ValueError("HYPERCODE_JWT_SECRET is missing in production/staging!")
        
        if len(self.HYPERCODE_JWT_SECRET) < 32:
            raise ValueError(f"HYPERCODE_JWT_SECRET is too short ({len(self.HYPERCODE_JWT_SECRET)} chars). Must be at least 32 characters.")

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
