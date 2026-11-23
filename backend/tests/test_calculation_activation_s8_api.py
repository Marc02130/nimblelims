"""Calculations S8: review, confirm token, activation, test cases, and the agent.

Runs on the ``create_all`` schema, so the database triggers of 0124 to 0126 are
not present; the services' own checks are what these tests exercise. Inside
``db_session`` the database ``now()`` is constant for the whole test, so a token
whose ``issued_at`` is set to ``now() - 300 s`` is exactly 300 seconds old and
one set to ``now() - 301 s`` is 301. The triggers, privileges, and downgrade
are in ``test_calculation_activation_s8_db.py``.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Optional
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.agent_context import agent_run_context
from app.services import calculation_activation as activation
from app.services.calculation_runtime import expected_lock_from_commit
from tests.test_calculation_config_s7 import ad_hoc, config, field, stage_copy
from tests.test_calculation_config_s7_api import (  # noqa: F401  (fixtures)
    _body,
    _code,
    _row,
    _url,
    manager_headers,
    plain_headers,
)
from tests.test_result_promotion import (  # noqa: F401  (fixtures)
    analysis_and_analyte,
    auth_headers,
)

LOCK = expected_lock_from_commit().lock_hash


def _save(client: TestClient, headers, ids, configuration=None, order=1, analyte="lead_id"):
    cfg = configuration or config(stage_copy(), name=f"cfg-{analyte}")
    r = client.put(_url(ids, analyte), headers=headers, json=_body(cfg, order))
    assert r.status_code == 200, r.text
    return r.json()


def _review(client: TestClient, headers, ids, analyte="lead_id"):
    r = client.get(_url(ids, analyte, "calculation-config/activation-review"), headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _token(client: TestClient, headers, ids, review_hash: str, analyte="lead_id"):
    return client.post(
        _url(ids, analyte, "calculation-config/activation-token"),
        headers=headers,
        json={"review_hash": review_hash},
    )


def _issue(client: TestClient, headers, ids, analyte="lead_id") -> str:
    shown = _review(client, headers, ids, analyte)
    r = _token(client, headers, ids, shown["review_hash"], analyte)
    assert r.status_code == 201, r.text
    return r.json()["confirm_token"]


def _activate(client: TestClient, headers, ids, token: str, analyte="lead_id"):
    return client.post(
        _url(ids, analyte, "calculation-config/activate"),
        headers=headers,
        json={"confirm_token": token},
    )


def _set_age(db_session, seconds: int) -> None:
    db_session.execute(
        text("UPDATE calculation_confirm_tokens SET issued_at = now() - make_interval(secs => :s)"),
        {"s": seconds},
    )
    db_session.flush()


def _counts(db_session) -> Dict[str, int]:
    return {
        table: db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in (
            "calculation_activations",
            "calculation_confirm_tokens",
            "calculation_test_cases",
            "calculation_test_case_results",
            "calculation_dry_runs",
            "results",
        )
    }


def _login(client: TestClient, username: str, password: str):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def second_admin_headers(client: TestClient, db_session, test_org, test_admin_user):
    from app.core.security import get_password_hash
    from models.user import User

    user = User(
        name="Second Admin",
        username="admin-two",
        email="admin-two@example.com",
        password_hash=get_password_hash("admintwopassword"),
        role_id=test_admin_user.role_id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    return _login(client, "admin-two", "admintwopassword")


def _add_case(client, headers, ids, name="case", source="independent", analyte="lead_id", **extra):
    body = {"name": name, "inputs": {"OD 450": "0.5"}, "expected": {"calculated": "0.5"}, **extra}
    if source is not None:
        body["expected_source"] = source
    return client.post(_url(ids, analyte, "calculation-config/test-cases"), headers=headers, json=body)


def _record_result(db_session, case_id: str, passed: bool, lock: str = LOCK) -> None:
    from models.calculation import CalculationTestCaseResult

    db_session.add(CalculationTestCaseResult(test_case_id=UUID(case_id), lock_hash=lock, passed=passed))
    db_session.commit()


# ---- the review document (CALC-REQ-45) ----------------------------------------


def test_the_review_holds_every_item_the_spec_lists(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    document = shown["document"]
    assert document["schema"] == "calculation_activation_review/1"
    assert document["lock_hash"] == LOCK, "a document without the lock hash fails the rule"
    assert document["analysis"]["id"] == ids["analysis_id"]
    assert document["analyte"]["name"] == ids["lead_name"]
    assert document["configuration"]["version"] == 1 and document["configuration"]["name"] == "cfg-lead_id"
    assert document["function_versions"] == [{"function": "copy_raw", "version": 1}]
    assert document["validation_state"] == "no_test_cases"
    assert document["test_cases"]["none_recorded"] is True
    assert document["test_cases"]["notice"] == "No test cases recorded"
    assert document["confirm_label"] == "Activate with no test cases recorded"
    assert document["dry_run"] == {"done": False, "run_at": None, "input": None}
    assert document["diff"] == {"previous_version": None, "summary": "no previous version", "changes": []}
    declaration = document["stage_declarations"][0]
    assert declaration == {
        "stage": "copy",
        "outcome": "run_failed",
        "verdict": None,
        "flag": None,
        "missing_limit_flag": None,
        "gates": [],
        "precedence_place": 1,
        "reads_limit": False,
    }
    plain = document["plain_language"]
    assert "copy_raw version 1" in plain["stages"][0]["text"]
    assert "OD 450" in plain["stages"][0]["text"]
    assert "will be published as the analyte's result when the experiment is published" in plain["result_pointer"]
    assert re.fullmatch(r"[0-9a-f]{64}", shown["review_hash"])


def test_the_plain_language_text_matches_the_catalog_description(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    catalog = {e["name"]: e for e in client.get("/v1/calculation-catalog", headers=auth_headers).json()}
    text_ = _review(client, auth_headers, ids)["document"]["plain_language"]["stages"][0]["text"]
    assert catalog["copy_raw"]["description"] in text_


def test_a_stage_that_reads_a_limit_shows_the_missing_limit_flag(client, auth_headers, analysis_and_analyte):
    from tests.test_calculation_config_s7 import stage_limit

    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(stage_limit(value=field("Mean"))))
    declaration = _review(client, auth_headers, ids)["document"]["stage_declarations"][0]
    assert declaration["reads_limit"] is True
    assert declaration["missing_limit_flag"] == "limit_missing"
    assert declaration["flag"] == "above_limit" and declaration["outcome"] == "flag"


def test_two_builds_at_different_times_hash_the_same(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    first = _review(client, auth_headers, ids)
    db_session.execute(text("SELECT pg_sleep(0.05)"))
    second = _review(client, auth_headers, ids)
    assert first["review_hash"] == second["review_hash"]
    assert first["document"] == second["document"]


def test_the_document_has_no_render_time_nonce_countdown_or_identity(
    client, auth_headers, analysis_and_analyte, test_admin_user
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    blob = json.dumps(shown["document"])
    for name in ("rendered_at", "render_time", "nonce", "countdown", "expires", "timestamp"):
        assert name not in blob.lower(), name
    assert str(test_admin_user.id) not in blob
    assert test_admin_user.email not in blob and test_admin_user.username not in blob
    assert test_admin_user.name not in blob
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob)
    assert "created_by" not in blob and "password" not in blob.lower() and "token" not in blob.lower()
    assert "sop" not in blob.lower()


def test_the_review_hash_is_the_sha256_of_the_jcs_encoding_and_the_export_is_the_same_bytes(
    client, auth_headers, analysis_and_analyte, db_session
):
    from app.services import jcs

    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    before = _counts(db_session)
    r = client.get(_url(ids, "lead_id", "calculation-config/activation-review/export"), headers=auth_headers)
    assert r.status_code == 200
    assert r.content == jcs.canonical_bytes(shown["document"])
    assert hashlib.sha256(r.content).hexdigest() == shown["review_hash"] == r.headers["x-review-hash"]
    assert r.headers["content-type"].startswith("application/json")
    assert _counts(db_session) == before, "exporting the evidence writes no result and no attempt"
    assert _row(db_session, ids).calculation_config_state == "draft"


def test_the_review_is_for_admins_only(client, auth_headers, manager_headers, plain_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    for suffix in ("calculation-config/activation-review", "calculation-config/activation-review/export"):
        url = _url(ids, "lead_id", suffix)
        assert client.get(url, headers=manager_headers).status_code == 403
        assert client.get(url, headers=plain_headers).status_code == 403
        assert client.get(url).status_code in (401, 403)


def test_a_review_needs_a_draft_configuration(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    r = client.get(_url(ids, "lead_id", "calculation-config/activation-review"), headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "configuration_missing"
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, token).status_code == 200
    r = client.get(_url(ids, "lead_id", "calculation-config/activation-review"), headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "already_active"


# ---- the confirm token (CALC-REQ-34) ------------------------------------------


def test_a_token_is_issued_for_the_hash_shown_and_stored_only_hashed(
    client, auth_headers, analysis_and_analyte, db_session, test_admin_user
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    r = _token(client, auth_headers, ids, shown["review_hash"])
    assert r.status_code == 201
    body = r.json()
    assert body["expires_in_seconds"] == 300 and body["review_hash"] == shown["review_hash"]
    token = body["confirm_token"]
    assert len(token) >= 40
    row = db_session.execute(text("SELECT * FROM calculation_confirm_tokens")).mappings().one()
    assert row["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert token not in json.dumps({k: str(v) for k, v in row.items()})
    assert row["user_id"] == test_admin_user.id
    assert str(row["analysis_id"]) == ids["analysis_id"] and str(row["analyte_id"]) == ids["lead_id"]
    assert row["configuration_version"] == 1 and row["review_hash"] == shown["review_hash"]
    assert row["session_jti"] and row["consumed_at"] is None


def test_two_tokens_are_different(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    assert _issue(client, auth_headers, ids) != _issue(client, auth_headers, ids)


def test_a_token_for_a_hash_that_was_not_shown_is_refused(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    r = _token(client, auth_headers, ids, "0" * 64)
    assert r.status_code == 400 and _code(r) == "review_changed"
    r = client.post(
        _url(ids, "lead_id", "calculation-config/activation-token"), headers=auth_headers, json={}
    )
    assert r.status_code == 400 and _code(r) == "review_hash_required"
    assert _counts(db_session)["calculation_confirm_tokens"] == 0


def test_a_review_that_changed_after_it_was_shown_gets_no_token(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    assert _add_case(client, auth_headers, ids).status_code == 201
    r = _token(client, auth_headers, ids, shown["review_hash"])
    assert r.status_code == 400 and _code(r) == "review_changed"


def test_only_admins_get_a_token_or_activate(
    client, auth_headers, manager_headers, plain_headers, analysis_and_analyte, db_session
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    for headers in (manager_headers, plain_headers):
        assert _token(client, headers, ids, shown["review_hash"]).status_code == 403
    token = _issue(client, auth_headers, ids)
    for headers in (manager_headers, plain_headers):
        assert _activate(client, headers, ids, token).status_code == 403, "a Lab Manager is refused"
    assert _row(db_session, ids).calculation_config_state == "draft"
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None


def test_activation_takes_the_token_and_nothing_else(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    url = _url(ids, "lead_id", "calculation-config/activate")
    for body, code in (
        ({}, "confirm_token_required"),
        ({"confirm_token": ""}, "confirm_token_required"),
        ({"confirm_token": 5}, "confirm_token_required"),
        ({"confirm_token": token, "password": "adminpassword"}, "unknown_field"),
        ({"confirm_token": token, "reason": "because"}, "unknown_field"),
        ({"confirm_token": "not-a-token"}, "confirm_token_invalid"),
    ):
        r = client.post(url, headers=auth_headers, json=body)
        assert r.status_code == 400 and _code(r) == code, (body, r.text)
    assert _activate(client, auth_headers, ids, token).status_code == 200, "no password was needed"


def test_a_token_is_accepted_at_300_seconds_and_refused_at_301(
    client, auth_headers, analysis_and_analyte, db_session
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)

    _set_age(db_session, 301)
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_expired"
    assert _row(db_session, ids).calculation_config_state == "draft"
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None

    _set_age(db_session, 300)
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 200, r.text
    assert _row(db_session, ids).calculation_config_state == "active"


def test_a_token_is_single_use(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, token).status_code == 200
    consumed = db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar()
    assert consumed is not None
    # The analysis goes back to draft under a new analysis version, so the same
    # configuration version is activatable again. The old token is spent.
    assert client.post(f"/v1/analyses/{ids['analysis_id']}/new-version", headers=auth_headers).status_code == 200
    assert _row(db_session, ids).calculation_config_state == "draft"
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_used"
    assert _row(db_session, ids).calculation_config_state == "draft"


def test_a_token_for_proposal_a_is_refused_for_proposal_b(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(stage_copy(), name="proposal-a"), order=1, analyte="lead_id")
    _save(client, auth_headers, ids, config(stage_copy(), name="proposal-b"), order=2, analyte="arsenic_id")
    token_a = _issue(client, auth_headers, ids, "lead_id")
    r = _activate(client, auth_headers, ids, token_a, analyte="arsenic_id")
    assert r.status_code == 400 and _code(r) == "confirm_token_wrong_proposal"
    assert _row(db_session, ids, "arsenic_id").calculation_config_state == "draft"
    assert _row(db_session, ids, "lead_id").calculation_config_state == "draft"
    assert _activate(client, auth_headers, ids, token_a, analyte="lead_id").status_code == 200


def test_a_token_from_one_sign_in_is_refused_in_another(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    other_session = _login(client, "admin", "adminpassword")
    assert other_session["Authorization"] != auth_headers["Authorization"]
    r = _activate(client, other_session, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_wrong_session"
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None
    assert _activate(client, auth_headers, ids, token).status_code == 200


def test_a_token_issued_to_one_admin_is_refused_for_another(
    client, auth_headers, second_admin_headers, analysis_and_analyte, db_session
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    r = _activate(client, second_admin_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_wrong_user"
    assert _row(db_session, ids).calculation_config_state == "draft"


def test_a_token_is_bound_to_the_configuration_version(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(stage_copy(), name="cfg"))
    token = _issue(client, auth_headers, ids)
    changed = config(stage_copy(), name="cfg")
    changed["stages"][0]["bindings"]["value"] = field("OD 620")
    saved = _save(client, auth_headers, ids, changed)
    assert saved["version"] == 2
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_version_changed"
    assert _row(db_session, ids).calculation_config_state == "draft"


def test_a_token_is_bound_to_the_review_hash(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    assert _add_case(client, auth_headers, ids).status_code == 201
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "confirm_token_review_changed"
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None
    fresh = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, fresh).status_code == 200


def test_a_failed_activation_rolls_back_so_the_token_stays_unconsumed(
    client, auth_headers, analysis_and_analyte, db_session, monkeypatch
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)

    class Exploding:
        def __init__(self, **_kwargs: Any) -> None:
            raise RuntimeError("the database refused the activation row")

    monkeypatch.setattr(activation, "CalculationActivation", Exploding)
    with pytest.raises(RuntimeError):
        _activate(client, auth_headers, ids, token)
    db_session.rollback()
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None
    assert _row(db_session, ids).calculation_config_state == "draft"
    assert _counts(db_session)["calculation_activations"] == 0

    monkeypatch.undo()
    assert _activate(client, auth_headers, ids, token).status_code == 200


# ---- activation and its record (CALC-REQ-35) ----------------------------------


def test_an_admin_activates_and_the_record_holds_the_review_and_the_actor(
    client, auth_headers, analysis_and_analyte, db_session, test_admin_user
):
    ids = analysis_and_analyte
    saved = _save(client, auth_headers, ids)
    assert saved["state"] == "draft"
    shown = _review(client, auth_headers, ids)
    token = _token(client, auth_headers, ids, shown["review_hash"]).json()["confirm_token"]
    # A client header never sets the agent run context.
    headers = {**auth_headers, "X-Configuring-Agent-Run": "1", "X-Agent-Run": "true"}
    r = _activate(client, headers, ids, token)
    assert r.status_code == 200, r.text
    record = r.json()
    assert record["created_by"] == str(test_admin_user.id), "the Admin who proposed and activated is the named person"
    assert record["configuration_name"] == "cfg-lead_id" and record["configuration_version"] == 1
    assert record["function_versions"] == [{"function": "copy_raw", "version": 1}]
    assert record["lock_hash"] == LOCK
    assert record["validation_state"] == "no_test_cases"
    assert record["review_hash"] == shown["review_hash"]
    assert record["review_document"] == shown["document"]
    assert record["review_document"]["confirm_label"] == "Activate with no test cases recorded"
    assert _row(db_session, ids).calculation_config_state == "active"

    listed = client.get(_url(ids, "lead_id", "calculation-config/activations"), headers=auth_headers).json()
    assert [row["id"] for row in listed] == [record["id"]]
    again = client.get(_url(ids, "lead_id", "calculation-config"), headers=auth_headers).json()
    assert again["state"] == "active"
    assert _counts(db_session)["results"] == 0, "activation writes no result"


def test_the_stored_document_holds_no_identity_or_secret(
    client, auth_headers, analysis_and_analyte, test_admin_user
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    record = _activate(client, auth_headers, ids, token).json()
    blob = json.dumps(record["review_document"])
    assert token not in blob
    assert str(test_admin_user.id) not in blob and test_admin_user.email not in blob
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob)
    assert "password" not in blob.lower() and "token" not in blob.lower()


def test_an_active_configuration_cannot_be_activated_again_or_edited(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, token).status_code == 200
    r = _activate(client, auth_headers, ids, token)
    assert r.status_code == 400 and _code(r) == "already_active"
    r = client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy(), name="other")))
    assert r.status_code == 400 and _code(r) == "calculation_config_active"


def test_activation_needs_a_configuration(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    r = _activate(client, auth_headers, ids, "x" * 43)
    assert r.status_code == 400 and _code(r) == "configuration_missing"
    r = client.post(
        f"/v1/analyses/{ids['analysis_id']}/analytes/{UUID(int=5)}/calculation-config/activate",
        headers=auth_headers,
        json={"confirm_token": "x"},
    )
    assert r.status_code == 404


def test_activation_succeeds_whatever_the_test_counts(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    case = _add_case(client, auth_headers, ids, "never passes").json()
    _record_result(db_session, case["id"], False)
    shown = _review(client, auth_headers, ids)
    assert shown["document"]["validation_state"] == "tests_none_passed"
    assert shown["document"]["confirm_label"] == "Activate"
    token = _token(client, auth_headers, ids, shown["review_hash"]).json()["confirm_token"]
    record = _activate(client, auth_headers, ids, token).json()
    assert record["validation_state"] == "tests_none_passed"
    assert record["review_document"]["test_cases"]["passed_on_current_lock"] == 0


# ---- test cases and provenance (CALC-REQ-45 items 1 to 4) ---------------------


def test_three_cases_two_passing_one_from_system_output_and_no_dry_run(
    client, auth_headers, analysis_and_analyte, db_session
):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    first = _add_case(client, auth_headers, ids, "published example", "independent").json()
    second = _add_case(client, auth_headers, ids, "second example", "independent").json()
    third = _add_case(client, auth_headers, ids, "from the output", "system_output").json()
    assert third["from_system_output"] is True and first["from_system_output"] is False
    _record_result(db_session, first["id"], True)
    _record_result(db_session, second["id"], True)
    _record_result(db_session, third["id"], False)

    shown = _review(client, auth_headers, ids)
    tests = shown["document"]["test_cases"]
    assert tests["summary"] == "3 test cases, 2 passed, 1 from system output, no dry run"
    assert (tests["total"], tests["passed_on_current_lock"], tests["from_system_output"]) == (3, 2, 1)
    assert tests["none_recorded"] is False and tests["notice"] is None
    assert [c["from_system_output"] for c in tests["cases"]].count(True) == 1
    assert shown["document"]["validation_state"] == "tests_some_passed"
    assert shown["document"]["confirm_label"] == "Activate"

    token = _token(client, auth_headers, ids, shown["review_hash"]).json()["confirm_token"]
    record = _activate(client, auth_headers, ids, token).json()
    stored = record["review_document"]["test_cases"]
    assert stored["summary"] == "3 test cases, 2 passed, 1 from system output, no dry run"
    assert record["validation_state"] == "tests_some_passed"


def test_a_pass_on_another_lock_hash_does_not_count(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    case = _add_case(client, auth_headers, ids).json()
    _record_result(db_session, case["id"], True, lock="f" * 64)
    tests = _review(client, auth_headers, ids)["document"]["test_cases"]
    assert tests["passed_on_current_lock"] == 0
    assert tests["cases"][0]["passed_on_current_lock"] is None
    _record_result(db_session, case["id"], True)
    assert _review(client, auth_headers, ids)["document"]["test_cases"]["passed_on_current_lock"] == 1


def test_the_latest_outcome_on_the_lock_is_the_one_that_counts(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    case = _add_case(client, auth_headers, ids).json()
    _record_result(db_session, case["id"], True)
    db_session.execute(text("UPDATE calculation_test_case_results SET run_at = now() - interval '1 hour'"))
    _record_result(db_session, case["id"], False)
    assert _review(client, auth_headers, ids)["document"]["test_cases"]["passed_on_current_lock"] == 0


def test_a_dry_run_shows_its_time_and_input(client, auth_headers, analysis_and_analyte, db_session):
    from models.calculation import CalculationDryRun

    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    db_session.add(
        CalculationDryRun(
            analysis_id=UUID(ids["analysis_id"]),
            analyte_id=UUID(ids["lead_id"]),
            configuration_version=1,
            input={"OD 450": "0.5"},
        )
    )
    db_session.commit()
    document = _review(client, auth_headers, ids)["document"]
    dry = document["dry_run"]
    assert dry["done"] is True and dry["input"] == {"OD 450": "0.5"} and dry["run_at"]
    assert document["test_cases"]["summary"] == f"No test cases recorded, dry run done {dry['run_at']}"
    assert _counts(db_session)["results"] == 0


def test_a_test_case_is_recorded_for_the_current_version_only(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(stage_copy(), name="cfg"))
    _add_case(client, auth_headers, ids)
    changed = config(stage_copy(), name="cfg")
    changed["stages"][0]["bindings"]["value"] = field("OD 620")
    _save(client, auth_headers, ids, changed)
    assert _review(client, auth_headers, ids)["document"]["test_cases"]["total"] == 0
    listed = client.get(_url(ids, "lead_id", "calculation-config/test-cases"), headers=auth_headers).json()
    assert listed == []
    old = client.get(
        _url(ids, "lead_id", "calculation-config/test-cases") + "?version=1", headers=auth_headers
    ).json()
    assert [row["name"] for row in old] == ["case"]


def test_test_case_inputs_are_checked(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    assert _add_case(client, auth_headers, ids, source=None).json()["detail"]["code"] == "expected_source_required"
    assert _add_case(client, auth_headers, ids, source="made_up").json()["detail"]["code"] == "expected_source_required"
    bad = [
        ({"name": "", "inputs": {}, "expected": {}}, "test_case_invalid"),
        ({"name": " padded", "inputs": {}, "expected": {}}, "test_case_invalid"),
        ({"name": "n", "inputs": [], "expected": {}}, "test_case_invalid"),
        ({"name": "n", "inputs": {"a": 0.5}, "expected": {}}, "test_case_number_invalid"),
        ({"name": "n", "inputs": {}, "expected": {"a": [1.5]}}, "test_case_number_invalid"),
        ({"name": "n", "inputs": {}, "expected": {}, "extra": 1}, "unknown_field"),
    ]
    for body, code in bad:
        r = client.post(
            _url(ids, "lead_id", "calculation-config/test-cases"),
            headers=auth_headers,
            json={"expected_source": "independent", **body},
        )
        assert r.status_code == 400 and _code(r) == code, (body, r.text)
    assert _add_case(client, auth_headers, ids, "dup").status_code == 201
    assert _code(_add_case(client, auth_headers, ids, "DUP")) == "test_case_name_exists"
    assert _counts(db_session)["calculation_test_cases"] == 1


def test_a_test_case_needs_the_config_permission_and_a_draft(
    client, auth_headers, plain_headers, analysis_and_analyte
):
    ids = analysis_and_analyte
    assert _add_case(client, auth_headers, ids).status_code == 400, "no configuration yet"
    _save(client, auth_headers, ids)
    assert _add_case(client, plain_headers, ids).status_code == 403
    token = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, token).status_code == 200
    r = _add_case(client, auth_headers, ids, "late")
    assert r.status_code == 400 and _code(r) == "calculation_config_active"


# ---- the diff on a second version (CALC-REQ-45 item 6) ------------------------


def _snapshot(db_session, ids, analyte="lead_id", version=2) -> None:
    """What the 0124 trigger would have written at commit (absent in create_all)."""
    from models.calculation import AnalysisVersion

    rule = _row(db_session, ids, analyte)
    db_session.add(
        AnalysisVersion(
            analysis_id=UUID(ids["analysis_id"]),
            version=version,
            snapshot={
                "analysis": {"id": ids["analysis_id"]},
                "analytes": [
                    {
                        "analyte_id": ids[analyte],
                        "calculation_order": rule.calculation_order,
                        "calculation_config_name": rule.calculation_config_name,
                        "calculation_config_version": rule.calculation_config_version,
                        "calculation_config": rule.calculation_config,
                        "calculation_config_state": rule.calculation_config_state,
                    }
                ],
            },
        )
    )
    db_session.commit()


def test_a_second_version_shows_each_changed_binding_declaration_and_formula_text(
    client, auth_headers, analysis_and_analyte, db_session
):
    ids = analysis_and_analyte
    first = config(
        stage_copy("copy"),
        ad_hoc("calc", "ROUND(od - blank, 3)"),
        result={"stage": "calc", "output": "result"},
        name="cfg",
    )
    _save(client, auth_headers, ids, first)
    _snapshot(db_session, ids, version=2)

    second = config(
        stage_copy("copy", outcome="flag", flag="odd", precedence_place=4),
        ad_hoc("calc", "ROUND(od - blank, 4)"),
        result={"stage": "calc", "output": "result"},
        name="cfg",
    )
    second["stages"][0]["bindings"]["value"] = field("OD 620")
    saved = _save(client, auth_headers, ids, second)
    assert saved["version"] == 2

    diff = _review(client, auth_headers, ids)["document"]["diff"]
    assert diff["previous_version"] == 1 and diff["summary"].endswith("from version 1")
    by_category: Dict[str, list] = {}
    for change in diff["changes"]:
        by_category.setdefault(change["category"], []).append(change)

    binding = by_category["binding"][0]
    assert binding["stage"] == "copy" and "OD 450" in binding["old"] and "OD 620" in binding["new"]
    on_fail = {c["field"]: (c["old"], c["new"]) for c in by_category["on_fail"]}
    assert on_fail["outcome"] == ("run_failed", "flag")
    assert on_fail["flag"] == (None, "odd") and on_fail["precedence_place"] == ("1", "4")
    formula = by_category["formula_text"]
    assert len(formula) == 1, "a diff that omits the formula text fails"
    assert formula[0]["old"] == "ad hoc formula version 1: ROUND(od - blank, 3)"
    assert formula[0]["new"] == "ad hoc formula version 2: ROUND(od - blank, 4)"


def test_a_changed_saved_formula_version_shows_both_texts(client, auth_headers, analysis_and_analyte, db_session):
    ids = analysis_and_analyte
    for text_ in ("od - 1", "od - 2"):
        r = client.post(
            "/v1/calculation-formulas",
            headers=auth_headers,
            json={"name": "blank_correct", "formula_text": text_},
        )
        assert r.status_code == 201, r.text

    def stage(version: int) -> Dict[str, Any]:
        return {
            "id": "calc",
            "kind": "saved_formula",
            "formula_name": "blank_correct",
            "formula_version": version,
            "bindings": {"od": field("OD 450")},
            "on_fail": {"outcome": "run_failed", "flag": None, "gates": [], "precedence_place": 1},
        }

    pointer = {"stage": "calc", "output": "result"}
    _save(client, auth_headers, ids, config(stage(1), result=pointer, name="cfg"))
    _snapshot(db_session, ids, version=2)
    _save(client, auth_headers, ids, config(stage(2), result=pointer, name="cfg"))
    document = _review(client, auth_headers, ids)["document"]
    formula = [c for c in document["diff"]["changes"] if c["category"] == "formula_text"]
    assert [(c["old"], c["new"]) for c in formula] == [
        ("saved formula blank_correct version 1: od - 1", "saved formula blank_correct version 2: od - 2")
    ]
    assert document["formulas"] == [
        {"stage": "calc", "kind": "saved_formula", "name": "blank_correct", "version": 2, "text": "od - 2"}
    ]


def test_a_version_missing_from_the_history_is_said_so(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(stage_copy(), name="cfg"))
    changed = config(stage_copy(), name="cfg")
    changed["stages"][0]["bindings"]["value"] = field("OD 620")
    _save(client, auth_headers, ids, changed)
    diff = _review(client, auth_headers, ids)["document"]["diff"]
    assert diff["previous_version"] == 1 and diff["changes"] == []
    assert "not in the analysis version history" in diff["summary"]


def test_the_review_lists_formula_text_for_a_first_version(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids, config(ad_hoc("calc"), result={"stage": "calc", "output": "result"}))
    document = _review(client, auth_headers, ids)["document"]
    assert document["formulas"] == [
        {"stage": "calc", "kind": "ad_hoc_formula", "name": None, "version": 1, "text": "ROUND(od - blank, 3)"}
    ]
    assert "ROUND(od - blank, 3)" not in json.dumps(document["plain_language"]), "the text is listed once, under formulas"
    assert document["function_versions"] == []


# ---- the configuring agent: it proposes, it never activates -------------------


def _agent(db_session, user, method, path, body):
    from app.services.configuring_agent_apply import execute_step

    return execute_step(db_session, user, method, path, body)


def test_the_agent_proposes_an_inactive_draft_through_the_builder(
    client, auth_headers, analysis_and_analyte, db_session, test_admin_user
):
    ids = analysis_and_analyte
    changes = _agent(
        db_session,
        test_admin_user,
        "PUT",
        f"/v1/analyses/{ids['analysis_id']}/analytes/{ids['lead_id']}/calculation-config",
        _body(config(stage_copy(), name="agent proposal"), 1),
    )
    assert changes[0].kind == "calculation_config" and changes[0].name == "agent proposal"
    row = _row(db_session, ids)
    assert row.calculation_config_state == "draft" and row.calculation_config_version == 1


def test_the_agent_resolves_an_analysis_and_analyte_by_name(
    client, auth_headers, db_session, analysis_and_analyte, test_admin_user
):
    from models.analysis import Analysis

    ids = analysis_and_analyte
    analysis = db_session.get(Analysis, UUID(ids["analysis_id"]))
    changes = _agent(
        db_session,
        test_admin_user,
        "PUT",
        f"/v1/analyses/{analysis.name}/analytes/{ids['lead_name']}/calculation-config",
        _body(config(stage_copy(), name="by name"), 1),
    )
    assert changes[0].name == "by name"
    assert _row(db_session, ids).calculation_config_name == "by name"


def test_the_agent_cannot_add_a_function_to_the_catalog(
    db_session, analysis_and_analyte, test_admin_user
):
    from fastapi import HTTPException

    ids = analysis_and_analyte
    stage = stage_copy()
    stage["function"] = "elisa_4pl"
    with pytest.raises(HTTPException) as refused:
        _agent(
            db_session,
            test_admin_user,
            "PUT",
            f"/v1/analyses/{ids['analysis_id']}/analytes/{ids['lead_id']}/calculation-config",
            _body(config(stage, name="invented"), 1),
        )
    assert refused.value.detail["code"] == "catalog_function_unknown"
    assert _row(db_session, ids).calculation_config is None


def test_the_agent_cannot_reach_an_activation_route(db_session, analysis_and_analyte, test_admin_user):
    from app.services.configuring_agent_allow import ACTIVATION_GAP
    from app.services.configuring_agent_apply import CannotExpress

    ids = analysis_and_analyte
    base = f"/v1/analyses/{ids['analysis_id']}/analytes/{ids['lead_id']}/calculation-config"
    for method, suffix in (
        ("POST", "/activate"),
        ("POST", "/activation-token"),
        ("GET", "/activation-review"),
    ):
        with pytest.raises(CannotExpress) as stopped:
            _agent(db_session, test_admin_user, method, base + suffix, {"confirm_token": "x"})
        assert stopped.value.gap == ACTIVATION_GAP


def test_the_agent_needs_the_confirming_users_config_permission(
    db_session, analysis_and_analyte, test_user
):
    from app.services.configuring_agent_apply import PermissionDenied

    ids = analysis_and_analyte
    with pytest.raises(PermissionDenied):
        _agent(
            db_session,
            test_user,
            "PUT",
            f"/v1/analyses/{ids['analysis_id']}/analytes/{ids['lead_id']}/calculation-config",
            _body(config(stage_copy(), name="no permission"), 1),
        )


def test_an_agent_context_cannot_review_get_a_token_or_activate_even_for_the_same_admin(
    client, auth_headers, analysis_and_analyte, db_session, test_admin_user
):
    from fastapi import HTTPException

    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    shown = _review(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    analysis_id, analyte_id = UUID(ids["analysis_id"]), UUID(ids["lead_id"])
    calls = (
        lambda: activation.read_review(db_session, test_admin_user, analysis_id, analyte_id),
        lambda: activation.export_review(db_session, test_admin_user, analysis_id, analyte_id),
        lambda: activation.issue_token(
            db_session, test_admin_user, "jti", analysis_id, analyte_id, {"review_hash": shown["review_hash"]}
        ),
        lambda: activation.activate(
            db_session, test_admin_user, "jti", analysis_id, analyte_id, {"confirm_token": token}
        ),
    )
    with agent_run_context():
        for call in calls:
            with pytest.raises(HTTPException) as refused:
                call()
            assert refused.value.status_code == 403
            assert refused.value.detail["code"] == "agent_context_refused"
    assert _row(db_session, ids).calculation_config_state == "draft"
    assert db_session.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar() is None
    assert _counts(db_session)["calculation_confirm_tokens"] == 1, "no token was issued to the agent"
    assert _activate(client, auth_headers, ids, token).status_code == 200, "the person's own token still works"


def test_an_agent_replay_of_a_spent_token_is_refused(client, auth_headers, analysis_and_analyte, db_session, test_admin_user):
    from fastapi import HTTPException

    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    token = _issue(client, auth_headers, ids)
    assert _activate(client, auth_headers, ids, token).status_code == 200
    client.post(f"/v1/analyses/{ids['analysis_id']}/new-version", headers=auth_headers)
    with agent_run_context():
        with pytest.raises(HTTPException) as refused:
            activation.activate(
                db_session,
                test_admin_user,
                "jti",
                UUID(ids["analysis_id"]),
                UUID(ids["lead_id"]),
                {"confirm_token": token},
            )
    assert refused.value.detail["code"] == "agent_context_refused"
    assert _row(db_session, ids).calculation_config_state == "draft"


def test_the_agents_test_case_is_flagged_as_system_output(
    client, auth_headers, analysis_and_analyte, db_session, test_admin_user
):
    from fastapi import HTTPException

    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    path = f"/v1/analyses/{ids['analysis_id']}/analytes/{ids['lead_id']}/calculation-config/test-cases"
    changes = _agent(
        db_session,
        test_admin_user,
        "POST",
        path,
        {"name": "agent case", "inputs": {"OD 450": "0.5"}, "expected": {"calculated": "0.5"}},
    )
    assert changes[0].kind == "calculation_test_case"
    with pytest.raises(HTTPException) as claimed:
        _agent(
            db_session,
            test_admin_user,
            "POST",
            path,
            {
                "name": "agent claims",
                "inputs": {},
                "expected": {},
                "expected_source": "independent",
            },
        )
    assert claimed.value.detail["code"] == "agent_expected_source"
    cases = client.get(_url(ids, "lead_id", "calculation-config/test-cases"), headers=auth_headers).json()
    assert [(c["name"], c["expected_source"], c["from_system_output"]) for c in cases] == [
        ("agent case", "system_output", True)
    ]
    document = _review(client, auth_headers, ids)["document"]
    assert document["test_cases"]["from_system_output"] == 1
    assert "1 from system output" in document["test_cases"]["summary"]


def test_a_person_can_say_a_system_output_case_is_system_output(client, auth_headers, analysis_and_analyte):
    ids = analysis_and_analyte
    _save(client, auth_headers, ids)
    case = _add_case(client, auth_headers, ids, "from the screen", "system_output").json()
    assert case["expected_source"] == "system_output" and case["from_system_output"] is True
    assert case["passed_on_current_lock"] is None
