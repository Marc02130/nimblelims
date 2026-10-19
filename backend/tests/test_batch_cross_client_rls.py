"""batches_access is unchanged. Existence is a separate probe.

The policy still hides a batch the caller cannot reach through
has_project_access, and FORCE ROW LEVEL SECURITY still applies.
batch_access_status is the only security-definer function whose name
contains batch. It returns a status word, not the owner. The HTTP cases
live in test_batch_access_status_rls.py.
"""
from sqlalchemy import text


def test_batch_policy_hides_rows_the_caller_cannot_access(migrated_engine):
    with migrated_engine.connect() as conn:
        policy = conn.execute(
            text(
                "SELECT qual FROM pg_policies "
                "WHERE tablename = 'batches' AND policyname = 'batches_access'"
            )
        ).scalar()
        forced = conn.execute(
            text("SELECT relforcerowsecurity FROM pg_class WHERE relname = 'batches'")
        ).scalar()
        definers = conn.execute(
            text(
                "SELECT proname FROM pg_proc "
                "WHERE prosecdef AND proname ILIKE '%batch%' "
                "ORDER BY proname"
            )
        ).fetchall()
    assert policy is not None
    assert "has_project_access" in policy
    assert forced is True
    assert [row[0] for row in definers] == ["batch_access_status"]


def test_seed_qc_codes_and_qualifier_list_name(migrated_engine):
    """Migration 0097 backfills the stock QC names. The qualifier list is result_qualifiers."""
    with migrated_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT entry.name, entry.code
                FROM list_entries AS entry
                JOIN lists ON lists.id = entry.list_id
                WHERE lists.name = 'qc_types'
                  AND entry.name IN ('Positive Control', 'Negative Control')
                """
            )
        ).fetchall()
        qualifier_list = conn.execute(
            text("SELECT id FROM lists WHERE name = 'result_qualifiers'")
        ).first()
        wrong_name = conn.execute(
            text("SELECT id FROM lists WHERE name = 'qualifiers'")
        ).first()
    codes = {name: code for name, code in rows}
    assert codes.get("Positive Control") == "positive"
    assert codes.get("Negative Control") == "negative"
    assert qualifier_list is not None
    assert wrong_name is None
