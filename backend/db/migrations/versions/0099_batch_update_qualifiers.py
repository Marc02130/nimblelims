"""Grant batch:update and fold Result Qualifiers into result_qualifiers.

Revision ID: 0099_batch_update_qualifiers
Revises: 0098_batch_access_status

batch:update has existed since 0006 and was never granted. PATCH /batches/{id}
and PATCH /batches/{id}/status both require it. This grants it to the same
roles that already hold batch:manage: Administrator, Lab Manager, and Lab
Technician. Client and Configuration Editor are left unchanged. batch:delete
is not granted. Upgrade only inserts role_permissions rows.

0060 seeded a display-named list ``Result Qualifiers`` (<LOD, ND) beside the
0046 list ``result_qualifiers``. Entries whose name is not already on
``result_qualifiers`` move there and keep their ids, so results.qualifiers
and every other foreign key stay valid. A name that already exists is not
duplicated: foreign keys are repointed at the surviving entry and the old
entry is marked inactive. The display-named list is then marked inactive.
Nothing is deleted.

The move record is appended to that inactive list's description so downgrade
can put the same rows back. Downgrade does not restore foreign keys that a
name collision repointed; those stay on the surviving result_qualifiers
entry. The seeded names <LOD and ND do not collide, so a downgrade of the
seeded database restores them.

This revision follows 0098_batch_access_status, which is already on main.
It does not change that function.
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0099_batch_update_qualifiers"
down_revision = "0098_batch_access_status"
branch_labels = None
depends_on = None

BATCH_UPDATE_ROLES = ("Administrator", "Lab Manager", "Lab Technician")
OLD_QUALIFIER_LIST_NAME = "Result Qualifiers"
NEW_QUALIFIER_LIST_NAME = "result_qualifiers"
MARKER = "\n[[qualifier-consolidation]]\n"


def upgrade() -> None:
    connection = op.get_bind()
    _grant_batch_update(connection)
    consolidate_qualifier_lists(connection)


def downgrade() -> None:
    connection = op.get_bind()
    restore_qualifier_lists(connection)
    _revoke_batch_update(connection)


def _grant_batch_update(connection) -> None:
    permission_id = connection.execute(
        sa.text("SELECT id FROM permissions WHERE name = 'batch:update'")
    ).scalar()
    if permission_id is None:
        raise RuntimeError("batch:update permission is missing; 0006 should have inserted it")
    for role_name in BATCH_UPDATE_ROLES:
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = 'batch:update'
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_name": role_name},
        )


def _revoke_batch_update(connection) -> None:
    """Remove only the grants this revision adds. The permission row stays."""
    for role_name in BATCH_UPDATE_ROLES:
        connection.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE name = :role_name)
                  AND permission_id = (SELECT id FROM permissions WHERE name = 'batch:update')
                """
            ),
            {"role_name": role_name},
        )


