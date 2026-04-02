"""Dose response curve fitting: template_well_definitions, dose_response_results,
experiment_data_exclusions, fit_in_progress on experiment_runs, ci_method on results.

Revision ID: 0043
Revises: 0042
Create Date: 2026-04-02

Adds the data model for dose-response curve analysis:
  - template_well_definitions: relational well layout replacing JSONB for concentrations
  - dose_response_results: IC50/EC50 fit results with versioning + review workflow
  - experiment_data_exclusions: soft knockout audit trail
  - experiment_runs.fit_in_progress: mutex to prevent concurrent fits per run
  - dose_response_results.ci_method: "profiled" or "vcov" CI method tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0043'
down_revision = '0042'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── template_well_definitions ──────────────────────────────────────────────
    # Replaces template_definition.plate_layout.wells[] JSONB as the authoritative
    # source for concentration and role data. JSONB retains visual/structural data.
    op.create_table(
        'template_well_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('well_position', sa.String(10), nullable=False),
        sa.Column('sample_role', sa.String(20), nullable=True),   # test/positive_control/negative_control
        sa.Column('concentration_value', sa.Numeric(), nullable=True),
        sa.Column('concentration_unit', sa.String(20), nullable=True),
        sa.Column('replicate_group', sa.String(100), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['experiment_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'well_position', name='uq_template_well_definitions_template_well'),
    )
    op.create_index('idx_template_well_definitions_template_id', 'template_well_definitions', ['template_id'])
    op.execute('ALTER TABLE template_well_definitions ENABLE ROW LEVEL SECURITY;')
    op.execute("""
        CREATE POLICY template_well_definitions_client_isolation
        ON template_well_definitions
        USING (client_id = current_setting('app.client_id', true)::uuid);
    """)

    # ── dose_response_results ──────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE curve_category_enum AS ENUM (
            'SIGMOID', 'INACTIVE', 'INVERSE', 'PARTIAL_HIGH', 'PARTIAL_LOW',
            'HOOK_EFFECT', 'NOISY', 'CANNOT_FIT'
        );
    """)
    op.execute("""
        CREATE TYPE review_status_enum AS ENUM (
            'pending', 'approved', 'rejected', 'flagged'
        );
    """)

    op.create_table(
        'dose_response_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model', sa.String(10), nullable=False),  # '4PL', '3PL_FB', '3PL_FT', '5PL'

        # Fit parameters
        sa.Column('potency', sa.Numeric(), nullable=True),        # IC50 or EC50
        sa.Column('potency_type', sa.String(4), nullable=False),  # 'IC50' or 'EC50'
        sa.Column('hill_slope', sa.Numeric(), nullable=True),
        sa.Column('top', sa.Numeric(), nullable=True),
        sa.Column('bottom', sa.Numeric(), nullable=True),
        sa.Column('r_squared', sa.Numeric(), nullable=True),
        sa.Column('ci_low_95', sa.Numeric(), nullable=True),
        sa.Column('ci_high_95', sa.Numeric(), nullable=True),
        sa.Column('ci_method', sa.String(10), nullable=True),  # 'profiled' or 'vcov'

        # Classification
        sa.Column(
            'curve_category',
            postgresql.ENUM(
                'SIGMOID', 'INACTIVE', 'INVERSE', 'PARTIAL_HIGH', 'PARTIAL_LOW',
                'HOOK_EFFECT', 'NOISY', 'CANNOT_FIT',
                name='curve_category_enum', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('quality_flag', sa.String(20), nullable=False),

        # Point accounting
        sa.Column('points_used', sa.Integer(), nullable=True),
        sa.Column('points_excluded', sa.Integer(), nullable=True),

        # Visualization
        sa.Column('thumbnail_svg', sa.Text(), nullable=True),

        # Review workflow
        sa.Column(
            'review_status',
            postgresql.ENUM(
                'pending', 'approved', 'rejected', 'flagged',
                name='review_status_enum', create_type=False,
            ),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),

        # Fit versioning
        sa.Column('fit_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('superseded_by', postgresql.UUID(as_uuid=True), nullable=True),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('fit_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fit_triggered_by', postgresql.UUID(as_uuid=True), nullable=True),

        # RLS
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.ForeignKeyConstraint(['experiment_run_id'], ['experiment_runs.id']),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['fit_triggered_by'], ['users.id']),
        sa.ForeignKeyConstraint(['superseded_by'], ['dose_response_results.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_drr_experiment_run_id', 'dose_response_results', ['experiment_run_id'])
    op.create_index('idx_drr_sample_id', 'dose_response_results', ['sample_id'])
    op.create_index('idx_drr_curve_category', 'dose_response_results', ['curve_category'])
    op.create_index('idx_drr_review_status', 'dose_response_results', ['review_status'])
    op.create_index('idx_drr_potency', 'dose_response_results', ['potency'])
    op.create_index(
        'idx_drr_run_superseded',
        'dose_response_results',
        ['experiment_run_id', 'superseded_by'],
    )
    op.execute('ALTER TABLE dose_response_results ENABLE ROW LEVEL SECURITY;')
    op.execute("""
        CREATE POLICY dose_response_results_client_isolation
        ON dose_response_results
        USING (client_id = current_setting('app.client_id', true)::uuid);
    """)

    # ── experiment_data_exclusions ─────────────────────────────────────────────
    op.create_table(
        'experiment_data_exclusions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_data_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('excluded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('excluded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['experiment_data_id'], ['experiment_data.id']),
        sa.ForeignKeyConstraint(['excluded_by'], ['users.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('experiment_data_id', name='uq_experiment_data_exclusions_data_id'),
    )
    op.create_index('idx_ede_experiment_data_id', 'experiment_data_exclusions', ['experiment_data_id'])
    op.execute('ALTER TABLE experiment_data_exclusions ENABLE ROW LEVEL SECURITY;')
    op.execute("""
        CREATE POLICY experiment_data_exclusions_client_isolation
        ON experiment_data_exclusions
        USING (client_id = current_setting('app.client_id', true)::uuid);
    """)

    # ── experiment_runs.fit_in_progress ───────────────────────────────────────
    # Mutex to prevent concurrent fits for the same run (R service is single-threaded).
    op.add_column(
        'experiment_runs',
        sa.Column('fit_in_progress', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('experiment_runs', 'fit_in_progress')

    op.execute('DROP TABLE IF EXISTS experiment_data_exclusions CASCADE;')
    op.execute('DROP TABLE IF EXISTS dose_response_results CASCADE;')
    op.execute('DROP TABLE IF EXISTS template_well_definitions CASCADE;')

    op.execute('DROP TYPE IF EXISTS review_status_enum;')
    op.execute('DROP TYPE IF EXISTS curve_category_enum;')
