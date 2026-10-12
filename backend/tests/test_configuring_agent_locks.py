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


_ORIG_KEY_FOR_RUN = svc._key_for_run
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
    # Judged for the viewer (here starter = confirmer), not frozen at start.
    assert run.steps[0].status == "proposed"
    seen = svc.run_payload(run, db_session, confirmer)["steps"][0]
    assert seen["status"] == "stopped" and "result:review" in seen["gap"]


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
    seen = svc.run_payload(run, db_session, admin)["steps"]
    assert [step["status"] for step in seen] == ["stopped", "stopped", "stopped"]
    assert all("your own role" in step["gap"] for step in seen)


def test_schema_edit_is_never_granted(db_session, test_org, admin, configuration, monkeypatch):
    bench = _get_or_create(db_session, Role, f"bench_{uuid.uuid4().hex[:6]}", "bench")
    schema_edit = _get_or_create(db_session, Permission, "schema:edit", "x")
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "Bench", "action": "Grant", "why": "x",
         "call": {"method": "PUT", "path": f"/roles/{bench.id}/permissions", "body": {"permission_ids": [str(schema_edit.id)]}}},
    ])
    seen = svc.run_payload(run, db_session, admin)["steps"][0]
    assert seen["status"] == "stopped" and "schema:edit" in seen["gap"]


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
    # G4: the include control won't exclude a row an included row depends on.
    with pytest.raises(svc.ApplyRefused):
        svc.set_included(db_session, admin, run.id, run.steps[0].id, False)
    # Apply still guards it (e.g. a decision stored before that guard).
    run.steps[0].decision = "excluded"
    db_session.commit()
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
    # G2: a 404 from the API is a stop in place with the API's reason, and the
    # whole apply still rolls back.
    assert code == 200
    assert result.status == "stopped" and result.banner == allow.STOP_BANNER
    assert result.applied_count == 0
    assert result.stopped_count == 1
    assert _lists_named(db_session, first) == 0
    assert db_session.query(ListEntry).filter(ListEntry.name == "Whole Blood").count() == 0
    assert db_session.query(ConfigurationItem).filter_by(run_id=run.id).count() == 0
    assert [s.status for s in result.steps] == ["proposed", "proposed", "stopped"]
    assert "(404)" in result.steps[2].gap
    assert result.error_message is None


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


# ================================================================ Tobias review fixes (8121d38)

def _role_with(db, perms):
    role = _get_or_create(db, Role, f"r_{uuid.uuid4().hex[:6]}", "x")
    _grant(db, role, [_get_or_create(db, Permission, p, p) for p in perms])
    db.commit()
    return role


# ---------------------------------------------------------------- G1 escalation re-checked for the viewer

@pytest.mark.asyncio
async def test_g1_escalation_is_rechecked_for_the_confirmer(db_session, test_org, configuration, monkeypatch):
    starter = _user(db_session, test_org, "starter", ["config:edit", "result:review"])
    confirmer = _user(db_session, test_org, "confirm", ["config:edit"])
    bench = _role_with(db_session, [])
    review = _get_or_create(db_session, Permission, "result:review", "x")
    db_session.commit()
    run = _start(db_session, starter, configuration, monkeypatch, [
        {"group": "other", "target": "Bench", "action": "Grant review", "why": "SOP",
         "call": {"method": "PUT", "path": f"/roles/{bench.id}/permissions",
                  "body": {"permission_ids": [str(review.id)]}}},
    ])
    # Not an escalation for the starter, who holds result:review.
    assert run.steps[0].status == "proposed"
    assert svc.run_payload(run, db_session, starter)["steps"][0]["status"] == "proposed"
    # For the confirmer it is: shown as a stop in place, with the reason.
    seen = svc.run_payload(run, db_session, confirmer)["steps"][0]
    assert seen["status"] == "stopped" and seen["stopped_for_viewer"] is True
    assert "result:review" in seen["gap"]
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, confirmer, run.id, second_confirm=True)
    assert exc.value.detail["reason"] == "escalation"
    assert db_session.execute(role_permissions.select().where(role_permissions.c.role_id == bench.id)).first() is None


