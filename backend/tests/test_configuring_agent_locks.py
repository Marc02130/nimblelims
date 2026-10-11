"""Configuring agent Step 1 locks (SPEC §10, D-6/D-7/D-8, L-1..L-4, FB-11).

Real database, real list/role/container routes. Only the LLM call and the key
lookup are replaced, because D-2 (a live provider call) can't run in CI; see
tests/KNOWN_FAILURES.md.
"""

import inspect
import os
import re
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

os.environ.setdefault("EMBEDDING_PROVIDER", "stub")

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_apply as apply_mod
from app.services import configuring_agent_service as svc
from models.configuring_agent import Configuration, ConfigurationItem, ConfigurationRun
from models.container import Container, ContainerType, Contents
from models.list import List as ListModel, ListEntry
from models.user import Permission, Role, User, role_permissions
from tests.conftest import _get_or_create, _grant


PROVIDER = SimpleNamespace(agent_provider="xai", agent_model="grok-test-model")


@pytest.fixture(autouse=True)
def _no_live_provider(monkeypatch):
    monkeypatch.setattr(svc, "_key_for_run", lambda _db: (PROVIDER, "test-key"))
    monkeypatch.setattr(svc, "_excerpt", lambda *_a, **_k: ["excerpt"])
    monkeypatch.setattr(svc, "_ready_documents", lambda *_a, **_k: 1)


