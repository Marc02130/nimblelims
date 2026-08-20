"""
Application configuration
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Known insecure / placeholder JWT secrets (S3)
_INSECURE_SECRET_DEFAULTS = frozenset(
    {
        "",
        "your-secret-key-change-in-production",
        "your-secret-key-here",
        "change-me-in-production",
        "changeme",
        "secret",
    }
)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def insecure_defaults_allowed() -> bool:
    """Local/dev/test may use placeholder secrets only with an explicit flag (Q3)."""
    env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if env not in ("development", "dev", "test"):
        return False
    return _env_flag("ALLOW_INSECURE_DEFAULTS")


def resolve_secret_key() -> str:
    """
    Resolve JWT HMAC secret.

    Precedence: SECRET_KEY, then JWT_SECRET_KEY (compose historically set the latter).
    Refuses known defaults unless ENVIRONMENT is development/test AND
    ALLOW_INSECURE_DEFAULTS=true.
    """
    raw = os.getenv("SECRET_KEY")
    if raw is None or str(raw).strip() == "":
        raw = os.getenv("JWT_SECRET_KEY")
    secret = (raw or "").strip()
    if secret in _INSECURE_SECRET_DEFAULTS:
        if insecure_defaults_allowed():
            return secret or "your-secret-key-change-in-production"
        raise RuntimeError(
            "Refusing to start with a missing or default JWT secret. "
            "Set SECRET_KEY (preferred) or JWT_SECRET_KEY to a strong random value. "
            "For local development only, set ENVIRONMENT=development|test and "
            "ALLOW_INSECURE_DEFAULTS=true."
        )
    return secret


def validate_security_config() -> None:
    """Call at process start so misconfiguration fails loudly."""
    try:
        resolve_secret_key()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


# JWT Configuration — fail closed at import for app/runtime
SECRET_KEY = resolve_secret_key()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    or "30"
)

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://lims_user:lims_password@localhost:5432/lims_db",
)

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

ENVIRONMENT = (os.getenv("ENVIRONMENT") or "development").strip().lower()
ALLOW_DEV_SEED_USERS = _env_flag("ALLOW_DEV_SEED_USERS")
