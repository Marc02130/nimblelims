"""Revoke DELETE on the reagent tables from lims_app.

Revision ID: 0109_revoke_reagent_delete
Revises: 0108_elisa_followups

0090 ``_secure`` gave lims_app DELETE on vendors, reagents, reagent_vendors,
reagent_lots, and reagent_uses. The product retires those rows with ``active``
false and has no DELETE route. This revision revokes DELETE only. It adds no
privilege and drops nothing. Downgrade does not hand DELETE back.
"""
from __future__ import annotations

from alembic import op

revision = "0109_revoke_reagent_delete"
down_revision = "0108_elisa_followups"
branch_labels = None
depends_on = None

REAGENT_TABLES = ("vendors", "reagents", "reagent_vendors", "reagent_lots", "reagent_uses")


def upgrade() -> None:
    for table in REAGENT_TABLES:
        op.execute(f"REVOKE DELETE ON TABLE {table} FROM lims_app")


def downgrade() -> None:
    pass