def _user(db, org, name, perms):
    role = _get_or_create(db, Role, f"role_{name}_{uuid.uuid4().hex[:6]}", "test")
    _grant(db, role, [_get_or_create(db, Permission, p, p) for p in perms])
    user = User(
        name=name, username=f"{name}_{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:8]}@x.org",
        password_hash="x", role_id=role.id, client_id=org.id, must_change_password=False,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin(db_session, test_org):
    return _user(db_session, test_org, "conf", ["config:edit", "sample:update", "schema:edit", "layout:edit", "user:manage"])


@pytest.fixture
def configuration(db_session, admin):
    row = Configuration(id=uuid.uuid4(), client_id=admin.client_id, name=f"Cfg {uuid.uuid4().hex[:6]}", created_by=admin.id)
    db_session.add(row)
    db_session.commit()
    return row


def _propose(monkeypatch, steps):
    monkeypatch.setattr(svc, "propose", lambda *_a, **_k: {"steps": steps})


def _list_step(name, **extra):
    return {"group": "other", "target": name, "action": f"Create list {name}", "why": "SOP",
            "call": {"method": "POST", "path": "/lists", "body": {"name": name}}, **extra}


def _entry_step(list_name, entry, **extra):
    return {"group": "other", "target": entry, "action": f"Add {entry}", "why": "SOP",
            "call": {"method": "POST", "path": f"/lists/{list_name}/entries", "body": {"name": entry}}, **extra}


def _start(db, user, configuration, monkeypatch, steps):
    _propose(monkeypatch, steps)
    return svc.start_run(db, user, configuration.id, "goal")


def _lists_named(db, name):
    return db.query(ListModel).filter(ListModel.name == name).count()


# ---------------------------------------------------------------- 1. no drop / delete

BANNED = [
    ("POST", "/v1/schema/tables/00000000-0000-4000-8000-000000000001/drop"),
    ("POST", "/v1/schema/columns/00000000-0000-4000-8000-000000000001/drop"),
    ("DELETE", "/v1/schema/relations/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/lists/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/lists/Matrix/entries/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/roles/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/v1/sample-type-transitions/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/containers/00000000-0000-4000-8000-000000000001/contents/00000000-0000-4000-8000-000000000002"),
    ("DELETE", "/samples/00000000-0000-4000-8000-000000000001"),
    ("DELETE", "/users/00000000-0000-4000-8000-000000000001"),
]


def test_allowed_list_has_no_drop_or_delete():
    for method, pattern, *_ in allow._ALLOWED:
        assert method != "DELETE"
        assert "drop" not in pattern.pattern
        assert "truncate" not in pattern.pattern


@pytest.mark.parametrize("method,path", BANNED)
def test_every_drop_and_delete_is_a_stop(method, path):
    result = allow.classify_call(method, path, {"confirm": True})
    assert result.ok is False
    assert result.gap


def test_relation_removal_stop_says_why():
    result = allow.classify_call("DELETE", "/v1/schema/relations/00000000-0000-4000-8000-000000000001")
    assert "no status flag" in result.gap


def test_deprecate_and_set_inactive_are_allowed():
    assert allow.classify_call("POST", "/v1/schema/tables/abc/deprecate").ok
    assert allow.classify_call("POST", "/v1/schema/columns/abc/deprecate").ok
    patch = allow.classify_call("PATCH", "/lists/abc/entries/def", {"active": False})
    assert patch.ok
    assert allow.verb_for("PATCH", "/lists/abc/entries/def", {"active": False}) == "Set inactive"
    assert allow.verb_for("POST", "/v1/schema/columns/abc/deprecate", {}) == "Set inactive"


def test_dispatcher_has_no_drop_or_delete_code_path():
    source = inspect.getsource(apply_mod)
    for name in ("drop_table", "drop_column", "delete_relation", "delete_list", "delete_list_entry", "remove_sample_from_container"):
        assert name not in source


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", BANNED[:5])
async def test_execute_step_refuses_drop_and_delete_before_dispatch(db_session, admin, method, path):
    with pytest.raises(apply_mod.CannotExpress):
        await apply_mod.execute_step(db_session, admin, method, path, {"confirm": True})


# ---------------------------------------------------------------- 2. container retire = amount -> 0

def test_amount_zero_is_the_only_contents_change():
    path = "/containers/00000000-0000-4000-8000-000000000001/contents/00000000-0000-4000-8000-000000000002"
    ok = allow.classify_call("PATCH", path, {"amount": 0})
    assert ok.ok and ok.permission == "sample:update" and ok.kind == "contents_amount"
    assert allow.verb_for("PATCH", path, {"amount": 0}) == "Amount \u2192 0"
    assert allow.needs_second_confirm("PATCH", path, {"amount": 0}, ok.kind)
    for body in ({"amount": 5}, {"amount": 0, "concentration": 1}, {"concentration": 0}, {}):
        assert allow.classify_call("PATCH", path, body).ok is False


@pytest.mark.asyncio
async def test_container_retire_sets_amount_zero_and_keeps_the_row(db_session, admin, configuration, cohort_sample_id, monkeypatch):
    ctype = ContainerType(name=f"tube_{uuid.uuid4().hex[:6]}")
    db_session.add(ctype)
    db_session.flush()
    tube = Container(name=f"T-{uuid.uuid4().hex[:6]}", type_id=ctype.id)
    db_session.add(tube)
    db_session.flush()
    db_session.add(Contents(container_id=tube.id, sample_id=uuid.UUID(cohort_sample_id), amount=400))
    db_session.commit()
    path = f"/containers/{tube.id}/contents/{cohort_sample_id}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": tube.name, "action": "Retire tube", "why": "spent",
         "call": {"method": "PATCH", "path": path, "body": {"amount": 0}}},
    ])
    payload = svc.run_payload(run, db_session, admin)
    assert payload["steps"][0]["verb"] == "Amount \u2192 0"
    assert payload["steps"][0]["second_confirm"] is True
    result, code = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", result.steps[0].error_message or result.steps[0].gap
    row = db_session.query(Contents).filter_by(container_id=tube.id, sample_id=uuid.UUID(cohort_sample_id)).one()
    assert float(row.amount) == 0.0


# ---------------------------------------------------------------- 3. scope = confirming user's permissions

def test_allow_module_no_longer_scopes_by_the_schema_catalog():
    source = inspect.getsource(allow)
    assert "LAB_TABLES" not in source and "SYSTEM_TABLES" not in source
    assert not hasattr(allow, "schema_table_names")


