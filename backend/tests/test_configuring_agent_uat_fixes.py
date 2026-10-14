"""Configuring agent fixes from live UAT on main 145f6b3 (D-4, D-5, D-7, G5).

Evidence: the model sent {"name", "table": "blood"} to POST /v1/schema/columns,
called /v1/layouts, /v1/container-types and /v1/relations (not real routes),
proposed tables for sample types, invented kit lot numbers, and a rerun proposed
everything again. The live model call itself (D-2) can't run in CI
(tests/KNOWN_FAILURES.md); these tests feed the UAT's own bodies in place of it.
"""

import uuid

import pytest
from sqlalchemy import text

from app.services import configuring_agent_catalog as cat
from app.services import configuring_agent_llm as llm
from app.services import configuring_agent_service as svc
from models.list import List as ListModel, ListEntry
from models.user import Permission, Role, User, role_permissions
from tests.conftest import _get_or_create
from tests.test_configuring_agent_locks import (  # noqa: F401  (fixtures)
    _no_live_provider,
    _role_with,
    _start,
    _user,
    admin,
    configuration,
    mig,
)


def _seed_list(db, name, entries):
    lst = db.query(ListModel).filter(ListModel.name == name).first()
    if lst is None:
        lst = ListModel(name=name, description=name)
        db.add(lst)
        db.flush()
    out = {}
    for entry in entries:
        row = db.query(ListEntry).filter(ListEntry.list_id == lst.id, ListEntry.name == entry).first()
        if row is None:
            row = ListEntry(list_id=lst.id, name=entry)
            db.add(row)
            db.flush()
        out[entry] = row
    db.commit()
    return lst, out


def _step(method, path, body, **extra):
    return {"group": "other", "target": "t", "action": "a", "why": "SOP",
            "call": {"method": method, "path": path, "body": body}, **extra}


# ------------------------------------------------- 2. real routes and formats

def test_route_formats_are_the_allowed_routes_with_real_field_names():
    rows = cat.route_formats()
    paths = {f"{r['method']} {r['path']}" for r in rows}
    assert "POST /containers/types" in paths
    assert "POST /v1/sample-type-transitions" in paths
    assert "PUT /v1/schema/layouts" in paths and "POST /v1/schema/relations" in paths
    for fake in ("/v1/layouts", "/v1/container-types", "/v1/relations"):
        assert not any(r["path"] == fake for r in rows)
    by = {f"{r['method']} {r['path']}": r["body"] for r in rows}
    assert "table_id: uuid" in by["POST /v1/schema/columns"]
    assert "display_name: string" in by["POST /v1/schema/columns"]
    assert "display_name: string" in by["POST /v1/schema/tables"]
    assert "fk_column_id: uuid" in by["POST /v1/schema/relations"]
    assert "column_id: uuid" in by["PUT /v1/schema/layouts"]


def test_system_prompt_carries_formats_catalog_and_reuse_rules():
    prompt = llm._system_prompt(None, "CATALOG-BLOCK")
    assert "POST /v1/schema/columns body {table_id: uuid, display_name: string" in prompt
    assert "/v1/layouts" in prompt and "does not exist" in prompt
    assert "CATALOG-BLOCK" in prompt
    assert "sample_types" in prompt and "matrix_types" in prompt
    assert "lot numbers" in prompt
    assert "example data" in prompt


# ------------------------------------------------- 1. catalog with ids in the prompt

def test_start_run_sends_catalog_with_seed_list_ids(db_session, admin, configuration, monkeypatch):
    lst, entries = _seed_list(db_session, "sample_types", ["Blood", "Urine"])
    seen = {}

    def fake(*_a, **kwargs):
        seen.update(kwargs)
        return {"steps": [_step("POST", "/lists", {"name": f"L_{uuid.uuid4().hex[:6]}"})]}

    monkeypatch.setattr(svc, "propose", fake)
    svc.start_run(db_session, admin, configuration.id, "goal")
    block = seen["catalog"]
    assert f"{lst.id} sample_types" in block
    assert f"Blood={entries['Blood'].id}" in block
    assert "Layout screen_key values: receive, samples.detail, samples.list" in block
    assert "Roles:" in block


# ------------------------------------------------- 1. names -> ids, key fixes

