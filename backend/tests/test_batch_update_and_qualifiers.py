"""batch:update grants and the Result Qualifiers consolidation.

The create_all database has no seed, so the collision and id-preserving move
are exercised by calling the migration helpers. The migrated database is the
real 0046/0060 seed: <LOD and ND land on result_qualifiers, and downgrade
puts them back without dropping the batch access function from 0098.
"""
from __future__ import annotations

import importlib.util
import inspect
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from models.analysis import Analyte, Analysis
from models.client import Client
from models.field_definition import FieldDefinition
from models.list import List, ListEntry
from models.project import Project
from models.result import Result
from models.sample import Sample
from models.test import Test
from tests._fk_helpers import scratch_entry_id

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "versions"
    / "0099_batch_update_qualifiers.py"
)
GRANTED_ROLES = ("Administrator", "Lab Manager", "Lab Technician")


def _migration():
    spec = importlib.util.spec_from_file_location(
        "mig_0099_batch_update_qualifiers", MIGRATION
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_does_not_delete_rows():
    module = _migration()
    source = "\n".join(
        inspect.getsource(fn)
        for fn in (
            module.upgrade,
            module._grant_batch_update,
            module.consolidate_qualifier_lists,
            module._repoint_entry_references,
            module._repoint_list_references,
        )
    )
    assert "DELETE" not in source
    assert "DROP" not in source
    revoke = inspect.getsource(module._revoke_batch_update)
    assert "DELETE FROM role_permissions" in revoke
    assert "DELETE FROM permissions" not in revoke
    assert "DELETE FROM list_entries" not in inspect.getsource(module.restore_qualifier_lists)


def _world(db_session, admin):
    suffix = uuid4().hex[:8]
    org = Client(
        name=f"Qual Org {suffix}",
        description="qualifier consolidation",
        billing_info={},
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(org)
    db_session.flush()
    project = Project(
        name=f"Qual Project {suffix}",
        description="qualifier consolidation",
        start_date=datetime(2026, 1, 1, 0, 0),
        client_id=org.id,
        status=scratch_entry_id(db_session),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"QUAL-SAMPLE-{suffix}",
        description="qualifier consolidation",
        sample_type=scratch_entry_id(db_session),
        status=scratch_entry_id(db_session),
        matrix=scratch_entry_id(db_session),
        project_id=project.id,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(sample)
    db_session.flush()
    analysis = Analysis(
        name=f"Qual Analysis {suffix}",
        description="qualifier consolidation",
        created_by=admin.id,
        modified_by=admin.id,
    )
    analyte = Analyte(
        name=f"Qual Analyte {suffix}",
        description="qualifier consolidation",
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add_all([analysis, analyte])
    db_session.flush()
    test = Test(
        name=f"QUAL-TEST-{suffix}",
        description="qualifier consolidation",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=scratch_entry_id(db_session),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(test)
    db_session.flush()
    return test, analyte


def test_unique_entries_keep_ids_and_collisions_repoint(db_session, test_admin_user):
    module = _migration()
    admin = test_admin_user
    # create_all copies BaseModel's unique name. The migrated schema allows
    # the same entry name on two lists (0005 is unique on list_id, name).
    db_session.execute(text("ALTER TABLE list_entries DROP CONSTRAINT IF EXISTS list_entries_name_key"))
    db_session.commit()
    original = "Result qualifiers for reported values"
    old = List(
        name="Result Qualifiers",
        description=original,
        created_by=admin.id,
        modified_by=admin.id,
    )
    new = List(
        name="result_qualifiers",
        description="Result qualifiers / flags (list-backed)",
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add_all([old, new])
    db_session.flush()
    lod = ListEntry(
        list_id=old.id, name="<LOD", description="Below limit of detection",
        created_by=admin.id, modified_by=admin.id,
    )
    nd = ListEntry(
        list_id=old.id, name="ND", description="Not detected",
        created_by=admin.id, modified_by=admin.id,
    )
    duplicate = ListEntry(
        list_id=old.id, name="Normal", description="from the display list",
        created_by=admin.id, modified_by=admin.id,
    )
    survivor = ListEntry(
        list_id=new.id, name="Normal", description="already on result_qualifiers",
        created_by=admin.id, modified_by=admin.id,
    )
    db_session.add_all([lod, nd, duplicate, survivor])
    db_session.flush()
    test, analyte = _world(db_session, admin)
    kept = Result(
        test_id=test.id, analyte_id=analyte.id, raw_result="<LOD",
        qualifiers=lod.id, entered_by=admin.id, created_by=admin.id, modified_by=admin.id,
    )
    moved_fk = Result(
        test_id=test.id, analyte_id=analyte.id, raw_result="1",
        qualifiers=duplicate.id, entered_by=admin.id, created_by=admin.id, modified_by=admin.id,
    )
    field = FieldDefinition(
        name=f"qual_field_{uuid4().hex[:8]}",
        entity_type="result",
        data_type="list",
        source_list_id=old.id,
        is_required=False,
        is_unique=False,
        is_materialized_column=False,
        active=True,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add_all([kept, moved_fk, field])
    db_session.flush()
    lod_id = lod.id
    duplicate_id = duplicate.id
    survivor_id = survivor.id

    payload = module.consolidate_qualifier_lists(db_session.connection())
    db_session.expire_all()

    assert {item["name"] for item in payload["moved"]} == {"<LOD", "ND"}
    assert payload["merged"] == [
        {"id": str(duplicate_id), "name": "Normal", "survivor_id": str(survivor_id)}
    ]
    assert any(ref["table"] == "field_definitions" for ref in payload["list_refs"])
    assert db_session.get(ListEntry, lod_id).list_id == new.id
    assert db_session.get(ListEntry, lod_id).id == lod_id
    assert db_session.get(Result, kept.id).qualifiers == lod_id
    assert db_session.get(Result, moved_fk.id).qualifiers == survivor_id
    assert db_session.get(ListEntry, duplicate_id).active is False
    assert db_session.get(ListEntry, duplicate_id).list_id == old.id
    assert db_session.get(FieldDefinition, field.id).source_list_id == new.id
    assert db_session.get(List, old.id).active is False

    again = module.consolidate_qualifier_lists(db_session.connection())
    assert {item["name"] for item in again["moved"]} == {"<LOD", "ND"}

    module.restore_qualifier_lists(db_session.connection())
    db_session.expire_all()
    assert db_session.get(ListEntry, lod_id).list_id == old.id
    assert db_session.get(List, old.id).active is True
    assert db_session.get(List, old.id).description == original
    assert db_session.get(ListEntry, duplicate_id).active is True
    # A name collision cannot tell which foreign keys already used the survivor.
    assert db_session.get(Result, moved_fk.id).qualifiers == survivor_id
    assert db_session.get(FieldDefinition, field.id).source_list_id == old.id


def _roles_with_batch_update(conn):
    rows = conn.execute(
        text(
            """
            SELECT r.name
            FROM roles r
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.name = 'batch:update'
            ORDER BY r.name
            """
        )
    ).fetchall()
    return [row[0] for row in rows]


def _entry_home(conn, entry_name):
    return conn.execute(
        text(
            """
            SELECT lists.name, lists.active, list_entries.id::text, list_entries.active
            FROM list_entries
            JOIN lists ON lists.id = list_entries.list_id
            WHERE list_entries.name = :name
            ORDER BY lists.name
            """
        ),
        {"name": entry_name},
    ).fetchall()


def test_seeded_grant_and_qualifier_move_round_trip(migrated_engine):
    """0099 on the real seed. Downgrade stops at 0098 and leaves the probe."""
    from alembic import command
    from alembic.config import Config

    url = migrated_engine.url.render_as_string(hide_password=False)
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        with migrated_engine.connect() as conn:
            assert _roles_with_batch_update(conn) == list(GRANTED_ROLES)
            lod = _entry_home(conn, "<LOD")
            nd = _entry_home(conn, "ND")
            assert [row[0] for row in lod] == ["result_qualifiers"]
            assert [row[0] for row in nd] == ["result_qualifiers"]
            assert lod[0][1] is True and lod[0][3] is True
            lod_id = lod[0][2]
            nd_id = nd[0][2]
            old = conn.execute(
                text(
                    "SELECT active, description FROM lists WHERE name = 'Result Qualifiers'"
                )
            ).one()
            assert old[0] is False
            assert "[[qualifier-consolidation]]" in old[1]
            normal = _entry_home(conn, "Normal")
            assert [row[0] for row in normal] == ["result_qualifiers"]

        command.downgrade(cfg, "0098_batch_access_status")
        with migrated_engine.connect() as conn:
            assert _roles_with_batch_update(conn) == []
            assert [row[0] for row in _entry_home(conn, "<LOD")] == ["Result Qualifiers"]
            assert _entry_home(conn, "<LOD")[0][2] == lod_id
            assert _entry_home(conn, "ND")[0][2] == nd_id
            restored = conn.execute(
                text(
                    "SELECT active, description FROM lists WHERE name = 'Result Qualifiers'"
                )
            ).one()
            assert restored[0] is True
            assert restored[1] == "Result qualifiers for reported values"
            probe = conn.execute(
                text(
                    """
                    SELECT 1 FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public' AND p.proname = 'batch_access_status'
                    """
                )
            ).scalar()
            assert probe == 1
    finally:
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate
        with migrated_engine.connect() as conn:
            assert _roles_with_batch_update(conn) == list(GRANTED_ROLES)
            assert [row[0] for row in _entry_home(conn, "<LOD")] == ["result_qualifiers"]
