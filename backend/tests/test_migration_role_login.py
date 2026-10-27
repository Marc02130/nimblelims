"""0103 creates lims_migrate as LOGIN and repairs an existing NOLOGIN role."""
from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def test_existing_nologin_lims_migrate_is_altered_to_login(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        with migrated_engine.connect() as conn:
            conn.execute(text("ALTER ROLE lims_migrate NOLOGIN"))
            conn.commit()
            before = conn.execute(
                text("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'lims_migrate'")
            ).scalar()
            assert before is False
        from tests.conftest import clear_0117_downgrade_blockers

        clear_0117_downgrade_blockers(migrated_engine)
        command.downgrade(cfg, "0102_instant_timestamptz")
        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT rolcanlogin, rolsuper, rolbypassrls
                    FROM pg_roles
                    WHERE rolname = 'lims_migrate'
                    """
                )
            ).one()
            assert row[0] is True
            assert row[1] is False
            assert row[2] is True
    finally:
        os.environ["DATABASE_URL"] = url
        os.environ["MIGRATE_DATABASE_URL"] = url
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate
