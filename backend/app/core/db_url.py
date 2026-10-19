"""Resolve the database URL from the environment.

Runtime reads ``DATABASE_URL``. Migrations read ``MIGRATE_DATABASE_URL``.
Neither call invents a URL, and neither falls back to the other variable.
"""
from __future__ import annotations

import os

_RUNTIME_VAR = "DATABASE_URL"
_MIGRATE_VAR = "MIGRATE_DATABASE_URL"


def resolve_db_url(*, migrate: bool = False) -> str:
    """Return the URL for this process, or raise if it is missing.

    ``migrate=False`` is the API (``lims_app``). ``migrate=True`` is Alembic
    (``lims_migrate``). A blank value is treated as unset. The error names the
    variable and does not include a connection string.
    """
    name = _MIGRATE_VAR if migrate else _RUNTIME_VAR
    url = (os.getenv(name) or "").strip()
    if not url:
        raise RuntimeError(
            f"{name} is required. Refusing to start without it. "
            "Set it in the environment. There is no default database URL."
        )
    return url