def test_g1_starter_proposes_change_to_confirmers_own_role(db_session, test_org, admin, configuration, monkeypatch):
    confirmer = _user(db_session, test_org, "self", ["config:edit", "user:manage"])
    extra = _get_or_create(db_session, Permission, "layout:edit", "x")
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "role", "action": "Add", "why": "x",
         "call": {"method": "PUT", "path": f"/roles/{confirmer.role_id}/permissions",
                  "body": {"permission_ids": [str(extra.id)]}}},
        {"group": "other", "target": "user", "action": "Role", "why": "x",
         "call": {"method": "PATCH", "path": f"/users/{confirmer.id}", "body": {"role_id": str(admin.role_id)}}},
    ])
    assert [s.status for s in run.steps] == ["proposed", "proposed"]
    seen = svc.run_payload(run, db_session, confirmer)["steps"]
    assert [s["status"] for s in seen] == ["stopped", "stopped"]
    assert all("your own role" in s["gap"] for s in seen)


# ---------------------------------------------------------------- G3 routing / asked-for, DDL rollback

@pytest.mark.parametrize("path", ["/v1/routing-map", "/v1/routing-map/abc", "/v1/asked-for", "/v1/asked-for/abc/items"])
def test_g3_routing_and_asked_for_are_stops(db_session, admin, configuration, monkeypatch, path):
    assert allow.classify_call("POST", path, {}).ok is False
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "route", "action": "Route", "why": "x",
         "call": {"method": "POST", "path": path, "body": {}}},
        _list_step(f"after_{uuid.uuid4().hex[:6]}"),
    ])
    assert [s.status for s in run.steps] == ["stopped", "proposed"]
    assert "stays as built" in run.steps[0].gap


@pytest.fixture
def mig(migrated_engine):
    """Real DDL needs ui_schema_create_table, which only the migrated DB has."""
    from sqlalchemy.orm import sessionmaker
    from models.client import Client

    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")()
    org = Client(name=f"Mig {uuid.uuid4().hex[:6]}")
    session.add(org)
    session.flush()
    user = _user(session, org, "migadmin", ["config:edit", "schema:edit", "layout:edit"])
    cfg = Configuration(id=uuid.uuid4(), client_id=org.id, name=f"M {uuid.uuid4().hex[:6]}", created_by=user.id)
    session.add(cfg)
    session.commit()
    yield SimpleNamespace(db=session, admin=user, configuration=cfg)
    session.close()
    transaction.rollback()
    connection.close()


@pytest.mark.asyncio
async def test_g3_schema_ddl_rolls_back_inside_the_apply_transaction(mig, monkeypatch):
    db_session, admin, configuration = mig.db, mig.admin, mig.configuration
    slug = uuid.uuid4().hex[:8]
    physical = f"x_ca_{slug}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "schema_tables", "target": "Extraction", "action": "Create table", "why": "SOP",
         "call": {"method": "POST", "path": "/v1/schema/tables",
                  "body": {"display_name": f"CA {slug}", "physical_name": physical}}},
        _entry_step(f"missing_{slug}", "Nope"),  # 404 -> whole apply rolls back
    ])
    result, _ = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert result.status == "stopped"
    assert result.steps[0].status == "proposed" and result.steps[1].status == "stopped"
    exists = db_session.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"), {"t": physical}
    ).first()
    assert exists is None
    from models.ui_schema import SchemaTable

    assert db_session.query(SchemaTable).filter(SchemaTable.physical_name == physical).count() == 0


@pytest.mark.asyncio
async def test_g3_schema_ddl_is_real_when_apply_succeeds(mig, monkeypatch):
    db_session, admin, configuration = mig.db, mig.admin, mig.configuration
    # Control for the rollback test: the same call does create the table.
    physical = f"x_ca_{uuid.uuid4().hex[:8]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "schema_tables", "target": "T", "action": "Create", "why": "x",
         "call": {"method": "POST", "path": "/v1/schema/tables", "body": {"display_name": physical, "physical_name": physical}}},
    ])
    result, _ = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert result.status == "done", result.steps[0].error_message or result.steps[0].gap
    assert db_session.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"), {"t": physical}
    ).first() is not None