@pytest.mark.asyncio
async def test_rows_the_confirmer_cannot_do_are_flagged_and_apply_refuses_before_writing(
    db_session, test_org, admin, configuration, monkeypatch
):
    starter = admin
    confirmer = _user(db_session, test_org, "nolist", ["config:edit"])
    name = f"L_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, starter, configuration, monkeypatch, [
        _list_step(name),
        {"group": "schema_tables", "target": "Extraction", "action": "Create table", "why": "SOP",
         "call": {"method": "POST", "path": "/v1/schema/tables", "body": {"display_name": "Extraction"}}},
    ])
    viewed = svc.run_payload(run, db_session, confirmer)
    assert viewed["steps"][0]["needs_permission"] is None
    assert viewed["steps"][1]["needs_permission"] == "schema:edit"
    assert svc.run_payload(run, db_session, starter)["steps"][1]["needs_permission"] is None
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, confirmer, run.id, second_confirm=True)
    assert exc.value.status_code == 403
    assert "schema:edit" in exc.value.detail["message"]
    assert _lists_named(db_session, name) == 0


@pytest.mark.asyncio
async def test_a_table_the_user_can_write_is_reachable(db_session, test_org, configuration, monkeypatch):
    confirmer = _user(db_session, test_org, "lister", ["config:edit"])
    name = f"L_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, confirmer, configuration, monkeypatch, [_list_step(name)])
    result, code = await svc.apply_run(db_session, confirmer, run.id)
    assert code == 200 and result.status == "done"
    assert _lists_named(db_session, name) == 1


def test_granting_a_permission_you_do_not_hold_is_a_stop(db_session, test_org, configuration, monkeypatch):
    confirmer = _user(db_session, test_org, "granter", ["config:edit"])
    other_role = _get_or_create(db_session, Role, f"bench_{uuid.uuid4().hex[:6]}", "bench")
    review = _get_or_create(db_session, Permission, "result:review", "review")
    db_session.commit()
    run = _start(db_session, confirmer, configuration, monkeypatch, [
        {"group": "other", "target": "Bench", "action": "Grant review", "why": "SOP",
         "call": {"method": "PUT", "path": f"/roles/{other_role.id}/permissions",
                  "body": {"permission_ids": [str(review.id)]}}},
    ])
    assert run.steps[0].status == "stopped"
    assert "result:review" in run.steps[0].gap


def test_self_escalation_is_a_stop(db_session, test_org, admin, configuration, monkeypatch):
    other_role = _get_or_create(db_session, Role, f"other_{uuid.uuid4().hex[:6]}", "x")
    extra = _get_or_create(db_session, Permission, "experiment:manage", "x")
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "me", "action": "My role", "why": "x",
         "call": {"method": "PATCH", "path": f"/users/{admin.id}", "body": {"role_id": str(other_role.id)}}},
        {"group": "other", "target": "my role", "action": "Add perms", "why": "x",
         "call": {"method": "PUT", "path": f"/roles/{admin.role_id}/permissions",
                  "body": {"permission_ids": [str(extra.id)]}}},
        {"group": "privileges", "target": "my privileges", "action": "Grant", "why": "x",
         "call": {"method": "PUT", "path": "/v1/schema/privileges",
                  "body": {"privileges": [{"role_id": str(admin.role_id), "table_id": str(uuid.uuid4()), "access": "write"}]}}},
    ])
    assert [step.status for step in run.steps] == ["stopped", "stopped", "stopped"]
    assert "your own role" in run.steps[0].gap
    assert "your own role" in run.steps[1].gap
    assert "your own role" in run.steps[2].gap


def test_schema_edit_is_never_granted(db_session, test_org, admin, configuration, monkeypatch):
    bench = _get_or_create(db_session, Role, f"bench_{uuid.uuid4().hex[:6]}", "bench")
    schema_edit = _get_or_create(db_session, Permission, "schema:edit", "x")
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "Bench", "action": "Grant", "why": "x",
         "call": {"method": "PUT", "path": f"/roles/{bench.id}/permissions", "body": {"permission_ids": [str(schema_edit.id)]}}},
    ])
    assert run.steps[0].status == "stopped"
    assert "schema:edit" in run.steps[0].gap


