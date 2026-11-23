"""An analysis version does not rise when a save changes nothing (calculations S8).

Revision ID: 0125_analysis_version_no_change
Revises: 0124_calculation_configuration

OQ-CALC-31, CALC-REQ-40. Marc, 2026-11-22: the analysis version must not
increment when a save makes no real change.

Migration 0124 bumped ``analyses.version`` on any UPDATE to ``analyses`` or
``analysis_analytes``, even one that wrote identical values. This revision
replaces the deferred trigger function ``record_analysis_version`` so that, at
commit, it builds the analysis snapshot it would record and compares it with
the latest ``analysis_versions`` snapshot. Audit-only columns are left out of
the comparison: ``created_at``, ``created_by``, ``modified_at``,
``modified_by`` and the ``version`` itself. When the two snapshots match, it
skips both the version bump and the new snapshot row. Any other difference is a
real change and is recorded once per transaction, as before. A reorder
(``display_order``, ``calculation_order``), an added or removed analyte row,
and an edit to the calculation configuration are all real changes.

The function also takes the analysis row lock before it reads the latest
snapshot, so two commits for one analysis queue up and each compares against
the other's committed snapshot.

0124 is not rewritten. Downgrade restores the 0124 function body and drops the
two helper functions added here.
"""

from __future__ import annotations

import importlib.util
import os

from alembic import op

revision = "0125_analysis_version_no_change"
down_revision = "0124_calculation_configuration"
branch_labels = None
depends_on = None

APP_ROLE = "lims_app"

# Keys left out of the comparison. They record who touched a row and when, or
# are the counter this function maintains. They are not a change to the analysis.
AUDIT_KEYS = "ARRAY['version', 'created_at', 'created_by', 'modified_at', 'modified_by']"

_SNAPSHOT_FN = """
CREATE OR REPLACE FUNCTION public.analysis_snapshot_of(aid uuid)
RETURNS jsonb
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
    SELECT jsonb_build_object(
               'analysis', to_jsonb(a),
               'analytes', coalesce(
                   (SELECT jsonb_agg(to_jsonb(aa) ORDER BY aa.analyte_id)
                      FROM public.analysis_analytes aa
                     WHERE aa.analysis_id = aid),
                   '[]'::jsonb)
           )
      FROM public.analyses a
     WHERE a.id = aid
$$;
"""

_COMPARABLE_FN = f"""
CREATE OR REPLACE FUNCTION public.analysis_snapshot_comparable(snap jsonb)
RETURNS jsonb
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT jsonb_build_object(
               'analysis', coalesce(snap -> 'analysis', '{{}}'::jsonb) - {AUDIT_KEYS}::text[],
               'analytes', coalesce(
                   (SELECT jsonb_agg(t.elem - {AUDIT_KEYS}::text[] ORDER BY t.ord)
                      FROM jsonb_array_elements(coalesce(snap -> 'analytes', '[]'::jsonb))
                           WITH ORDINALITY AS t(elem, ord)),
                   '[]'::jsonb)
           )
$$;
"""

_RECORD_VERSION_FN = """
CREATE OR REPLACE FUNCTION public.record_analysis_version()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    aid uuid;
    marker text;
    new_version integer;
    last_snap jsonb;
    snap jsonb;
BEGIN
    IF TG_TABLE_NAME = 'analyses' THEN
        aid := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        aid := OLD.analysis_id;
    ELSE
        aid := NEW.analysis_id;
    END IF;

    marker := 'lims.av_' || replace(aid::text, '-', '_');
    IF coalesce(current_setting(marker, true), '') <> '' THEN
        RETURN NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.analyses a WHERE a.id = aid) THEN
        RETURN NULL;
    END IF;
    PERFORM set_config(marker, '1', true);

    -- Queue behind any other commit for this analysis, then read what it left.
    PERFORM 1 FROM public.analyses a WHERE a.id = aid FOR UPDATE;

    IF TG_TABLE_NAME = 'analyses' AND TG_OP = 'INSERT' THEN
        SELECT a.version INTO new_version FROM public.analyses a WHERE a.id = aid;
    ELSE
        SELECT v.snapshot INTO last_snap
          FROM public.analysis_versions v
         WHERE v.analysis_id = aid
         ORDER BY v.version DESC
         LIMIT 1;
        IF last_snap IS NOT NULL
           AND public.analysis_snapshot_comparable(last_snap)
               = public.analysis_snapshot_comparable(public.analysis_snapshot_of(aid)) THEN
            -- Nothing but audit columns differs: no new version, no new snapshot.
            RETURN NULL;
        END IF;

        PERFORM set_config('lims.analysis_version_bump', 'on', true);
        UPDATE public.analyses SET version = version + 1
         WHERE id = aid
        RETURNING version INTO new_version;
        PERFORM set_config('lims.analysis_version_bump', 'off', true);
    END IF;

    snap := public.analysis_snapshot_of(aid);
    INSERT INTO public.analysis_versions (analysis_id, version, snapshot, created_by)
    VALUES (
        aid,
        new_version,
        snap,
        (SELECT u.id FROM public.users u WHERE u.id = public.current_user_id())
    );
    RETURN NULL;
END;
$$;
"""


def _m0124():
    path = os.path.join(os.path.dirname(__file__), "0124_calculation_configuration.py")
    spec = importlib.util.spec_from_file_location("_m0124_for_0125", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function_grants(signature: str) -> None:
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def upgrade() -> None:
    # The two helpers run with the privileges of whoever calls them: inside the
    # SECURITY DEFINER trigger function that is its owner. They read only what
    # the caller can already read, so they need no extra grant or revoke.
    op.execute(_SNAPSHOT_FN)
    op.execute(_COMPARABLE_FN)
    op.execute(_RECORD_VERSION_FN)
    _function_grants("record_analysis_version()")


def downgrade() -> None:
    op.execute(_m0124()._RECORD_VERSION_FN)
    _function_grants("record_analysis_version()")
    op.execute("DROP FUNCTION IF EXISTS public.analysis_snapshot_comparable(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.analysis_snapshot_of(uuid)")