def test_resolve_body_fixes_uat_list_entry_and_transition_bodies(db_session, admin):
    _lst, entries = _seed_list(db_session, "sample_types", ["Whole Blood", "Plasma"])
    assert cat.resolve_body(db_session, admin, "POST", "/lists/sample_types/entries", {"value": "Serum"}) == {"name": "Serum"}
    body = cat.resolve_body(
        db_session, admin, "POST", "/v1/sample-type-transitions",
        {"source": "Whole Blood", "operation": "Aliquot", "dest": "Plasma"},
    )
    assert body == {
        "source_sample_type": str(entries["Whole Blood"].id),
        "operation": "aliquot",
        "allowed_dest_sample_type": str(entries["Plasma"].id),
    }


def test_resolve_body_column_table_name_required_and_list_name(db_session, admin):
    from models.ui_schema import SchemaTable

    table = SchemaTable(id=uuid.uuid4(), client_id=admin.client_id, display_name="Blood Draw",
                        physical_name=f"x_blood_{uuid.uuid4().hex[:4]}", kind="lab", status="active")
    db_session.add(table)
    lst, _ = _seed_list(db_session, "matrix_types", ["Soil"])
    body = cat.resolve_body(db_session, admin, "POST", "/v1/schema/columns",
                            {"name": "Matrix", "table": "Blood Draw", "required": True, "list_name": "matrix_types"})
    assert body == {"table_id": str(table.id), "display_name": "Matrix", "data_type": "list",
                    "nullable": False, "list_id": str(lst.id)}
    # A name that doesn't resolve is left as is (the API's 422 stops it); nothing invented.
    left = cat.resolve_body(db_session, admin, "POST", "/v1/schema/columns", {"name": "X", "table": "nope"})
    assert left["table_id"] == "nope"


def test_resolve_body_layout_and_privileges_role_names(db_session, admin):
    role = _role_with(db_session, [])
    body = cat.resolve_body(db_session, admin, "PUT", "/v1/schema/layouts",
                            {"role": role.name, "screen_key": "samples.detail", "fields": []})
    assert body == {"role_id": str(role.id), "screen_key": "samples.detail", "fields": []}
    rows = cat.resolve_body(db_session, admin, "PUT", "/v1/schema/privileges",
                            {"privileges": [{"role": role.name, "table": "nope", "access": "read"}]})
    assert rows == [{"role_id": str(role.id), "table_id": "nope", "access": "read"}]


def test_proposal_stores_the_resolved_request(db_session, admin, configuration, monkeypatch):
    _seed_list(db_session, "sample_types", ["Blood"])
    name = f"Serum {uuid.uuid4().hex[:4]}"
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/lists/sample_types/entries", {"value": name}),
    ])
    assert run.steps[0].call_body == {"name": name}
    assert run.steps[0].status == "proposed"


# ------------------------------------------------- 3. reuse seed lists, no invented values

@pytest.mark.parametrize("body", [
    {"name": "Blood", "table_type": "sample_type", "is_active": True},
    {"name": "Sample Types"},
    {"display_name": "Matrix"},
    {"name": "Tubes", "table_type": "container_type"},
])
def test_new_table_for_a_seed_concept_is_a_stop(db_session, admin, configuration, monkeypatch, body):
    run = _start(db_session, admin, configuration, monkeypatch, [_step("POST", "/v1/schema/tables", body)])
    assert run.steps[0].status == "stopped"
    assert "/lists/" in run.steps[0].gap or "/containers/types" in run.steps[0].gap


@pytest.mark.parametrize("step", [
    _step("POST", "/lists", {"name": "dsdna_hs_kit_lot"}),
    _step("POST", "/lists/kit_lot_numbers/entries", {"name": "LOT-2231"}),
])
def test_per_run_values_are_never_configured(db_session, admin, configuration, monkeypatch, step):
    run = _start(db_session, admin, configuration, monkeypatch, [step])
    assert run.steps[0].status == "stopped"
    assert "recorded when the work is done" in run.steps[0].gap


@pytest.mark.asyncio
async def test_apply_also_refuses_a_seed_concept_table(db_session, admin):
    from app.services.configuring_agent_apply import CannotExpress, execute_step

    with pytest.raises(CannotExpress):
        await execute_step(db_session, admin, "POST", "/v1/schema/tables", {"name": "Blood", "table_type": "sample_type"})


# ------------------------------------------------- 4. G5 before/after and rerun no-op