# ---------------------------------------------------------------- G4 excluding a depended-on row

def test_g4_cannot_exclude_a_row_an_included_row_depends_on(db_session, admin, configuration, monkeypatch):
    name = f"D_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(name), _entry_step(name, "Whole Blood", depends_on=[0]),
    ])
    with pytest.raises(svc.ApplyRefused) as exc:
        svc.set_included(db_session, admin, run.id, run.steps[0].id, False)
    assert exc.value.detail["reason"] == "dependency"
    assert "Row 2 depends on row 1" in exc.value.detail["message"]
    db_session.refresh(run.steps[0])
    assert run.steps[0].decision == "included"
    # Exclude the dependent first, then the parent: allowed.
    svc.set_included(db_session, admin, run.id, run.steps[1].id, False)
    svc.set_included(db_session, admin, run.id, run.steps[0].id, False)


@pytest.mark.asyncio
async def test_g4_apply_refuses_dependency_on_any_excluded_row(db_session, admin, configuration, monkeypatch):
    name = f"D_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(name), _entry_step(name, "Whole Blood", depends_on=[0]),
    ])
    run.steps[0].decision = "excluded"  # e.g. stored before this guard existed
    db_session.commit()
    with pytest.raises(svc.ApplyRefused) as exc:
        await svc.apply_run(db_session, admin, run.id)
    assert "which is excluded" in exc.value.detail["message"]
    assert _lists_named(db_session, name) == 0


# ---------------------------------------------------------------- G6 stop recount on failure

@pytest.mark.asyncio
async def test_g6_failure_recounts_every_stop(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        {"group": "other", "target": "g1", "action": "x", "why": "x", "gap": "No API one."},
        {"group": "other", "target": "g2", "action": "x", "why": "x", "gap": "No API two."},
        _entry_step(f"missing_{uuid.uuid4().hex[:6]}", "Nope"),
    ])
    assert run.stopped_count == 2
    for step in run.steps[:2]:
        svc.set_included(db_session, admin, run.id, step.id, False)
    result, _ = await svc.apply_run(db_session, admin, run.id)
    # The 404 row is now a stop too (G2): two proposal stops + one apply stop.
    assert result.status == "stopped"
    assert result.stopped_count == 3


# ---------------------------------------------------------------- G8 no writes on missing key

def test_g8_missing_key_writes_no_settings_row(db_session, monkeypatch):
    from fastapi import HTTPException
    from models.configuring_agent import ConfiguringAgentSettings

    for env in ("OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    db_session.query(ConfiguringAgentSettings).delete()
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        svc.models_for(db_session, "openai")
    assert "OPENAI_API_KEY" in str(exc.value.detail)
    with pytest.raises(HTTPException):
        _ORIG_KEY_FOR_RUN(db_session)
    assert db_session.new == set() or not any(isinstance(o, ConfiguringAgentSettings) for o in db_session.new)
    assert db_session.query(ConfiguringAgentSettings).count() == 0


# ---------------------------------------------------------------- G7 privileges beyond the confirmer's own

def test_g7_cannot_grant_more_table_access_than_your_own_role_has(db_session, test_org, admin):
    from models.ui_schema import SchemaPrivilege, SchemaTable

    table = SchemaTable(client_id=test_org.id, display_name="Ext", physical_name=f"x_{uuid.uuid4().hex[:8]}", kind="ui")
    db_session.add(table)
    db_session.flush()
    db_session.add(SchemaPrivilege(client_id=test_org.id, role_id=admin.role_id, table_id=table.id, access="read"))
    other = _role_with(db_session, [])
    body = lambda access: {"privileges": [{"role_id": str(other.id), "table_id": str(table.id), "access": access}]}
    gap = apply_mod.escalation_gap(db_session, admin, "PUT", "/v1/schema/privileges", body("write"))
    assert gap and "write access where your own role has read" in gap
    assert apply_mod.escalation_gap(db_session, admin, "PUT", "/v1/schema/privileges", body("read")) is None
    assert apply_mod.escalation_gap(db_session, admin, "PUT", "/v1/schema/privileges", body("none")) is None


# ---------------------------------------------------------------- rerun with PUT / PATCH rows

@pytest.mark.asyncio
async def test_rerun_with_put_and_patch_rows_writes_no_duplicates(db_session, admin, configuration, monkeypatch):
    lst = ListModel(name=f"P_{uuid.uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.flush()
    entry = ListEntry(list_id=lst.id, name=f"E_{uuid.uuid4().hex[:6]}")
    db_session.add(entry)
    bench = _role_with(db_session, [])
    perm = _get_or_create(db_session, Permission, "sample:update", "x")
    db_session.commit()
    steps = [
        {"group": "other", "target": entry.name, "action": "Set inactive", "why": "x",
         "call": {"method": "PATCH", "path": f"/lists/{lst.name}/entries/{entry.id}", "body": {"active": False}}},
        {"group": "other", "target": "Bench", "action": "Perms", "why": "x",
         "call": {"method": "PUT", "path": f"/roles/{bench.id}/permissions", "body": {"permission_ids": [str(perm.id)]}}},
    ]

    def snapshot():
        return (
            db_session.query(ListEntry).filter(ListEntry.list_id == lst.id).count(),
            db_session.execute(role_permissions.select().where(role_permissions.c.role_id == bench.id)).all(),
        )

    for _ in range(2):
        run = _start(db_session, admin, configuration, monkeypatch, steps)
        result, code = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
        assert code == 200 and result.status == "done", [s.error_message or s.gap for s in result.steps]
        count, perms = snapshot()
        assert count == 1 and len(perms) == 1
    db_session.refresh(entry)
    assert entry.active is False


# ---------------------------------------------------------------- L-4 plan equals effect

def _row_counts(db):
    tables = [r[0] for r in db.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
    ))]
    return {t: db.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in tables}


@pytest.mark.asyncio
async def test_l4_plan_equals_effect(db_session, admin, configuration, monkeypatch):
    lst = ListModel(name=f"L4_{uuid.uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.flush()
    entry = ListEntry(list_id=lst.id, name=f"E_{uuid.uuid4().hex[:6]}")
    db_session.add(entry)
    db_session.commit()
    included_name, excluded_name = f"I_{uuid.uuid4().hex[:6]}", f"X_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(included_name),
        _list_step(excluded_name),
        {"group": "other", "target": entry.name, "action": "Set inactive", "why": "x",
         "call": {"method": "PATCH", "path": f"/lists/{lst.name}/entries/{entry.id}", "body": {"active": False}}},
    ])
    svc.set_included(db_session, admin, run.id, run.steps[1].id, False)
    before = _row_counts(db_session)
    other_entries = {e.id: (e.name, e.active) for e in db_session.query(ListEntry).filter(ListEntry.id != entry.id)}
    result, code = await svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done"
    after = _row_counts(db_session)
    changed = {t: after[t] - before[t] for t in after if after[t] != before[t]}
    # Exactly the confirmed plan: one new list, and one ledger row per applied row.
    assert changed == {"lists": 1, "configuration_items": 2}
    assert _lists_named(db_session, included_name) == 1
    assert _lists_named(db_session, excluded_name) == 0
    db_session.refresh(entry)
    assert entry.active is False
    # No other list entry was touched.
    assert {e.id: (e.name, e.active) for e in db_session.query(ListEntry).filter(ListEntry.id != entry.id)} == other_entries


