"""Configuring agent fixes from the UAT re-score on main e217b58.

D-7: the CMDL-SOP2310 rerun proposed an invalid 'dna extraction' transition
(operation must be aliquot or pool) and a 'Request ID' row near-matched to the
platform column 'Id'. Qubit: the first async run failed with 'no JSON'; the
reply is now parsed tolerantly and retried once. The live model can't run in
CI (tests/KNOWN_FAILURES.md).
"""

import asyncio
import uuid

import pytest

from app.services import configuring_agent_catalog as cat
from app.services import configuring_agent_llm as llm
from app.services.configuring_agent_apply import CannotExpress, execute_step
from models.list import List as ListModel, ListEntry
from models.sample import SampleTypeTransition
from tests.test_configuring_agent_locks import (  # noqa: F401  (fixtures)
    _no_live_provider,
    _start,
    admin,
    configuration,
)


def _step(method, path, body, target="t"):
    return {"group": "other", "target": target, "action": "a", "why": "SOP",
            "call": {"method": method, "path": path, "body": body}}


@pytest.fixture
def blood_to_dna(db_session, admin):
    lst = cat.find_list(db_session, "sample_types")
    if lst is None:
        lst = ListModel(name="sample_types")
        db_session.add(lst)
        db_session.flush()
    slug = uuid.uuid4().hex[:6]
    blood = ListEntry(list_id=lst.id, name=f"Blood {slug}")
    dna = ListEntry(list_id=lst.id, name=f"DNA {slug}")
    db_session.add_all([blood, dna])
    db_session.flush()
    return blood, dna


def _transition(blood, dna, operation):
    return _step("POST", "/v1/sample-type-transitions", {
        "active": True, "operation": operation,
        "source_sample_type": str(blood.id), "allowed_dest_sample_type": str(dna.id)}, target="Blood to DNA")


def _existing(db, admin, blood, dna, operation="aliquot"):
    db.add(SampleTypeTransition(client_id=admin.client_id, source_sample_type=blood.id, operation=operation,
                                allowed_dest_sample_type=dna.id, created_by=admin.id, modified_by=admin.id))
    db.flush()


# ------------------------------------------------ D-7 transition

def test_rerun_of_dna_extraction_transition_is_no_change(db_session, admin, configuration, monkeypatch, blood_to_dna):
    blood, dna = blood_to_dna
    _existing(db_session, admin, blood, dna)
    run = _start(db_session, admin, configuration, monkeypatch, [_transition(blood, dna, "dna extraction")])
    assert run.steps[0].status == "unchanged"
    assert run.steps[0].call_body["operation"] == "aliquot"


def test_invalid_operation_without_an_existing_edge_stops_at_proposal(db_session, admin, configuration, monkeypatch,
                                                                      blood_to_dna):
    blood, dna = blood_to_dna
    run = _start(db_session, admin, configuration, monkeypatch, [_transition(blood, dna, "dna extraction")])
    assert run.steps[0].status == "stopped"
    assert "aliquot or pool" in run.steps[0].gap


def test_invalid_operation_stops_at_apply_and_writes_nothing(db_session, admin, blood_to_dna):
    blood, dna = blood_to_dna
    body = _transition(blood, dna, "dna extraction")["call"]["body"]
    with pytest.raises(CannotExpress) as stop:
        execute_step(db_session, admin, "POST", "/v1/sample-type-transitions", body)
    assert "aliquot or pool" in str(stop.value)
    assert not db_session.query(SampleTypeTransition).filter(
        SampleTypeTransition.source_sample_type == blood.id).count()


def test_apply_of_dna_extraction_against_existing_edge_is_a_noop(db_session, admin, blood_to_dna):
    blood, dna = blood_to_dna
    _existing(db_session, admin, blood, dna)
    body = _transition(blood, dna, "dna extraction")["call"]["body"]
    changes = execute_step(db_session, admin, "POST", "/v1/sample-type-transitions", body)
    assert changes[0].noop
    assert db_session.query(SampleTypeTransition).filter(
        SampleTypeTransition.source_sample_type == blood.id).count() == 1