@pytest.mark.asyncio
async def test_g5_rerun_shows_before_after_and_is_a_noop(db_session, admin, configuration, monkeypatch):
    _seed_list(db_session, "sample_types", ["Blood"])
    bench = _role_with(db_session, [])
    perm = _get_or_create(db_session, Permission, "sample:update", "x")
    db_session.commit()
    entry_name = f"Serum {uuid.uuid4().hex[:4]}"
    steps = [
        _step("POST", "/lists/sample_types/entries", {"value": entry_name}),
        _step("PUT", f"/roles/{bench.id}/permissions", {"permission_ids": [str(perm.id)]}),
    ]
    first = _start(db_session, admin, configuration, monkeypatch, steps)
    payload = svc.run_payload(first, db_session, admin)["steps"]
    assert payload[0]["diff"]["before"] is None and payload[0]["diff"]["changed"] is True
    assert payload[1]["diff"]["before"] == {"permission_ids": []}
    assert payload[1]["diff"]["after"] == {"permission_ids": [str(perm.id)]}
    result, code = await svc.apply_run(db_session, admin, first.id, second_confirm=True)
    assert code == 200 and result.status == "done"
    items_before = db_session.execute(text("SELECT count(*) FROM configuration_items")).scalar()

    rerun = _start(db_session, admin, configuration, monkeypatch, steps)
    assert [s.status for s in rerun.steps] == ["unchanged", "unchanged"]
    assert [s.decision for s in rerun.steps] == ["excluded", "excluded"]
    seen = svc.run_payload(rerun, db_session, admin)["steps"]
    assert all(row["diff"]["changed"] is False for row in seen)
    assert seen[0]["diff"]["before"]["name"] == entry_name
    assert seen[1]["diff"]["before"] == seen[1]["diff"]["after"]
    # Even if a user includes the rows again, Apply writes nothing and logs nothing.
    for step in rerun.steps:
        svc.set_included(db_session, admin, rerun.id, step.id, True)
    again, code = await svc.apply_run(db_session, admin, rerun.id, second_confirm=True)
    assert code == 200 and again.status == "done"
    assert [s.status for s in again.steps] == ["unchanged", "unchanged"]
    assert again.applied_count == 0
    assert db_session.execute(text("SELECT count(*) FROM configuration_items")).scalar() == items_before
    assert db_session.query(ListEntry).filter(ListEntry.name == entry_name).count() == 1


def test_g5_patch_diff_shows_current_values(db_session, admin):
    lst, entries = _seed_list(db_session, f"L_{uuid.uuid4().hex[:6]}", ["A"])
    diff = cat.describe_change(db_session, admin, "PATCH", f"/lists/{lst.name}/entries/{entries['A'].id}", {"active": False})
    assert diff == {"before": {"active": True}, "after": {"active": False}, "changed": True}
    same = cat.describe_change(db_session, admin, "PATCH", f"/lists/{lst.name}/entries/{entries['A'].id}", {"active": True})
    assert same["changed"] is False


# ------------------------------------------------- smaller: viewer-only stops counted

def test_viewer_only_stops_are_counted_and_show_the_banner(db_session, test_org, configuration, monkeypatch):
    starter = _user(db_session, test_org, "starter", ["config:edit", "result:review"])
    confirmer = _user(db_session, test_org, "confirm", ["config:edit"])
    bench = _role_with(db_session, [])
    review = _get_or_create(db_session, Permission, "result:review", "x")
    db_session.commit()
    run = _start(db_session, starter, configuration, monkeypatch, [
        _step("PUT", f"/roles/{bench.id}/permissions", {"permission_ids": [str(review.id)]}),
    ])
    mine = svc.run_payload(run, db_session, starter)
    assert mine["stopped_count"] == 0 and mine["banner"] is None
    theirs = svc.run_payload(run, db_session, confirmer)
    assert theirs["stopped_count"] == 1
    assert theirs["banner"] == svc.STOP_BANNER


# ------------------------------------------------- smaller: configurable timeout

def test_model_timeout_default_and_env(monkeypatch):
    monkeypatch.delenv("CONFIGURING_AGENT_TIMEOUT_S", raising=False)
    assert llm.model_timeout() == 300.0
    monkeypatch.setenv("CONFIGURING_AGENT_TIMEOUT_S", "600")
    assert llm.model_timeout() == 600.0
    monkeypatch.setenv("CONFIGURING_AGENT_TIMEOUT_S", "nonsense")
    assert llm.model_timeout() == 300.0