@pytest.mark.asyncio
async def test_add_column_refusal_still_stops(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "schema_columns", "target": "lists", "action": "Add", "why": "x",
         "call": {"method": "POST", "path": "/v1/schema/columns", "body": {"table": "lists", "data_type": "text"}}},
    ])
    assert run.steps[0].status == "stopped"
    assert "not a Schema table" in run.steps[0].gap


# ---------------------------------------------------------------- 4. every stop in place

def test_start_run_keeps_every_row_and_every_stop(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(f"A_{uuid.uuid4().hex[:6]}"),
        {"group": "relations", "target": "M:N", "action": "Link", "why": "x",
         "call": {"method": "POST", "path": "/v1/schema/relations", "body": {"cardinality": "many_to_many"}}},
        _list_step(f"B_{uuid.uuid4().hex[:6]}"),
        {"group": "other", "target": "Drop", "action": "Drop", "why": "x",
         "call": {"method": "DELETE", "path": f"/lists/{uuid.uuid4()}"}},
        _list_step(f"C_{uuid.uuid4().hex[:6]}"),
    ])
    assert len(run.steps) == 5
    assert [step.status for step in run.steps] == ["proposed", "stopped", "proposed", "stopped", "proposed"]
    assert run.stopped_count == 2
    assert run.status == "stopped"
    assert run.banner == allow.STOP_BANNER
    assert all(step.gap for step in run.steps if step.status == "stopped")


@pytest.mark.asyncio
async def test_apply_refuses_while_an_included_row_is_stopped(db_session, admin, configuration, monkeypatch):
    name = f"A_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(name),
        {"group": "other", "target": "Drop", "action": "Drop", "why": "x",
         "call": {"method": "DELETE", "path": f"/lists/{uuid.uuid4()}"}},
    ])
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, admin, run.id)
    assert exc.value.status_code == 409 and exc.value.detail["reason"] == "stopped"
    assert exc.value.detail["rows"] == [2]
    assert _lists_named(db_session, name) == 0
    # Excluding the stopped row (nothing depends on it) lets Apply go.
    svc.set_included(db_session, admin, run.id, run.steps[1].id, False)
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert code == 200 and result.status == "done"
    assert _lists_named(db_session, name) == 1


@pytest.mark.asyncio
async def test_row_depending_on_excluded_stop_refuses_apply(db_session, admin, configuration, monkeypatch):
    name = f"A_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "Gap", "action": "x", "why": "x", "gap": "No API for this."},
        _list_step(name, depends_on=[0]),
    ])
    svc.set_included(db_session, admin, run.id, run.steps[0].id, False)
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, admin, run.id)
    assert exc.value.detail["reason"] == "dependency"
    assert "Row 2 depends on row 1, which is stopped" in exc.value.detail["message"]
    assert _lists_named(db_session, name) == 0


# ---------------------------------------------------------------- 5. include + second confirm

@pytest.mark.asyncio
async def test_only_included_rows_are_applied(db_session, admin, configuration, monkeypatch):
    keep, drop = f"K_{uuid.uuid4().hex[:6]}", f"X_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(keep), _list_step(drop)])
    svc.set_included(db_session, admin, run.id, run.steps[1].id, False)
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert code == 200
    assert _lists_named(db_session, keep) == 1
    assert _lists_named(db_session, drop) == 0
    assert result.applied_count == 1 and result.skipped_count == 1


@pytest.mark.asyncio
async def test_nothing_included_writes_nothing(db_session, admin, configuration, monkeypatch):
    name = f"K_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(name)])
    svc.set_included(db_session, admin, run.id, run.steps[0].id, False)
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, admin, run.id)
    assert exc.value.detail["message"] == "Include at least one change."
    assert _lists_named(db_session, name) == 0