def consolidate_qualifier_lists(connection) -> dict:
    """Move unique Result Qualifiers entries onto result_qualifiers.

    Returns the move record. A second call is a no-op once the marker is stored.
    """
    old = connection.execute(
        sa.text(
            "SELECT id, description FROM lists WHERE name = :name"
        ),
        {"name": OLD_QUALIFIER_LIST_NAME},
    ).fetchone()
    if old is None:
        return {"moved": [], "merged": [], "list_refs": []}
    old_id, description = old[0], old[1]
    text = "" if description is None else description
    if MARKER in text:
        return _payload_from_description(text)

    new_id = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = :name"),
        {"name": NEW_QUALIFIER_LIST_NAME},
    ).scalar()
    if new_id is None:
        raise RuntimeError(
            "result_qualifiers list is missing; 0046 should have inserted it"
        )

    entries = connection.execute(
        sa.text(
            """
            SELECT id, name FROM list_entries
            WHERE list_id = :list_id
            ORDER BY name
            """
        ),
        {"list_id": old_id},
    ).fetchall()

    moved = []
    merged = []
    for entry_id, entry_name in entries:
        survivor_id = connection.execute(
            sa.text(
                """
                SELECT id FROM list_entries
                WHERE list_id = :list_id AND name = :name
                """
            ),
            {"list_id": new_id, "name": entry_name},
        ).scalar()
        if survivor_id is not None and survivor_id != entry_id:
            _repoint_entry_references(connection, entry_id, survivor_id)
            connection.execute(
                sa.text(
                    """
                    UPDATE list_entries
                    SET active = false, modified_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": entry_id},
            )
            merged.append(
                {
                    "id": str(entry_id),
                    "name": entry_name,
                    "survivor_id": str(survivor_id),
                }
            )
            continue
        connection.execute(
            sa.text(
                """
                UPDATE list_entries
                SET list_id = :list_id, modified_at = NOW()
                WHERE id = :id
                """
            ),
            {"list_id": new_id, "id": entry_id},
        )
        moved.append({"id": str(entry_id), "name": entry_name})

    list_refs = _repoint_list_references(connection, old_id, new_id)
    payload = {"moved": moved, "merged": merged, "list_refs": list_refs}
    prefix = text
    if prefix == "":
        stored = MARKER + json.dumps(payload)
    else:
        stored = prefix + MARKER + json.dumps(payload)
    connection.execute(
        sa.text(
            """
            UPDATE lists
            SET active = false, description = :description, modified_at = NOW()
            WHERE id = :id
            """
        ),
        {"description": stored, "id": old_id},
    )
    return payload


def restore_qualifier_lists(connection) -> None:
    """Put moved entries back on Result Qualifiers and mark that list active.

    Foreign keys repointed because of a name collision stay on the surviving
    result_qualifiers entry. Reactivating the inactive duplicate is enough
    for that case; rewriting every row that now points at the survivor would
    also move references that already used the survivor before this revision.
    """
    old = connection.execute(
        sa.text("SELECT id, description FROM lists WHERE name = :name"),
        {"name": OLD_QUALIFIER_LIST_NAME},
    ).fetchone()
    if old is None:
        return
    old_id, description = old[0], old[1]
    text = "" if description is None else description
    if MARKER not in text:
        connection.execute(
            sa.text(
                "UPDATE lists SET active = true, modified_at = NOW() WHERE id = :id"
            ),
            {"id": old_id},
        )
        return
    prefix, payload = _split_description(text)
    for item in payload.get("moved", []):
        connection.execute(
            sa.text(
                """
                UPDATE list_entries
                SET list_id = :list_id, modified_at = NOW()
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"list_id": old_id, "id": item["id"]},
        )
    for item in payload.get("merged", []):
        connection.execute(
            sa.text(
                """
                UPDATE list_entries
                SET active = true, modified_at = NOW()
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": item["id"]},
        )
    for ref in payload.get("list_refs", []):
        table = _quote_ident(ref["table"])
        column = _quote_ident(ref["column"])
        for row_id in ref["row_ids"]:
            connection.execute(
                sa.text(
                    f"""
                    UPDATE {table}
                    SET {column} = :list_id
                    WHERE id = CAST(:row_id AS uuid)
                    """
                ),
                {"list_id": old_id, "row_id": row_id},
            )
    restored = None if prefix == "" else prefix
    connection.execute(
        sa.text(
            """
            UPDATE lists
            SET active = true, description = :description, modified_at = NOW()
            WHERE id = :id
            """
        ),
        {"description": restored, "id": old_id},
    )


def _payload_from_description(description: str) -> dict:
    _prefix, payload = _split_description(description)
    return payload


def _split_description(description: str) -> tuple:
    prefix, raw = description.split(MARKER, 1)
    return prefix, json.loads(raw)


def _repoint_entry_references(connection, old_entry_id, survivor_id) -> None:
    for schema, table, column in _foreign_key_columns(connection, "list_entries", "id"):
        if schema != "public":
            continue
        if table == "list_entries":
            continue
        quoted_table = _quote_ident(table)
        quoted_column = _quote_ident(column)
        connection.execute(
            sa.text(
                f"""
                UPDATE {quoted_table}
                SET {quoted_column} = :survivor
                WHERE {quoted_column} = :old_id
                """
            ),
            {"survivor": survivor_id, "old_id": old_entry_id},
        )


def _repoint_list_references(connection, old_list_id, new_list_id) -> list:
    """Point list-level foreign keys at result_qualifiers and record the row ids."""
    moved_refs = []
    for schema, table, column in _foreign_key_columns(connection, "lists", "id"):
        if schema != "public":
            continue
        # Entry membership is handled above. A merged duplicate stays on the
        # old list so the unique (list_id, name) index is not broken.
        if table == "list_entries":
            continue
        quoted_table = _quote_ident(table)
        quoted_column = _quote_ident(column)
        pk_columns = _primary_key_columns(connection, table)
        if pk_columns != ["id"]:
            count = connection.execute(
                sa.text(
                    f"""
                    SELECT count(*) FROM {quoted_table}
                    WHERE {quoted_column} = :old_id
                    """
                ),
                {"old_id": old_list_id},
            ).scalar()
            if count is not None and count > 0:
                raise RuntimeError(
                    f"Cannot record a downgrade for {table}.{column}: "
                    f"primary key is {pk_columns}"
                )
            continue
        rows = connection.execute(
            sa.text(
                f"""
                SELECT id FROM {quoted_table}
                WHERE {quoted_column} = :old_id
                """
            ),
            {"old_id": old_list_id},
        ).fetchall()
        if not rows:
            continue
        connection.execute(
            sa.text(
                f"""
                UPDATE {quoted_table}
                SET {quoted_column} = :new_id
                WHERE {quoted_column} = :old_id
                """
            ),
            {"new_id": new_list_id, "old_id": old_list_id},
        )
        moved_refs.append(
            {
                "table": table,
                "column": column,
                "row_ids": [str(row[0]) for row in rows],
            }
        )
    return moved_refs


def _foreign_key_columns(connection, referenced_table: str, referenced_column: str):
    return connection.execute(
        sa.text(
            """
            SELECT n.nspname, src.relname, a.attname
            FROM pg_constraint c
            JOIN pg_class src ON src.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = src.relnamespace
            JOIN pg_class dst ON dst.oid = c.confrelid
            JOIN LATERAL unnest(c.conkey, c.confkey) AS cols(src_att, dst_att) ON true
            JOIN pg_attribute a ON a.attrelid = src.oid AND a.attnum = cols.src_att
            JOIN pg_attribute fa ON fa.attrelid = dst.oid AND fa.attnum = cols.dst_att
            WHERE c.contype = 'f'
              AND dst.relname = :referenced_table
              AND fa.attname = :referenced_column
              AND n.nspname = 'public'
              AND src.relkind = 'r'
            """
        ),
        {
            "referenced_table": referenced_table,
            "referenced_column": referenced_column,
        },
    ).fetchall()


def _primary_key_columns(connection, table: str) -> list:
    rows = connection.execute(
        sa.text(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
            WHERE i.indrelid = CAST(:regclass AS regclass)
              AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """
        ),
        {"regclass": f"public.{table}"},
    ).fetchall()
    return [row[0] for row in rows]


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'
