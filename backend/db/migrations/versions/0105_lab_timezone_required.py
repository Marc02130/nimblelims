"""Refuse a missing lab timezone in public.current_lab_day().

Revision ID: 0105_lab_timezone_required
Revises: 0104_current_lab_day

0104 fell back to UTC when ``lab_settings.timezone`` was blank or missing,
and honoured ``lims.as_of`` for any session. There is no timezone fallback
and no session time-override hook. The function raises
``lab timezone not configured: set lab_settings.timezone``. The lab day is
always ``now()`` in the saved zone.

``STABLE`` and ``SECURITY INVOKER``. No new privilege. Owner is
``lims_migrate``.

Existing rows are not updated. Nothing is deleted.

Downgrade restores the 0104 function (UTC fallback and ``lims.as_of``).
"""
from __future__ import annotations

from alembic import op

revision = "0105_lab_timezone_required"
down_revision = "0104_current_lab_day"
branch_labels = None
depends_on = None

# Same id as models.lab_setting.LAB_SETTINGS_ID.
_SETTINGS_ID = "b1a16ae0-0000-4000-8000-000000000001"
UNSET = "lab timezone not configured: set lab_settings.timezone"

CREATE_FUNCTION = f"""
CREATE OR REPLACE FUNCTION public.current_lab_day()
RETURNS date
LANGUAGE plpgsql
STABLE
SET search_path = pg_catalog, public
AS $$
DECLARE
    zone text;
BEGIN
    BEGIN
        SELECT NULLIF(btrim(timezone), '')
          INTO zone
          FROM public.lab_settings
         WHERE id = '{_SETTINGS_ID}'::uuid;
    EXCEPTION
        WHEN undefined_table THEN
            RAISE EXCEPTION '{UNSET}';
    END;

    IF zone IS NULL THEN
        RAISE EXCEPTION '{UNSET}';
    END IF;

    RETURN (now() AT TIME ZONE zone)::date;
END;
$$;
"""

# 0104 body, restored on downgrade only.
_DOWNGRADE_FUNCTION = f"""
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
    op.execute("ALTER FUNCTION public.current_lab_day() OWNER TO lims_migrate")


def downgrade() -> None:
    op.execute(_DOWNGRADE_FUNCTION)
    op.execute("ALTER FUNCTION public.current_lab_day() OWNER TO lims_migrate")
