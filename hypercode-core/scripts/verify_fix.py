import sys
import os
from pydantic import ValidationError

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_auth_imports():
    print("Testing Auth Imports...")
    try:
        from app.core import auth
        print("✅ Auth module imported successfully (pyjwt dependency check passed).")
    except ImportError as e:
        print(f"❌ Failed to import auth module: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error importing auth: {e}")
        sys.exit(1)

def test_config_validation():
    print("\nTesting Config Validation...")
    from app.core.config import Settings
    
    # 1. Test Development Mode (Should pass)
    print("  - Testing Development Mode...")
    try:
        os.environ["ENVIRONMENT"] = "development"
        os.environ["HYPERCODE_DB_URL"] = "postgresql://user:pass@localhost/db"
        Settings()
        print("    ✅ Development mode passed.")
    except Exception as e:
        print(f"    ❌ Development mode failed: {e}")
        sys.exit(1)

    # 2. Test Production Mode - Missing API Key (Should fail)
    print("  - Testing Production Mode (Missing Keys)...")
    try:
        os.environ["ENVIRONMENT"] = "production"
        if "API_KEY" in os.environ: del os.environ["API_KEY"]
        Settings()
        print("    ❌ Production mode SHOULD have failed but didn't.")
        sys.exit(1)
    except ValidationError as e:
        print("    ✅ Production mode correctly failed validation (Missing API_KEY).")
    except ValueError as e:
        print(f"    ✅ Production mode correctly failed validation (ValueError: {e}).")
    except Exception as e:
        print(f"    ⚠️ Unexpected exception type: {type(e)}")
        print(e)

if __name__ == "__main__":
    test_auth_imports()
    test_config_validation()
