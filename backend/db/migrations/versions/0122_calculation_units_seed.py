"""Additive units seed for the calculation catalog (CALC-REQ-28).

Revision ID: 0122_calculation_units_seed
Revises: 0121_shared_reason_rules

Inserts three unit types and three units, each multiplier 1 in its own type:

* ``OD`` (type ``absorbance``)
* ``s`` (type ``time``)
* ``1`` (type ``dimensionless``)

Upgrade only inserts. It does not update or delete an existing row, and it
does not enable row-level security. ``units`` stays shared reference data
with no RLS policy (OQ-CALC-44, decided: the factor lookup does not run
under row-level security).

A row that already has the same name and already matches this seed is left
alone. A row that already has the name but does not match is a conflict:
upgrade raises and does not change that row. Downgrade deletes only the rows
this migration inserted (matched by the seed description).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from alembic import op
import sqlalchemy as sa

revision = "0122_calculation_units_seed"
down_revision = "0121_shared_reason_rules"
branch_labels = None
depends_on = None

UNIT_TYPE_LIST = "88888888-8888-8888-8888-888888888888"

# (unit name, type name, unit description, type description)
SEED = (
    (
        "OD",
        "absorbance",
        "Absorbance. Seeded multiplier 1 (calculations S4).",
        "Absorbance. OD is multiplier 1 in this type.",
    ),
    (
        "s",
        "time",
        "Time. Seeded multiplier 1 (calculations S4).",
        "Time. s is multiplier 1 in this type.",
    ),
    (
        "1",
        "dimensionless",
        "Dimensionless. Seeded multiplier 1 (calculations S4).",
        "Dimensionless. 1 is multiplier 1 in this type.",
    ),
)


def _is_one(text: object) -> bool:
    if text is None:
        return False
    try:
        return Decimal(str(text)) == Decimal("1")
    except (InvalidOperation, ValueError):
        return False


def _type_id(connection, name: str):
    return connection.execute(
        sa.text(
            """
            SELECT id FROM list_entries
            WHERE list_id = :list_id AND name = :name
            LIMIT 1
            """
        ),
        {"list_id": UNIT_TYPE_LIST, "name": name},
    ).scalar()


def _ensure_type(connection, name: str, description: str):
    existing = _type_id(connection, name)
    if existing is not None:
        return existing
    connection.execute(
        sa.text(
            """
            INSERT INTO list_entries (
                id, name, description, code, active, created_at, modified_at, list_id
            )
            SELECT gen_random_uuid(), :name, :description, NULL, true, NOW(), NOW(), :list_id
            WHERE NOT EXISTS (
                SELECT 1 FROM list_entries
                WHERE list_id = :list_id AND name = :name
            )
            """
        ),
        {"name": name, "description": description, "list_id": UNIT_TYPE_LIST},
    )
    inserted = _type_id(connection, name)
    if inserted is None:
        raise RuntimeError(f"unit type {name} was not inserted")
    return inserted


def _ensure_unit(connection, name: str, description: str, type_name: str, type_id) -> None:
    row = connection.execute(
        sa.text(
            """
            SELECT u.multiplier::text AS multiplier_text,
                   u.active AS active,
                   t.name AS type_name
            FROM units u
            JOIN list_entries t ON t.id = u.type
            WHERE u.name = :name
            """
        ),
        {"name": name},
    ).mappings().first()
    if row is not None:
        if row["active"] is True and _is_one(row["multiplier_text"]) and row["type_name"] == type_name:
            return
        raise RuntimeError(
            f"unit {name!r} already exists and does not match the S4 seed "
            f"(type {row['type_name']!r}, multiplier {row['multiplier_text']!r}, "
            f"active {row['active']!r}). Upgrade does not change an existing unit."
        )
    connection.execute(
        sa.text(
            """
            INSERT INTO units (
                id, name, description, active, created_at, modified_at, multiplier, type
            )
            SELECT gen_random_uuid(), :name, :description, true, NOW(), NOW(),
                   CAST('1' AS numeric(20, 10)), :type_id
            WHERE NOT EXISTS (SELECT 1 FROM units WHERE name = :name)
            """
        ),
        {"name": name, "description": description, "type_id": type_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for unit_name, type_name, unit_description, type_description in SEED:
        type_id = _ensure_type(connection, type_name, type_description)
        _ensure_unit(connection, unit_name, unit_description, type_name, type_id)


def downgrade() -> None:
    """Delete only the rows this migration inserted. No other unit changes."""
    connection = op.get_bind()
    for unit_name, type_name, unit_description, type_description in SEED:
        connection.execute(
            sa.text(
                """
                DELETE FROM units
                WHERE name = :name AND description = :description
                """
            ),
            {"name": unit_name, "description": unit_description},
        )
        connection.execute(
            sa.text(
                """
                DELETE FROM list_entries
                WHERE list_id = :list_id
                  AND name = :name
                  AND description = :description
                  AND NOT EXISTS (
                      SELECT 1 FROM units WHERE units.type = list_entries.id
                  )
                """
            ),
            {
                "list_id": UNIT_TYPE_LIST,
                "name": type_name,
                "description": type_description,
            },
        )
