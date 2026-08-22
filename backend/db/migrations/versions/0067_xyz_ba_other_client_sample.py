"""UAT seed: other-client plasma sample on Sponsor XYZ bioanalytical project.

Revision ID: 0067
Revises: 0066
Create Date: 2026-08-22

TC-S7-001 other-client beat needs a sample on PharmaTest CRO project
``Sponsor XYZ - Bioanalytical Services`` so alice-tech (NovaBio) can
GET/start/link against a true other-client UUID. 0058 seeds the project;
0059 seeds no sample on it.

Idempotent: resolve project / types / status / units by name at runtime
(0058 advertised ids are not always RFC-4122). Do not seed users. Do not
touch has_project_access or compose.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from alembic import op
import sqlalchemy as sa
import uuid

_SEED_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_ID_KEYS = (
    "id",
    "client_id",
    "project_id",
    "user_id",
    "type_id",
    "created_by",
    "modified_by",
    "sample_type",
    "matrix",
    "status",
    "parent_sample_id",
    "container_id",
    "sample_id",
    "qc_type",
    "concentration_units",
    "amount_units",
)

SAMPLE_NAME = "XYZ-BA-0001"
CONTAINER_NAME = "XYZ-BA-0001"
PROJECT_NAME = "Sponsor XYZ - Bioanalytical Services"
PROJECT_ADVERTISED_ID = "proj-cro-sponsor-004"
SAMPLE_SLUG = "sample-xyz-ba-0001"
CONTAINER_SLUG = "cont-xyz-ba-0001"

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def as_id(value: Any) -> Optional[str]:
    """Turn a seed slug into a stable UUID; leave real UUIDs alone."""
    if value is None:
        return None
    text = str(value)
    try:
        return str(uuid.UUID(text))
    except ValueError:
        return str(uuid.uuid5(_SEED_NS, f"nimblelims.seed.{text}"))


def seed_params(data: Optional[dict]) -> Optional[dict]:
    """Copy a seed dict, converting slug PK/FK fields to UUIDs."""
    if data is None:
        return None
    out = dict(data)
    for key in _ID_KEYS:
        if key in out and out[key] is not None:
            out[key] = as_id(out[key])
    return out


def _scalar_id(connection, sql: str, **params: Any) -> Optional[str]:
    row = connection.execute(sa.text(sql), params).fetchone()
    return str(row[0]) if row else None


def _list_entry_id(
    connection,
    list_name: str,
    entry_name: str,
    fallback_entry: Optional[str] = None,
) -> Optional[str]:
    list_id = _scalar_id(
        connection,
        "SELECT id FROM lists WHERE name = :n LIMIT 1",
        n=list_name,
    )
    if list_id:
        entry_id = _scalar_id(
            connection,
            """
            SELECT id FROM list_entries
            WHERE name = :n AND list_id = CAST(:lid AS uuid)
            LIMIT 1
            """,
            n=entry_name,
            lid=list_id,
        )
        if entry_id:
            return entry_id
        if fallback_entry:
            return _scalar_id(
                connection,
                """
                SELECT id FROM list_entries
                WHERE name = :n AND list_id = CAST(:lid AS uuid)
                LIMIT 1
                """,
                n=fallback_entry,
                lid=list_id,
            )
        return None
    entry_id = _scalar_id(
        connection,
        "SELECT id FROM list_entries WHERE name = :n LIMIT 1",
        n=entry_name,
    )
    if entry_id:
        return entry_id
    if fallback_entry:
        return _scalar_id(
            connection,
            "SELECT id FROM list_entries WHERE name = :n LIMIT 1",
            n=fallback_entry,
        )
    return None


def _resolve_cro_project_id(connection) -> Optional[str]:
    advertised_id = as_id(PROJECT_ADVERTISED_ID)
    return _scalar_id(
        connection,
        """
        SELECT id FROM projects
        WHERE name = :name OR id = CAST(:advertised_id AS uuid)
        ORDER BY CASE WHEN name = :name THEN 0 ELSE 1 END
        LIMIT 1
        """,
        name=PROJECT_NAME,
        advertised_id=advertised_id,
    )


def _resolve_container_type_id(connection) -> Optional[str]:
    for type_name in (
        "Cryovial (2mL)",
        "K2EDTA Tube (5mL)",
        "Microcentrifuge Tube (1.5mL)",
    ):
        type_id = _scalar_id(
            connection,
            "SELECT id FROM container_types WHERE name = :n LIMIT 1",
            n=type_name,
        )
        if type_id:
            return type_id
    return None


def upgrade() -> None:
    connection = op.get_bind()

    project_id = _resolve_cro_project_id(connection)
    if not project_id:
        return

    plasma_type_id = _list_entry_id(
        connection, "Sample Types", "Plasma", fallback_entry="Blood"
    )
    plasma_matrix_id = _list_entry_id(
        connection, "Matrix Types", "Plasma (K2EDTA)", fallback_entry="Plasma"
    )
    available_status_id = _list_entry_id(
        connection, "Sample Status", "Available for Testing"
    )
    if not plasma_type_id or not plasma_matrix_id or not available_status_id:
        return

    qc_sample_id = _list_entry_id(connection, "QC Types", "Sample")
    ul_id = _scalar_id(connection, "SELECT id FROM units WHERE name = 'µL' LIMIT 1")
    created_by = _scalar_id(
        connection, "SELECT id FROM users WHERE username = 'admin' LIMIT 1"
    ) or _scalar_id(
        connection, "SELECT id FROM users WHERE username = 'david-cro' LIMIT 1"
    )

    today = datetime.now(timezone.utc)
    received_date = today - timedelta(days=2)
    due_date = today + timedelta(days=14)

    sample_id = _scalar_id(
        connection,
        "SELECT id FROM samples WHERE name = :n LIMIT 1",
        n=SAMPLE_NAME,
    )
    if not sample_id:
        sample_id = as_id(SAMPLE_SLUG)
        connection.execute(
            sa.text(
                """
                INSERT INTO samples (
                    id, name, description, active, created_at, modified_at,
                    project_id, sample_type, matrix, status, received_date,
                    due_date, temperature, qc_type, parent_sample_id,
                    created_by, modified_by
                )
                VALUES (
                    :id, :name, :description, true, :received_date, :received_date,
                    :project_id, :sample_type, :matrix, :status, :received_date,
                    :due_date, :temperature, :qc_type, :parent_sample_id,
                    :created_by, :created_by
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            seed_params(
                {
                    "id": sample_id,
                    "name": SAMPLE_NAME,
                    "description": (
                        "Sponsor XYZ bioanalytical plasma PK sample, subject 001, "
                        "K2EDTA, stored at -80°C for ELISA/qPCR."
                    ),
                    "project_id": project_id,
                    "sample_type": plasma_type_id,
                    "matrix": plasma_matrix_id,
                    "status": available_status_id,
                    "received_date": received_date,
                    "due_date": due_date,
                    "temperature": -80.0,
                    "qc_type": qc_sample_id,
                    "parent_sample_id": None,
                    "created_by": created_by,
                }
            ),
        )
        sample_id = _scalar_id(
            connection,
            "SELECT id FROM samples WHERE name = :n LIMIT 1",
            n=SAMPLE_NAME,
        )
        if not sample_id:
            return

    type_id = _resolve_container_type_id(connection)
    if not type_id or not sample_id:
        return

    container_id = _scalar_id(
        connection,
        "SELECT id FROM containers WHERE name = :n LIMIT 1",
        n=CONTAINER_NAME,
    )
    if not container_id:
        container_id = as_id(CONTAINER_SLUG)
        connection.execute(
            sa.text(
                """
                INSERT INTO containers (
                    id, name, active, created_at, modified_at, type_id, row,
                    "column", concentration, concentration_units, amount,
                    amount_units, created_by, modified_by
                )
                VALUES (
                    :id, :name, true, NOW(), NOW(), :type_id, :row, :column,
                    :concentration, :concentration_units, :amount,
                    :amount_units, :created_by, :created_by
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            seed_params(
                {
                    "id": container_id,
                    "name": CONTAINER_NAME,
                    "type_id": type_id,
                    "row": 1,
                    "column": 1,
                    "concentration": None,
                    "concentration_units": None,
                    "amount": 500,
                    "amount_units": ul_id,
                    "created_by": created_by,
                }
            ),
        )
        container_id = _scalar_id(
            connection,
            "SELECT id FROM containers WHERE name = :n LIMIT 1",
            n=CONTAINER_NAME,
        ) or container_id

    connection.execute(
        sa.text(
            """
            INSERT INTO contents (
                container_id, sample_id, concentration, concentration_units,
                amount, amount_units
            )
            VALUES (
                :container_id, :sample_id, :concentration, :concentration_units,
                :amount, :amount_units
            )
            ON CONFLICT (container_id, sample_id) DO NOTHING
            """
        ),
        seed_params(
            {
                "container_id": container_id,
                "sample_id": sample_id,
                "concentration": None,
                "concentration_units": None,
                "amount": 500,
                "amount_units": ul_id,
            }
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    sample_id = _scalar_id(
        connection,
        "SELECT id FROM samples WHERE name = :n LIMIT 1",
        n=SAMPLE_NAME,
    )
    container_id = _scalar_id(
        connection,
        "SELECT id FROM containers WHERE name = :n LIMIT 1",
        n=CONTAINER_NAME,
    )
    sample_ids = [sid for sid in (sample_id, as_id(SAMPLE_SLUG)) if sid]
    container_ids = [cid for cid in (container_id, as_id(CONTAINER_SLUG)) if cid]

    if sample_ids:
        connection.execute(
            sa.text("DELETE FROM contents WHERE sample_id = ANY(:ids)"),
            {"ids": sample_ids},
        )
    if container_ids:
        connection.execute(
            sa.text("DELETE FROM contents WHERE container_id = ANY(:ids)"),
            {"ids": container_ids},
        )
    connection.execute(
        sa.text("DELETE FROM samples WHERE name = :n"),
        {"n": SAMPLE_NAME},
    )
    connection.execute(
        sa.text("DELETE FROM containers WHERE name = :n"),
        {"n": CONTAINER_NAME},
    )
