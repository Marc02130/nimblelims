"""Store the lab timezone on one lab_settings row.

Revision ID: 0095_lab_settings
Revises: 0094_routing_map_tat_min_zero

The row starts empty. The API seeds it from LAB_TIMEZONE on first start
when the column is blank. This upgrade only creates the table, inserts
that row, and grants lims_app. It does not drop or delete anything.
There is no RLS policy: startup reads the row before a user is signed in,
and the API restricts edits to Administrator and Lab Manager.
"""

from alembic import op

revision = "0095_lab_settings"
down_revision = "0094_routing_map_tat_min_zero"
branch_labels = None
depends_on = None

# Same id as models.lab_setting.LAB_SETTINGS_ID.
SETTINGS_ID = "b1a16ae0-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE lab_settings (
            id uuid PRIMARY KEY,
            timezone varchar(64),
            modified_at timestamptz NOT NULL DEFAULT now(),
            modified_by uuid REFERENCES users(id) ON DELETE RESTRICT
        );
        """
    )
    op.execute(
        f"INSERT INTO lab_settings (id) VALUES ('{SETTINGS_ID}')"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON lab_settings TO lims_app")


def downgrade() -> None:
    # The upgrade does not drop existing objects. Reversing this revision
    # removes only the table it added.
    op.execute("DROP TABLE IF EXISTS lab_settings")
