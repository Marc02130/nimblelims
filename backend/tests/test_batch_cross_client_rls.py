"""Why a cross-client batch GET is still 404.

batches_access hides a batch the caller cannot reach through
has_project_access, and FORCE ROW LEVEL SECURITY applies to lims_app.
The handler's 403 branch runs only after that query returns the row, so it
never runs for another client's batch.

Seeing existence and the owning client, without the batch's other columns,
needs one of: a SECURITY DEFINER function, a new RLS policy, or a grant to a
role that bypasses RLS. This change does none of those. The four cases
(cross-client 403, unknown id 404, own client 200, mixed batch still filtered)
are not automated here for that reason.

Sibling routes that 404 the same way: GET /batches/{id},
GET /batches/{id}/containers, GET /batches/{id}/tests,
POST /batches/{id}/containers, PATCH /batches/{id},
PATCH /batches/{id}/status, DELETE /batches/{id},
and removing a container from the batch.
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
                "SELECT count(*) FROM pg_proc "
                "WHERE prosecdef AND proname ILIKE '%batch%'"
            )
        ).scalar()
    assert policy is not None
    assert "has_project_access" in policy
    assert forced is True
    assert definers == 0


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
