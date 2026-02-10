import pytest
import os
from app.core.config import Settings

def test_security_validation_dev():
    # Development should pass even without secret
    s = Settings(ENVIRONMENT="development", HYPERCODE_JWT_SECRET=None, HYPERCODE_DB_URL="sqlite://")
    s.validate_security() # Should not raise

def test_security_validation_prod_missing():
    # Production missing secret should fail
    # Provide API_KEY to pass first check
    s = Settings(ENVIRONMENT="production", API_KEY="key", HYPERCODE_JWT_SECRET=None, HYPERCODE_DB_URL="sqlite://")
    with pytest.raises(ValueError, match="missing"):
        s.validate_security()

def test_security_validation_prod_short():
    # Production short secret should fail
    s = Settings(ENVIRONMENT="production", API_KEY="key", HYPERCODE_JWT_SECRET="short", HYPERCODE_DB_URL="sqlite://")
    with pytest.raises(ValueError, match="too short"):
        s.validate_security()

def test_security_validation_prod_valid():
    # Production valid secret should pass
    valid_secret = "a" * 32
    s = Settings(ENVIRONMENT="production", API_KEY="key", HYPERCODE_JWT_SECRET=valid_secret, HYPERCODE_DB_URL="sqlite://")
    s.validate_security() # Should not raise
