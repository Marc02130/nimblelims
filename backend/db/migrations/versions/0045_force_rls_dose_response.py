"""Add FORCE ROW LEVEL SECURITY to dose-response and template-well tables

Revision ID: 0045
Revises: 0044
Create Date: 2026-04-02

Migration 0043 enabled RLS on three new tables but did not add FORCE ROW LEVEL
SECURITY. Without FORCE, table owners and superusers (including lims_user, which
the app runs as) bypass RLS entirely. Migration 0041 set FORCE on all prior tables;
this migration closes the gap for the three tables added in 0043.

Tables affected:
  - template_well_definitions
  - dose_response_results
  - experiment_data_exclusions
"""
from alembic import op

revision = '0045'
down_revision = '0044'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE template_well_definitions FORCE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE dose_response_results FORCE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiment_data_exclusions FORCE ROW LEVEL SECURITY;')


def downgrade() -> None:
    op.execute('ALTER TABLE experiment_data_exclusions NO FORCE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE dose_response_results NO FORCE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE template_well_definitions NO FORCE ROW LEVEL SECURITY;')
