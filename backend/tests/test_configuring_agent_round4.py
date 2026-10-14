"""Configuring agent fixes from the UAT re-score on main 1787efc (D-6).

1. A routing redo came back 'unchanged' with no call: its target 'routing_map'
   named an existing table, and the call-less G5 path marked it No change.
   Stops now win, and No change needs a DB object the row only adds or reuses.
2. An escalation redo returned 400 'no steps'. Zero steps or a bare refusal is
   now one stop row with the reason.
"""

import pytest

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_llm as llm
from app.services import configuring_agent_service as svc
from tests.test_configuring_agent_locks import (  # noqa: F401  (fixtures)
    _no_live_provider,
    _propose,
    _start,
    admin,
    configuration,
)

ROUTING = {"group": "other", "target": "routing_map", "action": "replace automatic Qubit dsDNA routing",
           "why": "Post-extraction assay routing is not in the SOP and routing calls are forbidden"}


def _list_step(name):
    return {"group": "other", "target": name, "action": f"Create list {name}", "why": "SOP",
            "call": {"method": "POST", "path": "/lists", "body": {"name": name}}}


# ------------------------------------------------ 1. routing / asked-for are stops

def test_uat_routing_row_is_a_stop_not_unchanged(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [dict(ROUTING)])
    step = run.steps[0]
    assert step.status == "stopped"
    assert "Routing stays as built." in step.gap
    assert step.decision == svc.INCLUDED  # Apply refuses while it is in


def test_routing_redo_is_a_stop(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step("RedoRouting")])
    _propose(monkeypatch, [dict(ROUTING)])
    redone = svc.redo_step(db_session, admin, run.id, run.steps[0].id, "route every DNA sample to Qubit")
    assert redone.steps[0].status == "stopped" and "Routing" in redone.steps[0].gap
    assert redone.status == "stopped"


@pytest.mark.parametrize("raw", [
    {"target": "Asked-for", "action": "Add DNA QC to asked-for"},
    {"target": "Samples", "action": "Route DNA samples to Qubit"},
    {"target": "routing map", "action": "Use routing map as is"},
])
def test_routing_and_asked_for_requests_are_stops(db_session, admin, configuration, monkeypatch, raw):
    run = _start(db_session, admin, configuration, monkeypatch, [dict(raw, group="other", why="SOP")])
    assert run.steps[0].status == "stopped"


def test_a_change_to_an_existing_object_without_a_call_is_a_stop(db_session, admin, configuration, monkeypatch):
    raw = {"group": "other", "target": "samples", "action": "Update the Samples table", "why": "SOP"}
    run = _start(db_session, admin, configuration, monkeypatch, [raw])
    assert run.steps[0].status == "stopped"


def test_existing_object_added_as_is_is_still_no_change(db_session, admin, configuration, monkeypatch):
    raw = {"group": "schema_tables", "target": "Samples", "action": "Add Samples table", "why": "SOP",
           "gap": "Samples already exists."}
    run = _start(db_session, admin, configuration, monkeypatch, [raw])
    assert run.steps[0].status == "unchanged"


def test_change_words():
    assert allow.asks_for_a_change({"action": "replace automatic Qubit dsDNA routing"})
    assert allow.asks_for_a_change({"action": "Grant schema:edit"})
    assert not allow.asks_for_a_change({"action": "Set up the Samples table"})
    assert not allow.asks_for_a_change({"action": "Reuse K2EDTA Tube (5mL)"})


# ------------------------------------------------ 2. zero steps / refusal -> stop row

@pytest.mark.parametrize("reply", [
    {"steps": []},
    {"steps": [], "reason": "Granting schema:edit is not allowed."},
    {"refusal": "I can't change role permissions."},
    {},
])
def test_redo_with_no_steps_is_a_stop_row_not_400(db_session, admin, configuration, monkeypatch, reply):
    run = _start(db_session, admin, configuration, monkeypatch, [_list_step("RedoEsc")])
    monkeypatch.setattr(svc, "propose", lambda *_a, **_k: reply)
    redone = svc.redo_step(db_session, admin, run.id, run.steps[0].id, "grant schema:edit to Configuration Editor")
    step = redone.steps[0]
    assert step.status == "stopped" and step.call_method is None
    assert svc.NO_STEPS_GAP in step.gap
    assert step.target == "RedoEsc"
    for word in ("schema:edit", "role permissions"):
        if word in str(reply):
            assert word in step.gap
    assert len(redone.steps) == 1


def test_start_with_no_steps_is_one_stop_row(db_session, admin, configuration, monkeypatch):
    run = _start(db_session, admin, configuration, monkeypatch, [])
    assert [s.status for s in run.steps] == ["stopped"]
    assert run.status == "stopped"


def test_parser_accepts_a_bare_refusal_object():
    assert llm._parse_json('{"refusal": "Granting schema:edit is not allowed."}')["refusal"]
    assert llm._parse_json('Sorry. {"gap": "No API."}')["gap"] == "No API."


def test_parser_still_rejects_a_nested_row_of_a_cut_off_reply():
    cut = '{"steps": [{"target": "x", "gap": "y"}, {"target": "z"'
    with pytest.raises(llm.BadReply):
        llm._parse_json(cut)