def test_model_call_uses_the_configured_timeout(monkeypatch):
    seen = {}

    class Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "{\"steps\": []}"}}]}

    def fake_post(url, **kwargs):
        seen["timeout"] = kwargs["timeout"]
        return Resp()

    monkeypatch.setenv("CONFIGURING_AGENT_TIMEOUT_S", "420")
    monkeypatch.setattr(llm.httpx, "post", fake_post)
    llm.propose("xai", "grok-4.7", "k", chunks=["x"], goal_note=None)
    assert seen["timeout"] == 420.0


# ------------------------------------------------- migrated DB: the UAT run end to end

@pytest.mark.asyncio
async def test_uat_bodies_apply_table_column_layout_relation_then_rerun_is_noop(mig, monkeypatch):
    db, admin, configuration = mig.db, mig.admin, mig.configuration
    slug = uuid.uuid4().hex[:6]
    # The layout API only offers fields the role can read: set that up first.
    from app.services.ui_schema_service import UiSchemaService

    role = _role_with(db, [])
    schema = UiSchemaService(db, admin)
    samples = schema.ensure_core_catalog()
    schema.put_privileges([{"role_id": role.id, "table_id": samples.id, "column_id": None, "access": "read"}])
    db.commit()
    table_name = f"Extraction {slug}"
    steps = [
        # The model's UAT shapes: name/table/required, role by name, tables by name.
        _step("POST", "/v1/schema/tables", {"name": table_name, "is_active": True}),
        _step("POST", "/v1/schema/columns",
              {"name": "Elution Volume", "table": table_name, "type": "numeric", "required": False},
              depends_on=[0]),
        _step("POST", "/v1/schema/columns", {"name": f"Kit Note {slug}", "table": "samples", "data_type": "text"}),
        _step("PUT", "/v1/schema/layouts",
              {"role": role.name, "screen_key": "samples.detail", "fields": [f"Kit Note {slug}"]},
              depends_on=[2]),
    ]
    run = _start(db, admin, configuration, monkeypatch, steps)
    assert [s.status for s in run.steps] == ["proposed"] * 4, [s.gap for s in run.steps]
    result, code = await svc.apply_run(db, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", [s.gap or s.error_message for s in result.steps]
    from models.ui_schema import SchemaColumn, SchemaLayout, SchemaTable

    table = db.query(SchemaTable).filter(SchemaTable.display_name == table_name).one()
    assert db.query(SchemaColumn).filter(SchemaColumn.table_id == table.id, SchemaColumn.display_name == "Elution Volume").count() == 1
    layout = db.query(SchemaLayout).filter(SchemaLayout.role_id == role.id).one()
    assert layout.screen_key == "samples.detail"

    rerun = _start(db, admin, configuration, monkeypatch, steps)
    assert [s.status for s in rerun.steps] == ["unchanged"] * 4, [
        svc.step_payload(s, db, admin)["diff"] for s in rerun.steps
    ]
    assert db.query(SchemaTable).filter(SchemaTable.display_name == table_name).count() == 1


@pytest.mark.asyncio
async def test_relation_by_table_and_column_names(mig, monkeypatch):
    """UAT sent relations by name. They resolve to ids on an existing FK."""
    db, admin, configuration = mig.db, mig.admin, mig.configuration
    steps = [
        _step("POST", "/v1/schema/relations",
              {"name": "Project samples", "from_table": "projects", "to_table": "samples",
               "fk_column": "project_id", "relation_type": "one-to-many"}),
    ]
    run = _start(db, admin, configuration, monkeypatch, steps)
    body = run.steps[0].call_body
    assert body["cardinality"] == "one_to_many"
    # D-3/L-4 (06c630b round): the run registers no catalog rows, so before
    # confirm unregistered tables are still names; Apply registers and resolves.
    result, _ = await svc.apply_run(db, admin, run.id, second_confirm=True)
    assert result.status == "done", result.steps[0].gap or result.steps[0].error_message
    from models.ui_schema import SchemaRelation

    assert db.query(SchemaRelation).filter(SchemaRelation.client_id == admin.client_id).count() == 1
    rerun = _start(db, admin, configuration, monkeypatch, steps)
    assert rerun.steps[0].status == "unchanged"


def test_seed_config_editor_has_config_edit_not_schema_edit(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = conn.execute(text(
            """
            SELECT p.name FROM users u
            JOIN role_permissions rp ON rp.role_id = u.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE u.username = 'config-editor'
            """
        )).scalars().all()
    assert "config:edit" in rows
    assert "schema:edit" not in rows and "layout:edit" not in rows
    assert "role:manage" not in rows and "user:manage" not in rows
