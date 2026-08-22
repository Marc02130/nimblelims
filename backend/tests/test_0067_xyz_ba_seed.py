"""Static checks for Alembic 0067 other-client UAT sample seed.

These tests do not need a database. They lock revision chaining, the
advertised sample name, runtime name resolution, and the no-AuthZ /
no-user-seed / no-compose constraints.
"""
import importlib.util
import uuid
from pathlib import Path

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
    assert "has_project_access" not in source
    assert "INSERT INTO users" not in source
    assert "5432" not in source
    assert "docker-compose" not in source
    assert "project_users" not in source
