"""Configuring agent: settings, named configurations, ragged-style vectors, ledger.

Revision ID: 0083
Revises: 0082
"""

from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None

SETTINGS_ID = "c0a16ae0-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE configuring_agent_settings (
            id uuid PRIMARY KEY,
            name varchar(255) NOT NULL UNIQUE,
            agent_provider varchar(32),
            agent_model varchar(255),
            key_ciphertext text,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid REFERENCES users(id),
            modified_at timestamptz NOT NULL DEFAULT now(),
            modified_by uuid REFERENCES users(id),
            CONSTRAINT configuring_agent_settings_provider_chk
                CHECK (agent_provider IS NULL OR agent_provider IN ('openai', 'xai', 'anthropic'))
        );

        INSERT INTO configuring_agent_settings (id, name)
        VALUES ('"""
        + SETTINGS_ID
        + """', 'Configuring agent');

        CREATE TABLE configurations (
            id uuid PRIMARY KEY,
            client_id uuid NOT NULL REFERENCES clients(id),
            name varchar(255) NOT NULL,
            description text,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid REFERENCES users(id),
            modified_at timestamptz NOT NULL DEFAULT now(),
            modified_by uuid REFERENCES users(id),
            CONSTRAINT configurations_client_name_uniq UNIQUE (client_id, name)
        );

        CREATE TABLE configuration_documents (
            id uuid PRIMARY KEY,
            configuration_id uuid NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
            name varchar(255) NOT NULL,
            file_type varchar(16) NOT NULL,
            content text,
            status varchar(16) NOT NULL,
            embedding_model varchar(128),
            chunk_count integer NOT NULL DEFAULT 0,
            error_message text,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid REFERENCES users(id),
            CONSTRAINT configuration_documents_status_chk
                CHECK (status IN ('processing', 'ready', 'failed'))
        );

        CREATE TABLE configuration_chunks (
            id uuid PRIMARY KEY,
            configuration_id uuid NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
            document_id uuid NOT NULL REFERENCES configuration_documents(id) ON DELETE CASCADE,
            content text NOT NULL,
            embedding vector(384) NOT NULL,
            embedding_model varchar(128) NOT NULL,
            chunk_index integer NOT NULL,
            heading text,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX configuration_chunks_embedding_idx
            ON configuration_chunks USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX configuration_chunks_configuration_idx
            ON configuration_chunks (configuration_id);

        CREATE TABLE configuration_runs (
            id uuid PRIMARY KEY,
            configuration_id uuid NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
            name varchar(255) NOT NULL,
            status varchar(32) NOT NULL,
            goal_note text,
            banner text,
            error_message text,
            applied_count integer NOT NULL DEFAULT 0,
            skipped_count integer NOT NULL DEFAULT 0,
            stopped_count integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid REFERENCES users(id),
            modified_at timestamptz NOT NULL DEFAULT now(),
            modified_by uuid REFERENCES users(id),
            CONSTRAINT configuration_runs_status_chk CHECK (
                status IN (
                    'preparing', 'reading_inputs', 'proposing', 'applying',
                    'stopped', 'failed', 'done'
                )
            )
        );

        CREATE TABLE configuration_steps (
            id uuid PRIMARY KEY,
            run_id uuid NOT NULL REFERENCES configuration_runs(id) ON DELETE CASCADE,
            position integer NOT NULL,
            group_name varchar(32) NOT NULL,
            target varchar(255) NOT NULL,
            action varchar(500) NOT NULL,
            why varchar(500) NOT NULL,
            decision varchar(16) NOT NULL DEFAULT 'pending',
            status varchar(16) NOT NULL,
            call_method varchar(8),
            call_path text,
            call_body jsonb,
            gap text,
            error_message text,
            CONSTRAINT configuration_steps_decision_chk
                CHECK (decision IN ('pending', 'accepted', 'skipped')),
            CONSTRAINT configuration_steps_status_chk
                CHECK (status IN ('proposed', 'stopped', 'applied', 'failed', 'skipped'))
        );

        CREATE TABLE configuration_items (
            id uuid PRIMARY KEY,
            configuration_id uuid NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
            run_id uuid REFERENCES configuration_runs(id),
            kind varchar(64) NOT NULL,
            name varchar(255) NOT NULL,
            target_id uuid,
            detail text,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid REFERENCES users(id)
        );
        """
    )
    for table in (
        "configuring_agent_settings",
        "configurations",
        "configuration_documents",
        "configuration_chunks",
        "configuration_runs",
        "configuration_steps",
        "configuration_items",
    ):
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_app"
        )
        op.execute(
            f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY {table}_config_edit ON {table} FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM users u
                    JOIN role_permissions rp ON rp.role_id = u.role_id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE u.id = current_user_id()
                      AND p.name = 'config:edit'
                      AND p.active = true
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM users u
                    JOIN role_permissions rp ON rp.role_id = u.role_id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE u.id = current_user_id()
                      AND p.name = 'config:edit'
                      AND p.active = true
                )
            );
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            """
        )


def downgrade() -> None:
    for table in (
        "configuration_items",
        "configuration_steps",
        "configuration_runs",
        "configuration_chunks",
        "configuration_documents",
        "configurations",
        "configuring_agent_settings",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