@pytest.mark.asyncio
async def test_new_step_states_fit_the_migrated_check_constraints(mig, monkeypatch):
    """included/excluded/unchanged must be legal in the real (migrated) schema."""
    db_session, admin, configuration = mig.db, mig.admin, mig.configuration
    name = f"MC_{uuid.uuid4().hex[:6]}"
    first = _start(db_session, admin, configuration, monkeypatch, [_list_step(name), _list_step(f"{name}_b")])
    svc.set_included(db_session, admin, first.id, first.steps[1].id, False)
    result, _ = await svc.apply_run(db_session, admin, first.id)
    assert result.status == "done"
    second = _start(db_session, admin, configuration, monkeypatch, [_list_step(name)])
    assert second.steps[0].status == "unchanged" and second.steps[0].decision == "excluded"



# ---------------------------------------------------------------- G2 API 422/404 during Apply = stop

@pytest.mark.asyncio
async def test_g2_api_422_during_apply_is_a_stop_with_the_api_reason(db_session, admin, configuration, monkeypatch):
    name = f"G2_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _list_step(name),
        # ListCreate needs a name: the body fails validation -> 422 from the API layer.
        {"group": "other", "target": "bad", "action": "Create", "why": "x",
         "call": {"method": "POST", "path": "/lists", "body": {"description": "no name"}}},
    ])
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert code == 200
    assert result.status == "stopped" and result.banner == allow.STOP_BANNER
    assert [s.status for s in result.steps] == ["proposed", "stopped"]
    assert "(422)" in result.steps[1].gap
    assert result.stopped_count == 1 and result.applied_count == 0
    assert _lists_named(db_session, name) == 0  # earlier row rolled back
    assert svc.run_payload(result, db_session, admin)["steps"][1]["retryable"] is True
    # An API stop is retried by the next Apply; this body still fails, so it stops again.
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert result.status == "stopped" and result.stopped_count == 1
    assert _lists_named(db_session, name) == 0
    svc.set_included(db_session, admin, run.id, result.steps[1].id, False)
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert result.status == "done" and _lists_named(db_session, name) == 1


@pytest.mark.asyncio
async def test_g2_other_api_errors_still_fail(db_session, admin, configuration, monkeypatch):
    from fastapi import HTTPException

    async def boom(*_a, **_k):
        raise HTTPException(409, "Conflict from the API")

    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(f"G2b_{uuid.uuid4().hex[:6]}")])
    monkeypatch.setattr(svc, "execute_step", boom)
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert result.status == "failed" and code == 200
    assert result.steps[0].status == "failed" and "Conflict" in result.steps[0].error_message
    assert result.stopped_count == 0


@pytest.mark.asyncio
async def test_g2_permission_403_during_apply_still_fails_with_403(db_session, admin, configuration, monkeypatch):
    async def denied(*_a, **_k):
        raise apply_mod.PermissionDenied("Permission 'config:edit' required")

    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(f"G2c_{uuid.uuid4().hex[:6]}")])
    monkeypatch.setattr(svc, "execute_step", denied)
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert code == 403 and result.status == "failed"



# ================================================================ hotfix: G1 not frozen at start, model perms, G7 inherit, G2 fix path

def test_g1_start_does_not_freeze_the_starters_escalation(db_session, test_org, configuration, monkeypatch):
    starter = _user(db_session, test_org, "lowstart", ["config:edit"])
    confirmer = _user(db_session, test_org, "highconf", ["config:edit", "result:review"])
    bench = _role_with(db_session, [])
    review = _get_or_create(db_session, Permission, "result:review", "x")
    db_session.commit()
    run = _start(db_session, starter, configuration, monkeypatch, [
        {"group": "other", "target": "Bench", "action": "Grant review", "why": "SOP",
         "call": {"method": "PUT", "path": f"/roles/{bench.id}/permissions",
                  "body": {"permission_ids": [str(review.id)]}}},
    ])
    # Escalation for the starter, but nothing is stored as a stop.
    assert run.steps[0].status == "proposed" and run.steps[0].gap is None and run.stopped_count == 0
    assert svc.run_payload(run, db_session, starter)["steps"][0]["status"] == "stopped"
    assert svc.run_payload(run, db_session, confirmer)["steps"][0]["status"] == "proposed"
    return run, confirmer, bench


