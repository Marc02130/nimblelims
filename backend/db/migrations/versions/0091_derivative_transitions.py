"""Sample type transitions: add the 'derivative' operation.

Revision ID: 0091_derivative_transitions
Revises: 0090_reagent_tracking

Terminology (Marc): an ALIQUOT is the same sample and sample type in a new
container, with no new sample. A DERIVATIVE changes the sample type and creates
a new child sample (Blood -> DNA, Blood -> Plasma/RBC/WBC). Pools are unchanged.

sample_type_transitions stays the allow-list. Until now a type change was
stored with operation 'aliquot' (0068 seeded Blood -> DNA that way). This
migration:

* widens ck_sample_type_transitions_operation to aliquot, derivative, pool;
* converts every 'aliquot' row whose destination type differs from its source
  type to 'derivative'. Rows are matched on their own columns, never on the
  0068 seed IDs, so lab-added rows convert too. If a client already has the
  same derivative row, the old aliquot row is set inactive instead (status
  flag; nothing is deleted).

Same-type 'aliquot' rows, if any, are left as they are; aliquots need no
transition.
"""

from alembic import op
import sqlalchemy as sa

revision = "0091_derivative_transitions"
down_revision = "0090_reagent_tracking"
branch_labels = None
depends_on = None

CK = "ck_sample_type_transitions_operation"
TABLE = "sample_type_transitions"


def upgrade() -> None:
    op.drop_constraint(CK, TABLE, type_="check")
    op.create_check_constraint(
        CK, TABLE, "operation IN ('aliquot', 'derivative', 'pool')"
    )
    conn = op.get_bind()
    # A derivative twin already exists: retire the aliquot row (no delete).
    conn.execute(sa.text("""
        UPDATE sample_type_transitions AS a
           SET active = false, modified_at = NOW()
         WHERE a.operation = 'aliquot'
           AND a.source_sample_type <> a.allowed_dest_sample_type
           AND EXISTS (
               SELECT 1 FROM sample_type_transitions d
                WHERE d.client_id = a.client_id
                  AND d.source_sample_type = a.source_sample_type
                  AND d.allowed_dest_sample_type = a.allowed_dest_sample_type
                  AND d.operation = 'derivative'
           )
    """))
    conn.execute(sa.text("""
        UPDATE sample_type_transitions AS a
           SET operation = 'derivative', modified_at = NOW()
         WHERE a.operation = 'aliquot'
           AND a.source_sample_type <> a.allowed_dest_sample_type
           AND NOT EXISTS (
               SELECT 1 FROM sample_type_transitions d
                WHERE d.client_id = a.client_id
                  AND d.source_sample_type = a.source_sample_type
                  AND d.allowed_dest_sample_type = a.allowed_dest_sample_type
                  AND d.operation = 'derivative'
           )
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE sample_type_transitions AS d
           SET operation = 'aliquot', modified_at = NOW()
         WHERE d.operation = 'derivative'
           AND NOT EXISTS (
               SELECT 1 FROM sample_type_transitions a
                WHERE a.client_id = d.client_id
                  AND a.source_sample_type = d.source_sample_type
                  AND a.allowed_dest_sample_type = d.allowed_dest_sample_type
                  AND a.operation = 'aliquot'
           )
    """))
    remaining = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sample_type_transitions WHERE operation = 'derivative'"
    )).scalar()
    if remaining:
        raise RuntimeError(
            f"{remaining} derivative transition(s) have an aliquot twin; resolve them "
            "by hand before downgrading (rows are never deleted by migrations)."
        )
    op.drop_constraint(CK, TABLE, type_="check")
    op.create_check_constraint(CK, TABLE, "operation IN ('aliquot', 'pool')")
