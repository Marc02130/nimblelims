"""Default results.entry_date to the lab calendar day.

Revision ID: 0104_current_lab_day
Revises: 0103_migration_role_owner

``CURRENT_DATE`` uses the session time zone. The API session is UTC, so an
omitted entry date is already tomorrow during an evening in America/New_York.

``public.current_lab_day()`` is ``STABLE`` and ``SECURITY INVOKER``. It reads
``lab_settings.timezone``, which ``lims_app`` can already ``SELECT``. There is
no row-level security on that table. PostgreSQL grants ``EXECUTE`` to
``PUBLIC`` when a function is created. This revision adds no privilege.

A blank timezone, or no ``lab_settings`` row, uses UTC. That is the API
connection zone and the clock ``current_lab_day()`` is measured from before a
lab zone is saved. Python has no separate IANA default. A saved name that is
not a time zone still fails the insert.

``lims.as_of``, when set, replaces ``now()`` for tests. Production leaves it
unset. Existing rows are not updated. Nothing is deleted.

Downgrade puts ``CURRENT_DATE`` back and drops the function.
"""
from __future__ import annotations

from alembic import op

revision = "0104_current_lab_day"
down_revision = "0103_migration_role_owner"
branch_labels = None
depends_on = None

# Same id as models.lab_setting.LAB_SETTINGS_ID.
_SETTINGS_ID = "b1a16ae0-0000-4000-8000-000000000001"

CREATE_FUNCTION = f"""
CREATE OR REPLACE FUNCTION public.current_lab_day()
RETURNS date
LANGUAGE plpgsql
STABLE
SET search_path = pg_catalog, public
AS $$
DECLARE
    as_of text;
    moment timestamptz;
    zone text;
BEGIN
    as_of := NULLIF(current_setting('lims.as_of', true), '');
    IF as_of IS NULL THEN
        moment := now();
    ELSE
        moment := as_of::timestamptz;
    END IF;

    BEGIN
        SELECT NULLIF(btrim(timezone), '')
          INTO zone
          FROM public.lab_settings
         WHERE id = '{_SETTINGS_ID}'::uuid;
    EXCEPTION
        WHEN undefined_table THEN
            zone := NULL;
    END;

    IF zone IS NULL THEN
        zone := 'UTC';
    END IF;

    RETURN (moment AT TIME ZONE zone)::date;
END;
$$;
"""


def upgrade() -> None:
    op.execute(CREATE_FUNCTION)
    op.execute(
        "ALTER TABLE results ALTER COLUMN entry_date "
        "SET DEFAULT public.current_lab_day()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE results ALTER COLUMN entry_date SET DEFAULT CURRENT_DATE")
    op.execute("DROP FUNCTION IF EXISTS public.current_lab_day()")
