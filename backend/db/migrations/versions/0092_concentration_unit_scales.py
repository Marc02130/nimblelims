"""Mass-concentration scale, and separate activity / copy / count types.

Revision ID: 0092_concentration_unit_scales
Revises: 0091_derivative_transitions

Seed concentration stored several unrelated units at multiplier 1 (g/L,
ng/µL, µg/mL, EU/mL, copies/µL). Conversion is ``value * multiplier`` inside
one unit type, so those rows silently treated 1 EU/mL as 1 g/L.

This migration does not delete rows.

Mass concentration keeps g/L as the base (multiplier 1):

* 1 ng/µL = 1 µg/mL = 1 mg/L = 0.001 g/L
* 1 g/L = 1000 ng/µL
* 1 mg/mL = 1 g/L, so mg/mL is also multiplier 1 (an alias of the base)
* 1 pg/mL = 1e-9 g/L

EU/mL is endotoxin activity and moves to unit type ``activity``.
copies/µL is a nucleic-acid count per volume and moves to ``copy_concentration``.
cfu is a count, not a mass, and moves to ``count``.
Each of those types has its own multiplier-1 unit and does not convert onto
grams per litre.

Molar units are rescaled onto the existing mol/L base (1 mM = 0.001 mol/L).
"""

from alembic import op
import sqlalchemy as sa

revision = "0092_concentration_unit_scales"
down_revision = "0091_derivative_transitions"
branch_labels = None
depends_on = None

UNIT_TYPE_LIST = "88888888-8888-8888-8888-888888888888"

NEW_TYPES = (
    ("activity", "Endotoxin and other biological activity. Not a mass concentration."),
    ("copy_concentration", "Nucleic-acid copy count per volume. Not a mass concentration."),
    ("count", "A count, such as colony-forming units. Not a mass."),
)

# Relative to g/L. 1 mg/mL = 1 g/L, so both multipliers are 1.
MASS_CONCENTRATION = {
    "g/L": "1",
    "mg/mL": "1",
    "mg/L": "0.001",
    "ng/µL": "0.001",
    "µg/mL": "0.001",
    "µg/L": "0.000001",
    "ng/L": "0.000000001",
    "pg/mL": "0.000000001",
}

# Relative to mol/L.
MOLAR = {
    "mol/L": "1",
    "mmol/L": "0.001",
    "mM": "0.001",
    "µM": "0.000001",
    "nM": "0.000000001",
}


def _ensure_type(connection, name: str, description: str):
    connection.execute(
        sa.text(
            """
            INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
            SELECT gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id
            WHERE NOT EXISTS (
                SELECT 1 FROM list_entries
                WHERE list_id = :list_id AND name = :name
            )
            """
        ),
        {"name": name, "description": description, "list_id": UNIT_TYPE_LIST},
    )


def _type_id(connection, name: str):
    row = connection.execute(
        sa.text(
            """
            SELECT id FROM list_entries
            WHERE list_id = :list_id AND name = :name
            ORDER BY active DESC
            LIMIT 1
            """
        ),
        {"list_id": UNIT_TYPE_LIST, "name": name},
    ).fetchone()
    if row is None:
        raise RuntimeError(f"unit type {name} is not in the unit-type list")
    return row[0]


def _set_multiplier(connection, name: str, multiplier: str, type_id=None) -> None:
    if type_id is None:
        connection.execute(
            sa.text(
                """
                UPDATE units
                SET multiplier = :multiplier, modified_at = NOW()
                WHERE name = :name
                """
            ),
            {"name": name, "multiplier": multiplier},
        )
        return
    connection.execute(
        sa.text(
            """
            UPDATE units
            SET multiplier = :multiplier, type = :type_id, modified_at = NOW()
            WHERE name = :name
            """
        ),
        {"name": name, "multiplier": multiplier, "type_id": type_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for name, description in NEW_TYPES:
        _ensure_type(connection, name, description)
    activity = _type_id(connection, "activity")
    copies = _type_id(connection, "copy_concentration")
    count = _type_id(connection, "count")
    for name, multiplier in MASS_CONCENTRATION.items():
        _set_multiplier(connection, name, multiplier)
    for name, multiplier in MOLAR.items():
        _set_multiplier(connection, name, multiplier)
    _set_multiplier(connection, "EU/mL", "1", activity)
    _set_multiplier(connection, "copies/µL", "1", copies)
    _set_multiplier(connection, "cfu", "1", count)


def downgrade() -> None:
    """Restore the pre-0092 multipliers and types. The new list entries stay."""
    connection = op.get_bind()
    concentration = _type_id(connection, "concentration")
    mass = _type_id(connection, "mass")
    _set_multiplier(connection, "ng/µL", "1", concentration)
    _set_multiplier(connection, "µg/mL", "1", concentration)
    _set_multiplier(connection, "mg/mL", "1000", concentration)
    _set_multiplier(connection, "pg/mL", "0.001", concentration)
    _set_multiplier(connection, "EU/mL", "1", concentration)
    _set_multiplier(connection, "copies/µL", "1", concentration)
    _set_multiplier(connection, "mM", "1")
    _set_multiplier(connection, "µM", "0.001")
    _set_multiplier(connection, "nM", "0.000001")
    _set_multiplier(connection, "cfu", "1", mass)
