"""Join the configuring-agent and password-reset heads.

Revision ID: 0085_join_agent_reset
Revises: 0083, 0084_password_reset

0083 (configuring agent) and 0084_password_reset both revise 0082. After
origin/main was merged into configuring-agent, `alembic upgrade head`
stopped with two heads. This revision adds no schema. A database that
already has both schemas but only one stamp still needs the missing
revision row before this upgrade, or Alembic will try to create the
tables again.
"""

revision = "0085_join_agent_reset"
down_revision = ("0083", "0084_password_reset")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
