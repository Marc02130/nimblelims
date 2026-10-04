"""Configuring agent: same Schema list, ragged chunking, encrypted key, all-or-nothing apply."""

import os
import uuid
from types import SimpleNamespace

import pytest

os.environ["EMBEDDING_PROVIDER"] = "stub"

from app.services.configuring_agent_allow import (
    STOP_BANNER,
    classify_call,
    schema_table_names,
)
from app.services.configuring_agent_apply import (
    AppliedChange,
    AtomicSession,
    CannotExpress,
    PermissionDenied,
    _roles,
)
from app.services.configuring_agent_chunk import CHUNK_OVERLAP, CHUNK_SIZE, DEFAULT_SEPARATORS, split_with_headings
from app.services.configuring_agent_crypto import MissingProviderKey, clear_stored_key, decrypt_secret, encrypt_secret, resolve_provider_key
from app.services.configuring_agent_embeddings import EMBEDDING_DIM, EMBEDDING_MODEL, embed_texts
from app.services.configuring_agent_llm import _system_prompt
from app.services.ui_schema_catalog import LAB_TABLES, NOT_SCHEMA_TABLES, SYSTEM_TABLES
from app.services import configuring_agent_service as agent_service
from models.configuring_agent import Configuration, ConfigurationChunk, ConfigurationItem, ConfiguringAgentSettings


def test_schema_list_is_the_screen_list():
    names = schema_table_names()
    assert names["lab"] is LAB_TABLES
    assert names["system"] is SYSTEM_TABLES
    assert set(names["not_schema"]) == set(NOT_SCHEMA_TABLES)
    assert {"lists", "list_entries", "units"} <= set(names["not_schema"])


def test_prompt_uses_that_list():
    prompt = _system_prompt()
    for name in schema_table_names()["not_schema"]:
        assert name in prompt
    assert "samples" in prompt
    assert "many_to_many" in prompt
    assert "Do not grant schema:edit" in prompt


def test_lists_and_units_are_not_schema_calls():
    for table in ("lists", "list_entries", "units"):
        result = classify_call("POST", "/v1/schema/columns", {"table": table, "data_type": "text"})
        assert result.ok is False
        assert "not a Schema table" in result.gap
    many = classify_call("POST", "/v1/schema/relations", {"cardinality": "many_to_many"})
    assert many.ok is False
    assert "junction" in many.gap
    password = classify_call("PATCH", "/users/00000000-0000-4000-8000-000000000099", {"role_id": "x", "password": "secret"})
    assert password.ok is False
    assert "password" in password.gap
    created = classify_call("POST", "/users", {"username": "new"})
    assert created.ok is False
    column = classify_call("POST", "/v1/schema/columns", {"data_type": "text", "table": "samples"})
    assert column.ok is True
    assert column.kind == "column"


def test_chunking_matches_ragged_sizes():
    assert CHUNK_SIZE == 1000
    assert CHUNK_OVERLAP == 200
    assert DEFAULT_SEPARATORS == ["\n\n", "\n", ". ", " ", ""]
    text = "Sample processing\n\n" + ("Extract DNA. " * 80)
    parts = split_with_headings(text)
    assert parts
    assert all(heading == "Sample processing" for _, heading in parts)
    assert all(len(piece) <= CHUNK_SIZE + CHUNK_OVERLAP for piece, _ in parts)


def test_stub_embedding_is_384():
    vectors = embed_texts(["lab file"])
    assert EMBEDDING_MODEL == "sentence-transformers/all-MiniLM-L6-v2"
    assert EMBEDDING_DIM == 384
    assert len(vectors) == 1
    assert len(vectors[0]) == 384
    assert vectors[0][0] == 0.01


def test_key_round_trip_and_no_other_vendor(monkeypatch):
    token = encrypt_secret("unit-test-key")
    assert decrypt_secret(token) == "unit-test-key"
    assert "unit-test-key" not in token
    row = SimpleNamespace(key_ciphertext=token, agent_model="grok", agent_provider="xai")
    clear_stored_key(row)
    assert row.key_ciphertext is None
    assert row.agent_model is None
    assert row.agent_provider == "xai"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("XAI_API_KEY", "not-for-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-for-openai")
    with pytest.raises(MissingProviderKey) as exc:
        resolve_provider_key("openai", None)
    assert exc.value.env_name == "OPENAI_API_KEY"
    assert "not-for-openai" not in str(exc.value)


