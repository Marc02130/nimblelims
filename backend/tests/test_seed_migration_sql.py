"""Regression tests for BioTech seed migrations 0058/0059 SQL bind handling.

These tests do not need a database. They catch the two startup failures:
- slug strings inserted into UUID columns
- PostgreSQL ``::jsonb`` casts on SQLAlchemy bind params
"""
import importlib.util
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS = BACKEND_DIR / "db" / "migrations" / "versions"
MIGRATION_0058 = MIGRATIONS / "0058_biotech_comprehensive_seed.py"
MIGRATION_0059 = MIGRATIONS / "0059_biotech_sample_lifecycle_data.py"


def _load_migration(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0058_uses_cast_for_billing_info_jsonb():
    source = MIGRATION_0058.read_text()
    assert ":billing_info::jsonb" not in source
    assert "CAST(:billing_info AS jsonb)" in source


def test_jsonb_bind_compiles_to_psycopg2_placeholder():
    stmt = text(
        "INSERT INTO clients (billing_info) VALUES (CAST(:billing_info AS jsonb))"
    )
    compiled = str(stmt.compile(dialect=postgresql_dialect()))
    assert "%(billing_info)s" in compiled
    assert ":billing_info" not in compiled


def test_double_colon_jsonb_bind_does_not_compile_cleanly():
    """Document the SQLAlchemy/psycopg2 failure mode this migration hit."""
    stmt = text(
        "INSERT INTO clients (billing_info) VALUES (:billing_info::jsonb)"
    )
    compiled = str(stmt.compile(dialect=postgresql_dialect()))
    assert ":billing_info::jsonb" in compiled


def test_0058_as_id_converts_slugs_and_preserves_uuids():
    mod = _load_migration(MIGRATION_0058, "seed_0058")
    slug_id = mod.as_id("ctype-001-cryovial")
    real_uuid = "5a35c49d-96d7-51cd-a8fb-8634e8653a02"
    uuid.UUID(slug_id)
    assert slug_id != "ctype-001-cryovial"
    assert mod.as_id(real_uuid) == real_uuid
    assert mod.as_id(None) is None


def test_0058_seed_params_converts_id_keeps_billing_info():
    mod = _load_migration(MIGRATION_0058, "seed_0058_params")
    out = mod.seed_params({
        "id": "client-biotech-001",
        "name": "NovaBio Therapeutics",
        "billing_info": '{"city": "South San Francisco"}',
    })
    uuid.UUID(out["id"])
    assert out["name"] == "NovaBio Therapeutics"
    assert "South San Francisco" in out["billing_info"]


def test_0059_seed_params_converts_sample_and_parent_ids():
    mod = _load_migration(MIGRATION_0059, "seed_0059")
    out = mod.seed_params({
        "id": "sample-mab-pk-t0-aliquot",
        "parent_sample_id": "sample-mab-pk-t0",
        "name": "mAb-2301-PK-T0-Aliq",
    })
    uuid.UUID(out["id"])
    uuid.UUID(out["parent_sample_id"])
    assert out["id"] != "sample-mab-pk-t0-aliquot"
    assert out["parent_sample_id"] != "sample-mab-pk-t0"
    assert out["name"] == "mAb-2301-PK-T0-Aliq"


def test_0058_unique_name_tables_conflict_on_name():
    source = MIGRATION_0058.read_text()
    assert "INSERT INTO analyses" in source
    analyses_block = source.split("INSERT INTO analyses", 1)[1].split("for analysis in", 1)[0]
    assert "ON CONFLICT (name) DO NOTHING" in analyses_block

    source = MIGRATION_0058.read_text()
    assert "start_date" in source
    assert "INSERT INTO projects" in source


def test_0058_project_users_uses_granted_at():
    source = MIGRATION_0058.read_text()
    assert "INSERT INTO project_users (project_id, user_id, granted_at)" in source
    assert "INSERT INTO project_users (project_id, user_id, created_at)" not in source


def test_0058_battery_analyses_uses_optional_column():
    source = MIGRATION_0058.read_text()
    assert "INSERT INTO battery_analyses (battery_id, analysis_id, sequence, optional)" in source
    assert "is_optional" not in source


def test_0059_results_use_description_not_notes_column():
    source = MIGRATION_0059.read_text()
    assert "qualifiers, description, entry_date" in source
    assert "qualifiers, notes, entry_date" not in source

    source = MIGRATION_0059.read_text()
    assert "INSERT INTO batch_containers (batch_id, container_id)" in source
    assert "INSERT INTO batch_containers (batch_id, container_id, created_at)" not in source


def test_0059_tests_include_review_date_bind():
    source = MIGRATION_0059.read_text()
    assert "'review_date': None" in source
    assert "seed_params(test)" in source
    assert "seed_params(cont)" in source
    assert "seed_params(sample)" in source
