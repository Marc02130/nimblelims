"""Static checks for Alembic 0067 other-client UAT sample seed.

These tests do not need a database. They lock revision chaining, the
advertised sample name, runtime name resolution, and the no-AuthZ /
no-user-seed / no-compose constraints.
"""
import importlib.util
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_0067 = (
    BACKEND_DIR
    / "db"
    / "migrations"
    / "versions"
    / "0067_xyz_ba_other_client_sample.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("seed_0067", MIGRATION_0067)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0067_chains_from_0066():
    mod = _load_migration()
    assert mod.revision == "0067"
    assert mod.down_revision == "0066"


def test_0067_as_id_converts_slugs_and_preserves_uuids():
    mod = _load_migration()
    slug_id = mod.as_id("sample-xyz-ba-0001")
    real_uuid = "5a35c49d-96d7-51cd-a8fb-8634e8653a02"
    uuid.UUID(slug_id)
    assert slug_id != "sample-xyz-ba-0001"
    assert mod.as_id(real_uuid) == real_uuid
    assert mod.as_id(None) is None
    advertised = mod.as_id("proj-cro-sponsor-004")
    uuid.UUID(advertised)
    assert advertised != "proj-cro-sponsor-004"


def test_0067_seed_params_converts_sample_fk_keeps_name():
    mod = _load_migration()
    out = mod.seed_params(
        {
            "id": "sample-xyz-ba-0001",
            "name": "XYZ-BA-0001",
            "parent_sample_id": None,
            "project_id": "proj-cro-sponsor-004",
        }
    )
    uuid.UUID(out["id"])
    uuid.UUID(out["project_id"])
    assert out["name"] == "XYZ-BA-0001"
    assert out["parent_sample_id"] is None


def test_0067_source_is_idempotent_named_seed():
    source = MIGRATION_0067.read_text()
    assert 'SAMPLE_NAME = "XYZ-BA-0001"' in source
    assert "Sponsor XYZ - Bioanalytical Services" in source
    assert "proj-cro-sponsor-004" in source
    assert "Available for Testing" in source
    assert "Plasma (K2EDTA)" in source
    assert 'fallback_entry="Blood"' in source
    assert "ON CONFLICT (id) DO NOTHING" in source
    assert "ON CONFLICT (container_id, sample_id) DO NOTHING" in source
    assert "parent_sample_id" in source
    assert '"parent_sample_id": None' in source
    assert "INSERT INTO samples" in source
    assert "INSERT INTO containers" in source
    assert "INSERT INTO contents" in source


def test_0067_does_not_touch_authz_users_or_compose():
    source = MIGRATION_0067.read_text()
    assert "CREATE OR REPLACE FUNCTION has_project_access" not in source
    assert "INSERT INTO users" not in source
    assert "5432" not in source
    assert "docker-compose" not in source
    assert "INSERT INTO project_users" not in source


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    """Name-resolving bind that records INSERT/DELETE without Postgres."""

    def __init__(self):
        self.statements = []
        self.samples_by_name = {}
        self.containers_by_name = {}
        self.ids = {
            "project": str(uuid.uuid4()),
            "list-sample-types": str(uuid.uuid4()),
            "list-matrix-types": str(uuid.uuid4()),
            "list-sample-status": str(uuid.uuid4()),
            "list-qc-types": str(uuid.uuid4()),
            "entry-plasma": str(uuid.uuid4()),
            "entry-k2edta": str(uuid.uuid4()),
            "entry-available": str(uuid.uuid4()),
            "entry-qc-sample": str(uuid.uuid4()),
            "unit-ul": str(uuid.uuid4()),
            "user-admin": str(uuid.uuid4()),
            "ctype-cryovial": str(uuid.uuid4()),
        }

    def execute(self, stmt, params=None):
        sql = str(stmt)
        params = params or {}
        self.statements.append((sql, dict(params)))
        upper = sql.upper()

        if "INSERT INTO SAMPLES" in upper:
            name = params.get("name")
            sample_id = params.get("id")
            self.samples_by_name[name] = sample_id
            return _FakeResult(None)
        if "INSERT INTO CONTAINERS" in upper:
            name = params.get("name")
            container_id = params.get("id")
            self.containers_by_name[name] = container_id
            return _FakeResult(None)
        if "INSERT INTO CONTENTS" in upper:
            return _FakeResult(None)
        if "DELETE FROM" in upper:
            return _FakeResult(None)

        if "FROM PROJECTS" in upper:
            return _FakeResult((self.ids["project"],))
        if "FROM LISTS" in upper:
            name = params.get("n")
            mapping = {
                "Sample Types": "list-sample-types",
                "Matrix Types": "list-matrix-types",
                "Sample Status": "list-sample-status",
                "QC Types": "list-qc-types",
            }
            key = mapping.get(name)
            return _FakeResult((self.ids[key],) if key else None)
        if "FROM LIST_ENTRIES" in upper:
            name = params.get("n")
            mapping = {
                "Plasma": "entry-plasma",
                "Plasma (K2EDTA)": "entry-k2edta",
                "Available for Testing": "entry-available",
                "Sample": "entry-qc-sample",
            }
            key = mapping.get(name)
            return _FakeResult((self.ids[key],) if key else None)
        if "FROM UNITS" in upper:
            return _FakeResult((self.ids["unit-ul"],))
        if "FROM USERS" in upper:
            return _FakeResult((self.ids["user-admin"],))
        if "FROM CONTAINER_TYPES" in upper:
            return _FakeResult((self.ids["ctype-cryovial"],))
        if "FROM SAMPLES" in upper:
            name = params.get("n")
            sid = self.samples_by_name.get(name)
            return _FakeResult((sid,) if sid else None)
        if "FROM CONTAINERS" in upper:
            name = params.get("n")
            cid = self.containers_by_name.get(name)
            return _FakeResult((cid,) if cid else None)
        return _FakeResult(None)


def test_0067_upgrade_inserts_named_plasma_tube_once():
    mod = _load_migration()
    conn = _FakeConnection()
    with patch.object(mod.op, "get_bind", return_value=conn):
        mod.upgrade()
        first_insert_count = sum(
            1 for sql, _ in conn.statements if "INSERT INTO" in sql.upper()
        )
        mod.upgrade()
    assert first_insert_count == 3

    sample_inserts = [
        params
        for sql, params in conn.statements
        if "INSERT INTO SAMPLES" in sql.upper()
    ]
    assert len(sample_inserts) == 1
    assert sample_inserts[0]["name"] == "XYZ-BA-0001"
    assert sample_inserts[0]["parent_sample_id"] is None
    uuid.UUID(str(sample_inserts[0]["project_id"]))
    uuid.UUID(str(sample_inserts[0]["sample_type"]))
    uuid.UUID(str(sample_inserts[0]["matrix"]))
    uuid.UUID(str(sample_inserts[0]["status"]))

    container_inserts = [
        params
        for sql, params in conn.statements
        if "INSERT INTO CONTAINERS" in sql.upper()
    ]
    assert len(container_inserts) == 1
    assert container_inserts[0]["name"] == "XYZ-BA-0001"

    content_inserts = [
        params
        for sql, params in conn.statements
        if "INSERT INTO CONTENTS" in sql.upper()
    ]
    assert len(content_inserts) == 2
    assert content_inserts[0]["sample_id"] == sample_inserts[0]["id"]
    assert content_inserts[0]["container_id"] == container_inserts[0]["id"]

    user_inserts = [
        sql for sql, _ in conn.statements if "INSERT INTO USERS" in sql.upper()
    ]
    assert user_inserts == []