def test_configuration_rows_have_name_and_chunks_stay_with_configuration():
    settings = {column.name for column in ConfiguringAgentSettings.__table__.columns}
    configuration = {column.name for column in Configuration.__table__.columns}
    chunk = {column.name for column in ConfigurationChunk.__table__.columns}
    item = {column.name for column in ConfigurationItem.__table__.columns}
    assert {"id", "name"} <= settings
    assert {"id", "name"} <= configuration
    assert {"id", "name"} <= item
    assert "configuration_id" in chunk
    assert "user_id" not in chunk
    assert "uploaded_by" not in chunk


def test_atomic_session_flushes_instead_of_committing():
    class Session:
        def __init__(self):
            self.flushed = 0
            self.rolled = 0

        def flush(self):
            self.flushed += 1

        def rollback(self):
            self.rolled += 1

        def query(self):
            return "query"

    raw = Session()
    proxy = AtomicSession(raw)
    proxy.commit()
    proxy.rollback()
    assert raw.flushed == 1
    assert raw.rolled == 1
    assert proxy.query() == "query"


class _Db:
    def __init__(self, run):
        self.run = run
        self.events = []
        self.added = []

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")
        self.added.clear()
        for step in self.run.steps:
            if step.status == "applied":
                step.status = "proposed"

    def refresh(self, _obj):
        return None

    def add(self, obj):
        self.added.append(obj)

    def query(self, _model):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.run


def _accepted_run():
    steps = []
    for target in ("A", "B"):
        steps.append(
            SimpleNamespace(
                id=uuid.uuid4(),
                decision="accepted",
                gap=None,
                status="proposed",
                call_method="POST",
                call_path="/lists",
                call_body={},
                target=target,
                action="add",
            )
        )
    return SimpleNamespace(
        id=uuid.uuid4(),
        configuration_id=uuid.uuid4(),
        steps=steps,
        status="proposing",
        banner=None,
        error_message=None,
        applied_count=0,
        skipped_count=0,
        stopped_count=0,
        modified_by=None,
    )


@pytest.mark.asyncio
async def test_apply_rolls_back_every_write(monkeypatch):
    run = _accepted_run()
    db = _Db(run)
    calls = {"n": 0}

    async def execute_step(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise CannotExpress("no junction")
        return [AppliedChange("list", "Intake", uuid.uuid4())]

    monkeypatch.setattr(agent_service, "_run", lambda *_a, **_k: run)
    monkeypatch.setattr(agent_service, "_key_for_run", lambda _db: (SimpleNamespace(), "k"))
    monkeypatch.setattr(agent_service, "execute_step", execute_step)
    result, code = await agent_service.apply_run(db, SimpleNamespace(id=uuid.uuid4()), run.id)
    assert code == 200
    assert result.status == "stopped"
    assert result.banner == STOP_BANNER
    assert result.applied_count == 0
    assert result.steps[0].status == "proposed"
    assert result.steps[1].status == "stopped"
    assert db.added == []
    assert db.events == ["rollback", "commit"]


@pytest.mark.asyncio
async def test_permission_failure_rolls_back_and_returns_403(monkeypatch):
    run = _accepted_run()
    db = _Db(run)

    async def execute_step(*_args, **_kwargs):
        raise PermissionDenied("Permission 'schema:edit' required")

    monkeypatch.setattr(agent_service, "_run", lambda *_a, **_k: run)
    monkeypatch.setattr(agent_service, "_key_for_run", lambda _db: (SimpleNamespace(), "k"))
    monkeypatch.setattr(agent_service, "execute_step", execute_step)
    result, code = await agent_service.apply_run(db, SimpleNamespace(id=uuid.uuid4()), run.id)
    assert code == 403
    assert result.status == "failed"
    assert result.applied_count == 0
    assert "schema:edit" in result.error_message
    assert db.events == ["rollback", "commit"]


@pytest.mark.asyncio
async def test_new_schema_edit_grant_is_refused(monkeypatch):
    from models.user import Permission, Role

    role_id = uuid.uuid4()
    permission_id = uuid.uuid4()

    class Query:
        def __init__(self, rows=None, one=None):
            self.rows = rows or []
            self.one = one

        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return self.rows

        def first(self):
            return self.one

    class DB:
        def query(self, model):
            if model is Permission.name:
                return Query(rows=[("schema:edit",)])
            if model is Role:
                return Query(one=SimpleNamespace(name="Lab Technician"))
            raise AssertionError(model)

    monkeypatch.setattr("app.services.configuring_agent_apply._permission_names", lambda _db, _role_id: set())
    with pytest.raises(CannotExpress) as exc:
        await _roles(
            DB(),
            SimpleNamespace(id=uuid.uuid4()),
            "PUT",
            f"/roles/{role_id}/permissions",
            {"permission_ids": [str(permission_id)]},
        )
    assert "does not grant schema:edit" in exc.value.gap
