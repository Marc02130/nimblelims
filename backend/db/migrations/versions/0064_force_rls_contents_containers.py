"""P3 S11: FORCE RLS on tenant tables; tighten containers; contents RLS.

Revision ID: 0064
Revises: 0063
Create Date: 2026-08-21

- FORCE ROW LEVEL SECURITY on core tenant tables that had policies but not FORCE
- Split containers policies: INSERT via created_by; SELECT/UPDATE/DELETE via
  admin or contents→sample→project (OQ-S11a)
- ENABLE + FORCE + policy on contents (OQ-S11b)
"""
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

FORCE_TABLES = (
    "samples",
    "tests",
    "results",
    "projects",
    "batches",
    "containers",
    "client_projects",
)


def upgrade() -> None:
    # --- containers: drop FOR ALL; split by command (OQ-S11a) ---
    op.execute("DROP POLICY IF EXISTS containers_access ON containers;")
    op.execute(
        """
        CREATE POLICY containers_select ON containers
        FOR SELECT
        USING (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
        """
    )
    # created_by on SELECT covers same-session / pre-contents visibility;
    # product rule: never commit empty containers (aliquot txn rolls back).
    op.execute(
        """
        CREATE POLICY containers_insert ON containers
        FOR INSERT
        WITH CHECK (
            is_admin()
            OR created_by = current_user_id()
        );
        """
    )
    op.execute(
        """
        CREATE POLICY containers_update ON containers
        FOR UPDATE
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
        """
    )
    op.execute(
        """
        CREATE POLICY containers_delete ON containers
        FOR DELETE
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
        """
    )

    # --- contents RLS (OQ-S11b) ---
    op.execute("ALTER TABLE contents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE contents FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS contents_access ON contents;")
    op.execute(
        """
        CREATE POLICY contents_access ON contents
        FOR ALL
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = contents.sample_id
                AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = contents.sample_id
                AND has_project_access(s.project_id)
            )
        );
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON contents TO lims_app;
            END IF;
        END $$;
        """
    )

    # --- FORCE on existing tenant tables ---
    for table in FORCE_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    for table in FORCE_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS contents_access ON contents;")
    op.execute("ALTER TABLE contents NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE contents DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS containers_select ON containers;")
    op.execute("DROP POLICY IF EXISTS containers_insert ON containers;")
    op.execute("DROP POLICY IF EXISTS containers_update ON containers;")
    op.execute("DROP POLICY IF EXISTS containers_delete ON containers;")
    op.execute(
        """
        CREATE POLICY containers_access ON containers
        FOR ALL
        USING (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
        """
    )