@pytest.mark.asyncio
async def test_high_impact_rows_need_the_second_confirm(db_session, admin, configuration, monkeypatch):
    lst = ListModel(name=f"Retire_{uuid.uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.flush()
    entry = ListEntry(list_id=lst.id, name=f"E_{uuid.uuid4().hex[:6]}")
    db_session.add(entry)
    db_session.commit()
    other = f"N_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(other),
        {"group": "other", "target": entry.name, "action": "Set inactive", "why": "x",
         "call": {"method": "PATCH", "path": f"/lists/{lst.name}/entries/{entry.id}", "body": {"active": False}}},
    ])
    payload = svc.run_payload(run, db_session, admin)
    assert [s["second_confirm"] for s in payload["steps"]] == [False, True]
    assert payload["steps"][1]["verb"] == "Set inactive"
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, admin, run.id)
    assert exc.value.detail["reason"] == "second_confirm" and exc.value.detail["rows"] == [2]
    db_session.refresh(entry)
    assert entry.active is True
    assert _lists_named(db_session, other) == 0
    result, code = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done"
    db_session.refresh(entry)
    assert entry.active is False
    assert db_session.query(ListEntry).filter_by(id=entry.id).count() == 1


def test_second_confirm_kinds():
    for method, path, body in [
        ("PUT", "/roles/x/permissions", {"permission_ids": []}),
        ("PATCH", "/users/x", {"role_id": "y"}),
        ("PUT", "/v1/schema/privileges", {}),
        ("PUT", "/v1/schema/layouts", {}),
        ("POST", "/v1/schema/tables", {"display_name": "T"}),
        ("POST", "/v1/schema/columns", {"table": "samples", "data_type": "text"}),
        ("POST", "/v1/schema/relations", {"cardinality": "one_to_many"}),
        ("POST", "/v1/schema/columns/x/deprecate", {}),
        ("PATCH", "/lists/x", {"active": False}),
    ]:
        kind = allow.classify_call(method, path, body).kind
        assert allow.needs_second_confirm(method, path, body, kind), (method, path)
    for method, path, body in [("POST", "/lists", {"name": "x"}), ("POST", "/containers/types", {"name": "t"})]:
        kind = allow.classify_call(method, path, body).kind
        assert not allow.needs_second_confirm(method, path, body, kind)


def test_apply_endpoint_second_confirm_over_http(client, db_session, test_admin_user, monkeypatch):

    login = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    configuration = Configuration(id=uuid.uuid4(), client_id=test_admin_user.client_id, name=f"H {uuid.uuid4().hex[:6]}")
    db_session.add(configuration)
    db_session.commit()
    lst = ListModel(name=f"H_{uuid.uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.commit()
    _propose(monkeypatch, [{"group": "other", "target": lst.name, "action": "Set inactive", "why": "x",
                            "call": {"method": "PATCH", "path": f"/lists/{lst.id}", "body": {"active": False}}}])
    r = client.post(f"/v1/configuring-agent/configurations/{configuration.id}/runs", json={"goal_note": "g"}, headers=headers)
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["steps"][0]["included"] is True and run["steps"][0]["second_confirm"] is True
    r = client.post(f"/v1/configuring-agent/runs/{run['id']}/apply", headers=headers)
    assert r.status_code == 409 and r.json()["detail"]["reason"] == "second_confirm"
    db_session.refresh(lst)
    assert lst.active is True
    r = client.post(f"/v1/configuring-agent/runs/{run['id']}/steps/{run['steps'][0]['id']}/include",
                    json={"include": False}, headers=headers)
    assert r.status_code == 200 and r.json()["steps"][0]["included"] is False
    client.post(f"/v1/configuring-agent/runs/{run['id']}/steps/{run['steps'][0]['id']}/include",
                json={"include": True}, headers=headers)
    r = client.post(f"/v1/configuring-agent/runs/{run['id']}/apply", json={"second_confirm": True}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "done"
    db_session.refresh(lst)
    assert lst.active is False


# ---------------------------------------------------------------- 6. one transaction

@pytest.mark.asyncio
async def test_failure_rolls_back_every_write_from_the_apply(db_session, admin, configuration, monkeypatch):
    first = f"F_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(first),
        _entry_step(first, "Whole Blood"),
        _entry_step(f"missing_{uuid.uuid4().hex[:6]}", "Nope"),  # 404 from the lists route
    ])
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert result.status == "failed"
    assert result.applied_count == 0
    assert _lists_named(db_session, first) == 0
    assert db_session.query(ListEntry).filter(ListEntry.name == "Whole Blood").count() == 0
    assert db_session.query(ConfigurationItem).filter_by(run_id=run.id).count() == 0
    assert [s.status for s in result.steps] == ["proposed", "proposed", "failed"]
    assert result.steps[2].error_message


