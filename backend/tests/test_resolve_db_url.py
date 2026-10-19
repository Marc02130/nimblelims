"""DATABASE_URL is required at import. Migrations use a different variable."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.db_url import resolve_db_url

BACKEND = Path(__file__).resolve().parents[1]


def test_runtime_url_comes_from_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://lims_app@127.0.0.1:5432/lims_db")
    monkeypatch.setenv("MIGRATE_DATABASE_URL", "postgresql://lims_migrate@127.0.0.1:5432/lims_db")
    assert resolve_db_url() == "postgresql://lims_app@127.0.0.1:5432/lims_db"


def test_runtime_url_does_not_fall_back_to_the_migrate_variable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MIGRATE_DATABASE_URL", "postgresql://lims_migrate@127.0.0.1:5432/lims_db")
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        resolve_db_url()


def test_migrate_url_does_not_fall_back_to_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://lims_app@127.0.0.1:5432/lims_db")
    monkeypatch.delenv("MIGRATE_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="MIGRATE_DATABASE_URL is required"):
        resolve_db_url(migrate=True)


def test_blank_database_url_is_unset(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    with pytest.raises(RuntimeError, match="no default database URL"):
        resolve_db_url()


def test_importing_app_database_raises_in_production_without_database_url():
    """A fresh interpreter, so the parent process's imported engine stays put."""
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = ""
    env["MIGRATE_DATABASE_URL"] = ""
    env["ALLOW_INSECURE_DEFAULTS"] = ""
    env["SECRET_KEY"] = "pytest-secret-key-not-for-production"
    proc = subprocess.run(
        [sys.executable, "-c", "import app.database"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "DATABASE_URL is required" in output
    assert "postgresql://" not in output