@pytest.mark.asyncio
async def test_g1_confirmer_who_holds_the_permission_can_apply(db_session, test_org, configuration, monkeypatch):
    run, confirmer, bench = test_g1_start_does_not_freeze_the_starters_escalation(
        db_session, test_org, configuration, monkeypatch
    )
    result, code = await svc.apply_run(db_session, confirmer, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", [s.gap or s.error_message for s in result.steps]
    assert db_session.execute(role_permissions.select().where(role_permissions.c.role_id == bench.id)).first()


def test_g1_model_gets_no_ones_permissions(db_session, admin, configuration, monkeypatch):
    seen = {}

    def fake(*_a, **kwargs):
        seen.update(kwargs)
        return {"steps": [_list_step(f"P_{uuid.uuid4().hex[:6]}")]}

    monkeypatch.setattr(svc, "propose", fake)
    run = svc.start_run(db_session, admin, configuration.id, "goal")
    assert seen.get("permissions") is None
    from app.services.configuring_agent_llm import _system_prompt

    prompt = _system_prompt(None)
    assert "checked for the person who confirms" in prompt and "That user holds" not in prompt
    seen.clear()
    monkeypatch.setattr(svc, "propose", lambda *_a, **k: seen.update(k) or {"steps": [_list_step("x")]})
    svc.redo_step(db_session, admin, run.id, run.steps[0].id, "again")
    assert seen.get("permissions") is None


def test_g7_inherit_column_grant_resolves_to_table_access(db_session, test_org, admin):
    from models.ui_schema import SchemaColumn, SchemaPrivilege, SchemaTable

    table = SchemaTable(client_id=test_org.id, display_name="Inh", physical_name=f"x_{uuid.uuid4().hex[:8]}", kind="ui")
    db_session.add(table)
    db_session.flush()
    column = SchemaColumn(
        client_id=test_org.id, table_id=table.id, display_name="c", physical_name="c", data_type="text",
    )
    db_session.add(column)
    db_session.flush()
    # Mine: table write, but this column read only.
    db_session.add(SchemaPrivilege(client_id=test_org.id, role_id=admin.role_id, table_id=table.id, access="write"))
    db_session.add(SchemaPrivilege(client_id=test_org.id, role_id=admin.role_id, table_id=table.id, column_id=column.id, access="read"))
    other = _role_with(db_session, [])
    rows = lambda table_access: {"privileges": [
        {"role_id": str(other.id), "table_id": str(table.id), "access": table_access},
        {"role_id": str(other.id), "table_id": str(table.id), "column_id": str(column.id), "access": "inherit"},
    ]}
    gap = apply_mod.escalation_gap(db_session, admin, "PUT", "/v1/schema/privileges", rows("write"))
    assert gap and "write (inherited)" in gap and "your own role has read" in gap
    assert apply_mod.escalation_gap(db_session, admin, "PUT", "/v1/schema/privileges", rows("read")) is None


@pytest.mark.asyncio
async def test_g2_fixable_404_is_retried_after_the_cause_is_fixed(db_session, admin, configuration, monkeypatch):
    list_name = f"later_{uuid.uuid4().hex[:6]}"
    other = f"O_{uuid.uuid4().hex[:6]}"
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step(other), _entry_step(list_name, "Whole Blood")])
    result, _ = await svc.apply_run(db_session, admin, run.id)
    assert result.status == "stopped" and "(404)" in result.steps[1].gap
    payload = svc.run_payload(result, db_session, admin)
    assert payload["steps"][1]["retryable"] is True
    # Fix the cause outside the run (the list now exists), then Apply again: no Redo needed.
    db_session.add(ListModel(name=list_name))
    db_session.commit()
    result, code = await svc.apply_run(db_session, admin, run.id)
    assert code == 200 and result.status == "done"
    assert result.stopped_count == 0 and result.steps[1].gap is None
    assert db_session.query(ListEntry).join(ListModel).filter(ListModel.name == list_name).count() == 1
    assert _lists_named(db_session, other) == 1