@pytest.mark.parametrize("operation,expected", [("Pooling", "pool"), ("ALIQUOT", "aliquot"), ("combine", "pool")])
def test_operation_words_normalize(db_session, admin, operation, expected):
    assert cat.transition_operation(db_session, admin, {"operation": operation}) == expected


def test_prompt_states_transition_operations():
    assert "aliquot or pool only" in llm._system_prompt(None, "")


# ------------------------------------------------ D-7 Request ID near-match

def test_request_id_is_not_a_near_match_for_the_platform_id(db_session, admin, configuration, monkeypatch):
    name = f"Request ID {uuid.uuid4().hex[:4]}"
    body = {"display_name": name, "table_id": "samples", "data_type": "text"}
    assert cat.near_matches(db_session, admin, "POST", "/v1/schema/columns", body) == []
    run = _start(db_session, admin, configuration, monkeypatch, [_step("POST", "/v1/schema/columns", body)])
    assert run.steps[0].status == "proposed" and run.steps[0].decision in ("included", "accepted")


def test_user_columns_still_near_match(db_session, admin):
    near = cat.near_matches(db_session, admin, "POST", "/v1/schema/columns",
                            {"display_name": "Client Sample", "table_id": "samples"})
    assert any("Client Sample" in n for n in near)


# ------------------------------------------------ Qubit 'no JSON'

REPLY = '{"steps": [{"target": "x", "call": {"method": "POST", "path": "/analytes", "body": {"name": "a"}}}]}'


@pytest.mark.parametrize("text", [
    REPLY,
    "```json\n" + REPLY + "\n```",
    "Here is the configuration:\n```json\n" + REPLY + "\n```\nLet me know.",
    "Sure. " + REPLY + " Done.",
])
def test_parse_accepts_fenced_and_wrapped_replies(text):
    assert llm._parse_json(text)["steps"][0]["target"] == "x"


@pytest.mark.parametrize("text", ["", "I cannot do that.", REPLY[:-20]])
def test_parse_rejects_empty_prose_and_truncated_replies(text):
    with pytest.raises(llm.BadReply):
        llm._parse_json(text)


def test_truncated_reply_does_not_return_a_nested_object():
    with pytest.raises(llm.BadReply) as bad:
        llm._parse_json(REPLY[:-3])
    assert "cut off" in bad.value.message


def test_bad_reply_is_retried_once_with_a_json_reminder(monkeypatch):
    prompts = []
    replies = iter(["Thinking... the answer follows", REPLY])

    def fake(provider, model, key, system, user):
        prompts.append(user)
        return next(replies)

    monkeypatch.setattr(llm, "_call", fake)
    out = llm.propose("xai", "m", "k", chunks=["c"], goal_note="g")
    assert out["steps"][0]["target"] == "x"
    assert len(prompts) == 2 and "JSON object only" in prompts[1]


def test_two_bad_replies_fail_with_a_clear_message(monkeypatch):
    monkeypatch.setattr(llm, "_call", lambda *a: "no json here")
    with pytest.raises(llm.ProviderError) as err:
        llm.propose("xai", "m", "k", chunks=["c"], goal_note="g")
    assert "twice" in err.value.message


def test_length_finish_reason_is_a_bad_reply(monkeypatch):
    class R:
        status_code = 200

        def json(self):
            return {"choices": [{"finish_reason": "length", "message": {"content": REPLY[:40]}}]}

    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: R())
    with pytest.raises(llm.BadReply) as bad:
        llm._openai_compatible("u", "m", "k", "s", "u")
    assert "cut off" in bad.value.message


def test_empty_or_null_content_is_a_bad_reply(monkeypatch):
    class R:
        status_code = 200

        def json(self):
            return {"choices": [{"finish_reason": "stop", "message": {"content": None}}]}

    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: R())
    with pytest.raises(llm.BadReply):
        llm._openai_compatible("u", "m", "k", "s", "u")
