"""Startup environment variable checker.

Validates that every required env variable is set before the application
serves any requests. Fails fast with error code ERR_CDR_78_EX_CONFIG if
any required variable is missing, naming each missing variable and pointing
the operator at .env.example.

Usage (from the application entrypoint, before any module reads configuration):
    from config.env_check import check_env
    check_env()
"""

from __future__ import annotations

import os

# Each name here must also appear in .env.example with a safe placeholder.
REQUIRED_ENV_VARS: list[str] = [
    "DATABASE_URL",
]


def check_env() -> None:
    """Check that all required environment variables are set.

    Raises:
        RuntimeError: with prefix ERR_CDR_78_EX_CONFIG if any required
            variable is absent from the environment. The error message names
            every missing variable so the operator can fix them all at once.
    """
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            f"ERR_CDR_78_EX_CONFIG: Missing required environment variable(s): "
            f"{missing_list}. "
            f"Copy .env.example to .env and supply real values for each variable."
        )
