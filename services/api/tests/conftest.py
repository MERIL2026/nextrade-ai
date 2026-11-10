from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import Settings  # noqa: E402


def make_test_settings(**overrides: Any) -> Settings:
    """Construct isolated Settings instances without reading workstation .env files."""
    defaults: dict[str, Any] = {
        "app_env": "test",
        "debug": False,
        "log_level": "INFO",
        "app_secret": "test-only-placeholder-string-min-32-chars",
        "cors_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "database_url": "postgresql+psycopg://nextrade_app:test_pass@localhost:5435/nextrade",
        "redis_url": "redis://:test_pass@localhost:6381/0",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)
