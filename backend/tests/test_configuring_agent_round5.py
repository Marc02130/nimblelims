"""Follow-ups from the passing UAT on main 7d84e07.

1. 'Routing stays as built.' leaked onto gaps not about routing: the match read
   the model's why/gap text ('no route defines that field'). Only the request
   (target, action) is read now.
2. The CMDL rerun dropped Request ID and Sample Log Number. Calls an earlier
   run of the same source proposed or applied are listed in the prompt and kept
   as rows when the model leaves them out.
"""

import uuid

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_service as svc
from tests.test_configuring_agent_locks import (  # noqa: F401  (fixtures)
    _no_live_provider,
    _propose,
    _start,
    admin,
    configuration,
)


# ------------------------------------------------ 1. routing prefix

def test_uat_volume_gap_is_not_a_routing_stop(db_session, admin, configuration, monkeypatch):
    raw = {"group": "other", "target": "experiments", "action": "add working solution volume field",
           "why": "SOP records the volumes used to make the Qubit working solution",
           "gap": "Volumes used are per-run preparation data. Experiments cannot take new columns, "
                  "and no route defines that field."}
    run = _start(db_session, admin, configuration, monkeypatch, [raw])
    step = run.steps[0]
    assert step.status == "stopped"
    assert "Routing stays as built." not in step.gap
    assert step.gap.startswith("Volumes used")


def test_real_routing_request_keeps_the_reason(db_session, admin, configuration, monkeypatch):
    raw = {"group": "other", "target": "routing_map",
           "action": "do not route DNA samples to a Qubit dsDNA assay after extraction",
           "why": "Routing calls are forbidden.", "gap": "No allowed route updates the routing map."}
    run = _start(db_session, admin, configuration, monkeypatch, [raw])
    assert run.steps[0].status == "stopped" and run.steps[0].gap.startswith("Routing stays as built.")


def test_why_and_gap_text_never_trigger_the_area_reasons():
    assert allow.out_of_scope_request({"target": "Samples", "action": "Add Initials",
                                       "why": "route to Qubit", "gap": "asked-for is fixed"}) is None
    assert allow.out_of_scope_request({"target": "Asked-for", "action": "add DNA QC"}) == "Asked-for stays as built."


# ------------------------------------------------ 2. rerun coverage

def _column(name):
    return {"group": "schema_columns", "target": f"Samples.{name}", "action": "Add column", "why": "SOP",
            "call": {"method": "POST", "path": "/v1/schema/columns",
                     "body": {"display_name": name, "table_id": "samples", "data_type": "text"}}}


def test_rerun_keeps_fields_an_earlier_run_proposed(db_session, admin, configuration, monkeypatch):
    slug = uuid.uuid4().hex[:4]
    request, log, initials = f"Request ID {slug}", f"Sample Log Number {slug}", f"Initials {slug}"
    first = _start(db_session, admin, configuration, monkeypatch, [_column(request), _column(log), _column(initials)])
    assert [s.status for s in first.steps] == ["proposed"] * 3
    rerun = _start(db_session, admin, configuration, monkeypatch, [_column(initials)])
    names = [s.call_body["display_name"] for s in rerun.steps]
    assert sorted(names) == sorted([initials, request, log])
    kept = [s for s in rerun.steps if s.call_body["display_name"] != initials]
    assert all(s.status == "proposed" and s.why.startswith("Kept from an earlier run") for s in kept)


def test_rerun_keeps_applied_items_as_no_change(db_session, admin, configuration, monkeypatch):
    from models.container import ContainerType

    name = f"PP Tube {uuid.uuid4().hex[:4]}"
    step = {"group": "other", "target": name, "action": "Add container type", "why": "SOP",
            "call": {"method": "POST", "path": "/containers/types", "body": {"name": name}}}
    first = _start(db_session, admin, configuration, monkeypatch, [step])
    # Stand in for the applied first run: the row is applied and the object exists.
    db_session.add(ContainerType(name=name))
    first.steps[0].status = "applied"
    db_session.flush()
    rerun = _start(db_session, admin, configuration, monkeypatch, [])
    kept = [s for s in rerun.steps if s.call_path == "/containers/types"]
    assert len(kept) == 1 and kept[0].status == "unchanged"


def test_rerun_does_not_duplicate_a_row_the_model_kept(db_session, admin, configuration, monkeypatch):
    name = f"Request ID {uuid.uuid4().hex[:4]}"
    _start(db_session, admin, configuration, monkeypatch, [_column(name)])
    rerun = _start(db_session, admin, configuration, monkeypatch, [_column(name)])
    assert len(rerun.steps) == 1


def test_stopped_rows_are_not_carried(db_session, admin, configuration, monkeypatch):
    stop = {"group": "other", "target": "routing_map", "action": "route DNA to Qubit", "why": "SOP"}
    _start(db_session, admin, configuration, monkeypatch, [stop])
    rerun = _start(db_session, admin, configuration, monkeypatch, [_column(f"Initials {uuid.uuid4().hex[:4]}")])
    assert [s.status for s in rerun.steps] == ["proposed"]


def test_prompt_lists_earlier_items_for_the_same_source(db_session, admin, configuration, monkeypatch):
    name = f"Sample Log Number {uuid.uuid4().hex[:4]}"
    _start(db_session, admin, configuration, monkeypatch, [_column(name)])
    seen = {}

    def capture(*_a, **kw):
        seen.update(kw)
        return {"steps": [_column(name)]}

    monkeypatch.setattr(svc, "propose", capture)
    svc.start_run(db_session, admin, configuration.id, "goal")
    assert "Earlier runs of this source" in seen["catalog"] and f"Samples.{name}" in seen["catalog"]
