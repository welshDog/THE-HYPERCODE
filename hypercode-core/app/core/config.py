
from pydantic_settings import BaseSettings
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