# ---------------------------------------------------------------- 7. audit

@pytest.mark.asyncio
async def test_audit_records_confirmer_agent_flag_run_provider_model(db_session, test_org, admin, configuration, monkeypatch):
    confirmer = _user(db_session, test_org, "confirmer", ["config:edit"])
    name = f"A_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(name)])
    assert run.agent_provider == "xai" and run.agent_model == "grok-test-model"
    result, _ = await svc.apply_run(db_session, confirmer, run.id)
    assert result.confirmed_by == confirmer.id and result.confirmed_at is not None
    assert result.created_by == admin.id
    item = db_session.query(ConfigurationItem).filter_by(run_id=run.id).one()
    assert item.created_by == confirmer.id
    assert item.agent_assisted is True
    assert item.agent_provider == "xai" and item.agent_model == "grok-test-model"
    written = db_session.query(ListModel).filter(ListModel.name == name).one()
    assert item.target_id == written.id
    payload = svc.run_payload(result, db_session, confirmer)
    assert payload["confirmed_by"] == confirmer.id and payload["agent_model"] == "grok-test-model"


# ---------------------------------------------------------------- 8. safe rerun

@pytest.mark.asyncio
async def test_rerun_is_a_no_op_with_no_duplicates(db_session, admin, configuration, monkeypatch):
    name = f"R_{uuid.uuid4().hex[:6]}"
    steps = [_list_step(name), _entry_step(name, "Genomic DNA"),
             {"group": "other", "target": "tube", "action": "Create", "why": "x",
              "call": {"method": "POST", "path": "/containers/types", "body": {"name": f"EDTA_{name}"}}}]
    first = _start(db_session, admin, configuration, monkeypatch, steps)
    result, code = await svc.apply_run(db_session, admin, first.id)
    assert code == 200 and result.status == "done", [s.error_message or s.gap for s in result.steps]
    second = _start(db_session, admin, configuration, monkeypatch, steps)
    assert [s.status for s in second.steps] == ["unchanged", "unchanged", "unchanged"]
    # Even if the user includes the no-op rows, apply writes no duplicate.
    for step in second.steps:
        svc.set_included(db_session, admin, second.id, step.id, True)
    result, code = await svc.apply_run(db_session, admin, second.id)
    assert code == 200 and result.status == "done"
    assert _lists_named(db_session, name) == 1
    assert db_session.query(ListEntry).join(ListModel).filter(ListModel.name == name).count() == 1
    assert db_session.query(ContainerType).filter(ContainerType.name == f"EDTA_{name}").count() == 1


@pytest.mark.asyncio
async def test_applied_run_cannot_be_applied_twice(db_session, admin, configuration, monkeypatch):
    from fastapi import HTTPException

    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(f"T_{uuid.uuid4().hex[:6]}")])
    await svc.apply_run(db_session, admin, run.id)
    with pytest.raises(HTTPException):
        await svc.apply_run(db_session, admin, run.id)


# ---------------------------------------------------------------- RESTRICT backstop

def test_identity_fks_are_restrict(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = conn.execute(text(
            """
            SELECT conrelid::regclass::text, conname, confrelid::regclass::text, confdeltype
            FROM pg_constraint
            WHERE contype = 'f'
              AND confrelid::regclass::text IN ('samples', 'containers', 'projects', 'clients', 'users')
            """
        )).all()
    assert rows
    loose = [r for r in rows if r[3] != "r" and r[0] != "password_reset_tokens"]
    assert loose == []
    assert any(r[0] == "contents" and r[2] == "samples" for r in rows)
