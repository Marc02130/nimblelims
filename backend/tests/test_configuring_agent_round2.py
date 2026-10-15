"""Configuring agent fixes from the UAT re-score on main 06c630b.

D-5 (Qubit result fields need a valid home), D-7 (renamed duplicate template),
G5 (re-adding an existing column is No change, not a stop), near-matches
('EDTA Tube' vs 'K2EDTA Tube (5mL)'), the background run (grok-4.7 takes
96-300 s), and D-3/L-4 (no catalog rows committed before confirm). The live
model (D-2) can't run in CI (tests/KNOWN_FAILURES.md); the UAT's own rows
stand in for it.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.services import configuring_agent_catalog as cat
from app.services import configuring_agent_llm as llm
from app.services import configuring_agent_service as svc
from app.services import ui_schema_catalog as schema_catalog
from models.configuring_agent import Configuration, ConfigurationRun
from models.container import ContainerType
from models.experiment import ExperimentTemplate
from models.ui_schema import SchemaTable
from tests.test_configuring_agent_locks import (  # noqa: F401  (fixtures)
    PROVIDER,
    _no_live_provider,
    _propose,
    _start,
    _user,
    admin,
    configuration,
    mig,
)


def _step(method, path, body, target="t", **extra):
    return {"group": "other", "target": target, "action": "a", "why": "SOP",
            "call": {"method": method, "path": path, "body": body}, **extra}


def _gap_row(target, gap):
    return {"group": "schema_columns", "target": target, "action": "Add", "why": "SOP", "gap": gap}


def _registered(db, client_id):
    return {t.physical_name for t in db.query(SchemaTable).filter(SchemaTable.client_id == client_id).all()}


# ------------------------------------------------ D-3 / L-4 catalog registration

def test_configurable_tables_match_the_schema_display_rule(db_session, admin):
    names = {t["physical_name"] for t in cat.configurable_tables(db_session, admin)}
    wanted = list(schema_catalog.LAB_TABLES) + list(schema_catalog.SYSTEM_TABLES)
    present = schema_catalog.existing_tables(db_session, wanted)
    expected = {n for n in present if schema_catalog.shown_in_schema(n, schema_catalog.kind_for(n))}
    assert names == expected
    for code_owned in ("lists", "list_entries", "units"):
        assert code_owned not in names


def test_start_run_commits_no_catalog_rows(db_session, admin, configuration, monkeypatch):
    before = _registered(db_session, admin.client_id)
    _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/v1/schema/columns", {"name": f"Note {uuid.uuid4().hex[:4]}", "table": "samples", "data_type": "text"}),
    ])
    db_session.expire_all()
    assert _registered(db_session, admin.client_id) == before
def test_refused_apply_registers_nothing_and_confirmed_apply_registers_the_display_set(mig, monkeypatch):
    db, admin, configuration = mig.db, mig.admin, mig.configuration
    slug = uuid.uuid4().hex[:6]
    run = _start(db, admin, configuration, monkeypatch, [
        _step("POST", "/v1/schema/columns", {"name": f"Note {slug}", "table": "samples", "data_type": "text"}),
    ])
    assert _registered(db, admin.client_id) == set()
    with pytest.raises(svc.ApplyRefused):
        svc.apply_run(db, admin, run.id, second_confirm=False)  # second confirm missing
    assert _registered(db, admin.client_id) == set()
    result, code = svc.apply_run(db, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", result.steps[0].gap or result.steps[0].error_message
    expected = {t["physical_name"] for t in cat.configurable_tables(db, admin)}
    assert _registered(db, admin.client_id) == expected
    assert not ({"lists", "list_entries", "units"} & expected)


# ------------------------------------------------ D-5 Qubit result fields

def test_column_on_experiments_is_a_stop_that_names_the_valid_home(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/v1/schema/columns",
              {"display_name": "Qubit dsDNA HS reagent volume", "table_id": "experiments", "data_type": "numeric"}),
    ])
    assert run.steps[0].status == "stopped"
    assert "analyte on an analysis" in run.steps[0].gap


def test_catalog_marks_which_tables_take_new_columns(db_session, admin):
    block = cat.catalog_text(cat.catalog_snapshot(db_session, admin))
    assert "experiments \"Experiments\" core [NO new columns]" in block
    assert "samples \"Samples\" core [new columns OK]" in block
    assert "Analyses:" in block and "Analytes:" in block and "Units:" in block
    prompt = llm._system_prompt(None, block)
    assert "POST /analytes" in prompt and "analyte on an analysis" in prompt
def test_qubit_concentration_lands_as_an_analyte_on_an_analysis(db_session, admin, configuration, monkeypatch):
    from models.analysis import Analysis, Analyte

    slug = uuid.uuid4().hex[:6]
    analysis, analyte = f"Qubit dsDNA HS {slug}", f"DNA concentration {slug}"
    steps = [
        _step("POST", "/analytes", {"name": analyte, "data_type": "numeric"}),
        _step("POST", "/analyses", {"name": analysis, "method": "Qubit 4 fluorometer, dsDNA HS"}),
        _step("POST", f"/analyses/{analysis}/analytes", {"analyte_ids": [analyte]}, depends_on=[0, 1]),
    ]
    run = _start(db_session, admin, configuration, monkeypatch, steps)
    assert [s.status for s in run.steps] == ["proposed"] * 3, [s.gap for s in run.steps]
    result, code = svc.apply_run(db_session, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", [s.gap or s.error_message for s in result.steps]
    row = db_session.query(Analysis).filter(Analysis.name == analysis).one()
    assert [a.name for a in row.analytes] == [analyte]
    assert db_session.query(Analyte).filter(Analyte.name == analyte).one().data_type == "numeric"
    # Rerun: all three already in place.
    rerun = _start(db_session, admin, configuration, monkeypatch, steps)
    assert [s.status for s in rerun.steps] == ["unchanged"] * 3


# ------------------------------------------------ D-7 renamed duplicate template

def test_renamed_equivalent_template_is_unchanged_on_rerun(db_session, admin, configuration, monkeypatch):
    db_session.add(ExperimentTemplate(name=f"Qubit dsDNA HS Assay", description="x"))
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/v1/experiment-templates", {"name": "Qubit 4 dsDNA HS quantitation", "description": "y"}),
        _step("POST", "/v1/experiment-templates", {"name": "Qubit dsDNA BR Assay"}),
    ])
    assert [s.status for s in run.steps] == ["unchanged", "proposed"]
    diff = svc.run_payload(run, db_session, admin)["steps"][0]["diff"]
    assert diff["changed"] is False and diff["before"]["name"] == "Qubit dsDNA HS Assay"


def test_template_with_same_definition_is_equivalent(db_session):
    definition = {"entries": [{"entry_type": "samples", "name": "Samples"}]}
    db_session.add(ExperimentTemplate(name=f"Extraction {uuid.uuid4().hex[:4]}", template_definition=definition))
    db_session.commit()
    assert cat.equivalent_template(db_session, {"name": "Totally other", "template_definition": definition}) is not None


@pytest.mark.parametrize("a,b,same", [
    ("Qubit dsDNA HS Assay", "Qubit 4 dsDNA HS quantitation", True),
    ("Qubit dsDNA HS Assay", "Qubit dsDNA BR Assay", False),
    ("KingFisher extraction", "KingFisher Extraction protocol", True),
])
def test_equivalent_names(a, b, same):
    assert cat.equivalent_names(a, b) is same


# ------------------------------------------------ G5 re-adding an existing column
def test_readding_an_existing_column_is_unchanged_not_a_stop(mig, monkeypatch):
    db, admin, configuration = mig.db, mig.admin, mig.configuration
    name = f"Extraction date {uuid.uuid4().hex[:4]}"
    add = _step("POST", "/v1/schema/columns", {"name": name, "table": "samples", "data_type": "date"}, target=name)
    run = _start(db, admin, configuration, monkeypatch, [add])
    result, code = svc.apply_run(db, admin, run.id, second_confirm=True)
    assert code == 200 and result.status == "done", result.steps[0].gap
    # The same call again, and the UAT shape: no call, a gap saying it exists.
    rerun = _start(db, admin, configuration, monkeypatch, [
        add, _gap_row(name, f"{name} already exists on samples; do not add it again"),
    ])
    assert [s.status for s in rerun.steps] == ["unchanged", "unchanged"]
    assert all(s.gap is None and s.decision == "excluded" for s in rerun.steps)
    payload = svc.run_payload(rerun, db, admin)
    assert payload["stopped_count"] == 0 and payload["banner"] is None


def test_existing_physical_column_on_an_unregistered_table_is_unchanged(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/v1/schema/columns", {"display_name": "Description", "table_id": "experiments", "data_type": "text"}),
    ])
    assert run.steps[0].status == "unchanged"


def test_a_gap_claiming_existence_is_not_trusted(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [
        _gap_row(f"Nothing like this {uuid.uuid4().hex[:6]}", "already exists; do not add it again"),
    ])
    assert run.steps[0].status == "stopped"


# ------------------------------------------------ near-matches

@pytest.mark.parametrize("a,b,near", [
    ("EDTA Tube", "K2EDTA Tube (5mL)", True),
    ("EDTA Tube", "96-Well Plate", False),
    ("EDTA Tube", "EDTA Tube", False),  # identical is an exact match, not a near one
    ("Cryovial", "Cryovial (2mL)", True),
])
def test_near_names(a, b, near):
    assert cat.near_names(a, b) is near


def test_near_match_container_type_is_surfaced_and_excluded(db_session, admin, configuration, monkeypatch):
    existing = "K2EDTA Tube (5mL)"
    if db_session.query(ContainerType).filter(ContainerType.name == existing).first() is None:
        db_session.add(ContainerType(name=existing, rows=1, columns=1))
    for row in db_session.query(ContainerType).filter(ContainerType.name.ilike("%edta%")).all():
        if row.name != existing:
            row.active = False
    db_session.commit()
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/containers/types", {"name": "EDTA Tube"}, target="EDTA Tube"),
        _step("POST", "/containers/types", {"name": f"Deep well plate {uuid.uuid4().hex[:4]}"}),
    ])
    assert [s.status for s in run.steps] == ["proposed", "proposed"]
    assert [s.decision for s in run.steps] == ["excluded", "included"]
    rows = svc.run_payload(run, db_session, admin)["steps"]
    assert rows[0]["near_matches"] == [f"container type '{existing}'"]
    assert rows[1]["near_matches"] == []
    # The user can still include it if it really is different.
    svc.set_included(db_session, admin, run.id, run.steps[0].id, True)


def test_prompt_tells_the_model_to_reuse_near_matches():
    prompt = llm._system_prompt(None, None)
    assert "K2EDTA Tube (5mL)" in prompt and "never write a gap for something that already exists" in prompt


# ------------------------------------------------ item 5: background run

def test_begin_run_returns_before_the_model_call(db_session, admin, configuration, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("begin_run must not call the model")

    monkeypatch.setattr(svc, "propose", boom)
    run, pending = svc.begin_run(db_session, admin, configuration.id, "goal")
    assert run.status == "reading_inputs" and run.steps == []
    assert pending.catalog and pending.run_id == run.id


def test_background_task_stores_the_proposal(db_session, admin, configuration, monkeypatch):
    _propose(monkeypatch, [_step("POST", "/lists", {"name": f"L_{uuid.uuid4().hex[:6]}"})])
    run, pending = svc.begin_run(db_session, admin, configuration.id, "goal")
    svc.run_in_background(pending, session_factory=lambda: db_session)
    db_session.refresh(run)
    assert run.status == "proposing" and len(run.steps) == 1


def test_background_provider_error_marks_the_run_failed(db_session, admin, configuration, monkeypatch):
    def fail(*_a, **_k):
        raise llm.ProviderError("The model call failed. Check the key and the model.")

    monkeypatch.setattr(svc, "propose", fail)
    run, pending = svc.begin_run(db_session, admin, configuration.id, "goal")
    svc.run_in_background(pending, session_factory=lambda: db_session)
    db_session.refresh(run)
    assert run.status == "failed" and "model call failed" in run.error_message


def test_a_stale_reading_run_is_marked_failed(db_session, admin, configuration, monkeypatch):
    monkeypatch.setattr(svc, "propose", lambda *_a, **_k: {"steps": []})
    run, _pending = svc.begin_run(db_session, admin, configuration.id, "goal")
    run.created_at = datetime.now(timezone.utc) - timedelta(seconds=llm.model_timeout() + 600)
    db_session.commit()
    assert svc.expire_stale(db_session, run).status == "failed"
    fresh, _ = svc.begin_run(db_session, admin, configuration.id, "goal")
    assert svc.expire_stale(db_session, fresh).status == "reading_inputs"


def test_http_start_is_202_then_polling_shows_the_proposal(client, db_session, test_admin_user, monkeypatch):
    monkeypatch.delenv("CONFIGURING_AGENT_ASYNC", raising=False)
    monkeypatch.setattr(svc, "BACKGROUND_SESSION_FACTORY", lambda: db_session)
    login = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    configuration = Configuration(id=uuid.uuid4(), client_id=test_admin_user.client_id, name=f"A {uuid.uuid4().hex[:6]}")
    db_session.add(configuration)
    db_session.commit()
    _propose(monkeypatch, [_step("POST", "/lists", {"name": f"L_{uuid.uuid4().hex[:6]}"})])
    r = client.post(f"/v1/configuring-agent/configurations/{configuration.id}/runs", json={"goal_note": "g"}, headers=headers)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "reading_inputs" and r.json()["steps"] == []
    # TestClient runs the background task after the response.
    polled = client.get(f"/v1/configuring-agent/runs/{r.json()['id']}", headers=headers)
    assert polled.status_code == 200
    assert polled.json()["status"] == "proposing" and len(polled.json()["steps"]) == 1


def test_timeout_default_still_300():
    assert llm.DEFAULT_TIMEOUT_S == 300.0


# ------------------------------------------------ reagent tracking (kit-lot stop points at it)

@pytest.mark.parametrize("name", [
    "Kit lot number", "Qubit kit part number", "Reagent expiry date", "Lot", "Expiration Date",
    "Instrument serial", "Catalog number", "Exp date", "Reagent lot",
])
def test_per_run_kit_lot_part_expiry_columns_stop_at_proposal(db_session, admin, configuration, monkeypatch, name):
    run = _start(db_session, admin, configuration, monkeypatch, [
        _step("POST", "/v1/schema/columns", {"display_name": name, "table_id": "samples", "data_type": "text"}),
    ])
    assert run.steps[0].status == "stopped"
    assert "reagent tracking" in run.steps[0].gap
    assert "POST /v1/reagents" in run.steps[0].gap and "POST /v1/reagent-uses" in run.steps[0].gap


@pytest.mark.parametrize("name", ["Plot ID", "Slot position", "Volume (uL)", "Parent sample", "Qubit dsDNA HS reagent volume", "Kit Note"])
def test_ordinary_columns_are_not_mistaken_for_reagent_tracking(name):
    assert not cat.reagent_tracking_column({"display_name": name})


def test_reagent_tracking_column_stops_at_apply_and_writes_nothing(db_session, admin):
    import asyncio

    from app.services.configuring_agent_apply import CannotExpress, execute_step
    from models.ui_schema import SchemaColumn

    with pytest.raises(CannotExpress) as stop:
        execute_step(db_session, admin, "POST", "/v1/schema/columns",
                                 {"display_name": "Kit lot", "table_id": "samples", "data_type": "text"})
    assert "reagent tracking" in str(stop.value)
    assert not db_session.query(SchemaColumn).filter(SchemaColumn.display_name == "Kit lot").count()
    assert "kit_lot" not in {r[0] for r in db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'samples'"))}


def test_prompt_points_kit_lots_to_reagent_tracking():
    prompt = llm._system_prompt(None, "")
    assert "Use reagent tracking instead" in prompt and "POST /v1/vendors" in prompt
    assert "columns for them" in prompt
