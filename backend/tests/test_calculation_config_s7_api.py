"""Calculations S7: configuration, saved formulas, and versions through the API.

Runs on the ``create_all`` schema, so the database triggers of 0124 are not
present here; the routes' own refusals are what these tests check. The triggers,
the version counter, and the snapshots are in
``test_calculation_config_s7_db.py``.
"""
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from tests.test_calculation_config_s7 import (
    ABOVE_LIST,
    ad_hoc,
    config,
    declare,
    field,
    stage_copy,
    stage_cv,
    stage_limit,
)
from tests.test_result_promotion import (  # noqa: F401  (fixtures)
    analysis_and_analyte,
    auth_headers,
)


def _url(ids: Dict[str, str], analyte: str = "lead_id", suffix: str = "calculation-config") -> str:
    return f"/v1/analyses/{ids['analysis_id']}/analytes/{ids[analyte]}/{suffix}"


def _body(configuration: Dict[str, Any], order: int = 1) -> Dict[str, Any]:
    return {"calculation_order": order, "configuration": configuration}


@pytest.fixture
def manager_headers(client: TestClient, db_session, test_org):
    """A user with config:edit who is not an Administrator."""
    from app.core.security import get_password_hash
    from models.user import Permission, Role, User
    from tests.conftest import _get_or_create, _grant

    role = _get_or_create(db_session, Role, "Lab Manager", "Lab Manager")
    perm = _get_or_create(db_session, Permission, "config:edit", "Edit configuration")
    _grant(db_session, role, [perm])
    user = User(
        name="Manager",
        username="s7-manager",
        email="s7-manager@example.com",
        password_hash=get_password_hash("managerpassword"),
        role_id=role.id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    r = client.post("/auth/login", json={"username": "s7-manager", "password": "managerpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def plain_headers(client: TestClient, test_user):
    r = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _row(db_session, ids: Dict[str, str], analyte: str = "lead_id"):
    from models.analysis import AnalysisAnalyte

    db_session.expire_all()
    return (
        db_session.query(AnalysisAnalyte)
        .filter_by(analysis_id=UUID(ids["analysis_id"]), analyte_id=UUID(ids[analyte]))
        .one()
    )


def _code(response) -> str:
    return response.json()["detail"]["code"]


# ---- the catalog is read-only and there is no constants or run-R route -------


def test_the_catalog_is_readable_and_has_eleven_entries(client: TestClient, auth_headers) -> None:
    r = client.get("/v1/calculation-catalog", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) == 11
    assert {e["name"] for e in entries} >= {"fit_4pl", "limit_compare", "copy_raw"}
    fit = next(e for e in entries if e["name"] == "fit_4pl")
    assert fit["failure_stops"] == ["curve_not_fitted", "r_non_finite", "r_timeout"]
    assert "concentration" in fit["required_inputs"]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_a_write_to_the_catalog_is_405_and_the_catalog_is_unchanged(
    client: TestClient, auth_headers, method: str
) -> None:
    body = {"name": "elisa_4pl", "version": 1}
    r = getattr(client, method)("/v1/calculation-catalog", headers=auth_headers, json=body) if method != "delete" else client.delete(
        "/v1/calculation-catalog", headers=auth_headers
    )
    assert r.status_code == 405
    r = getattr(client, method)("/v1/calculation-catalog/elisa_4pl", headers=auth_headers) if method != "post" else client.post(
        "/v1/calculation-catalog/elisa_4pl", headers=auth_headers, json=body
    )
    assert r.status_code in (404, 405)
    assert len(client.get("/v1/calculation-catalog", headers=auth_headers).json()) == 11


def test_the_catalog_needs_a_login(client: TestClient) -> None:
    assert client.get("/v1/calculation-catalog").status_code in (401, 403)


def test_no_route_serves_constants_or_runs_r(client: TestClient) -> None:
    from app.main import app

    paths = [getattr(route, "path", "") for route in app.routes]
    s7 = [p for p in paths if "calculation" in p]
    assert s7, "the S7 routes are mounted"
    for path in paths:
        assert "constant" not in path.lower(), path
        assert not any(word in path.lower() for word in ("run-r", "run_r", "rscript")), path
    for path in s7:
        assert "execute" not in path.lower(), path


# ---- saving a configuration ---------------------------------------------------


def test_admin_saves_a_draft_configuration_and_reads_it_back(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    cfg = config(stage_cv(), stage_copy("copy2"), name="Lead mean")
    r = client.put(_url(ids), headers=auth_headers, json=_body(cfg, order=2))
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["state"] == "draft" and saved["version"] == 1 and saved["calculation_order"] == 2
    assert saved["name"] == "Lead mean" and saved["analysis_version"] >= 1
    assert saved["configuration"]["stages"][0]["function"] == "replicate_mean_cv"

    got = client.get(_url(ids), headers=auth_headers)
    assert got.status_code == 200 and got.json()["configuration"] == saved["configuration"]

    row = _row(db_session, ids)
    assert row.calculation_config_name == "Lead mean" and row.calculation_order == 2
    assert row.calculation_config_state == "draft"


def test_the_free_text_calculation_column_is_not_the_configuration(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    r = client.patch(
        f"/analyses/{ids['analysis_id']}/analyte-rules/{ids['lead_id']}",
        headers=auth_headers,
        json={"calculation": "x * 2"},
    )
    assert r.status_code == 200, r.text
    assert client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy()))).status_code == 200
    row = _row(db_session, ids)
    assert row.calculation == "x * 2"
    assert "x * 2" not in str(row.calculation_config)


def test_saving_the_same_content_again_changes_nothing(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    body = _body(config(stage_copy()))
    first = client.put(_url(ids), headers=auth_headers, json=body).json()
    again = client.put(_url(ids), headers=auth_headers, json=body).json()
    assert again["version"] == first["version"] == 1
    body["configuration"]["stages"][0]["bindings"]["value"]["field_name"] = "OD 600"
    changed = client.put(_url(ids), headers=auth_headers, json=body).json()
    assert changed["version"] == 2


def test_a_missing_declaration_is_refused_with_the_stage_named(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    stage = stage_copy("needs_decl")
    del stage["on_fail"]
    r = client.put(_url(ids), headers=auth_headers, json=_body(config(stage)))
    assert r.status_code == 400
    assert r.json()["detail"] == {
        "code": "on_fail_declaration_missing",
        "message": r.json()["detail"]["message"],
        "stage": "needs_decl",
    }
    assert _row(db_session, ids).calculation_config is None


def test_refusals_are_400_and_write_nothing(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    cases = [
        (config(stage_copy(outcome="pass")), "on_fail_pass_refused"),
        (config(stage_copy("a", outcome="flag", flag="one", precedence_place=1),
                stage_copy("b", outcome="flag", flag="two", precedence_place=1)), "precedence_place_conflict"),
        (config(stage_limit(limit={"kind": "direct", "value": 5}), result={"stage": "limit", "output": "verdict"}), "direct_value_invalid"),
        (config(ad_hoc(text="SUM(A1:A3)", od=field("x")), result={"stage": "calc", "output": "result"}), "formula_range_not_supported"),
    ]
    fit = {
        "id": "fit", "kind": "catalog_function", "function": "fit_4pl", "function_version": 1,
        "bindings": {"concentration": field("Dose"), "response": field("OD")},
        "on_fail": declare(outcome="run_failed"),
    }
    cases.append((config(fit), "on_fail_stage_stop_required"))
    unknown = config(stage_copy())
    unknown["stages"][0]["function"] = "elisa_4pl"
    cases.append((unknown, "catalog_function_unknown"))
    for configuration, code in cases:
        r = client.put(_url(ids), headers=auth_headers, json=_body(configuration))
        assert r.status_code == 400, (code, r.text)
        assert _code(r) == code
        assert _row(db_session, ids).calculation_config is None


def test_a_direct_binding_saves_and_a_stop_is_not_a_refusal(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    cfg = config(
        stage_cv(),
        stage_limit(value={"kind": "stage_output", "stage": "cv", "output": "mean"}, limit={"kind": "direct", "value": "5.00"}),
        result={"stage": "limit", "output": "verdict"},
    )
    r = client.put(_url(ids), headers=auth_headers, json=_body(cfg))
    assert r.status_code == 200, r.text
    assert r.json()["configuration"]["stages"][1]["bindings"]["limit"] == {"kind": "direct", "value": "5.00"}


def test_unknown_json_fields_are_refused(client: TestClient, auth_headers, analysis_and_analyte) -> None:
    ids = analysis_and_analyte
    body = _body(config(stage_copy()))
    body["extra"] = 1
    r = client.put(_url(ids), headers=auth_headers, json=body)
    assert r.status_code == 400 and _code(r) == "unknown_field"
    body = _body(config(stage_copy()))
    body["configuration"]["constants"] = {"a": "1"}
    r = client.put(_url(ids), headers=auth_headers, json=body)
    assert r.status_code == 400 and _code(r) == "unknown_field"
    r = client.patch(_url(ids, suffix="calculation-order"), headers=auth_headers, json={"calculation_order": 1, "x": 1})
    assert r.status_code == 400 and _code(r) == "unknown_field"


def test_calculation_order_is_required_positive_and_unique(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    r = client.put(_url(ids), headers=auth_headers, json={"configuration": config(stage_copy())})
    assert r.status_code == 400 and _code(r) == "calculation_order_required"
    for bad in (0, -1, 1.5, "1", True, None):
        r = client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy()), order=bad))
        assert r.status_code == 400 and _code(r) == "calculation_order_invalid", bad
    assert client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy(), name="a"), order=1)).status_code == 200
    r = client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(config(stage_copy(), name="b"), order=1))
    assert r.status_code == 400 and _code(r) == "calculation_order_duplicate"
    assert client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(config(stage_copy(), name="b"), order=2)).status_code == 200


def test_display_order_and_calculation_order_are_separate(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    assert client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy()), order=7)).status_code == 200
    r = client.patch(
        f"/analyses/{ids['analysis_id']}/analyte-rules/{ids['lead_id']}",
        headers=auth_headers,
        json={"display_order": 3},
    )
    assert r.status_code == 200
    rules = client.get(f"/analyses/{ids['analysis_id']}/analyte-rules", headers=auth_headers).json()
    lead = next(rule for rule in rules if rule["analyte_id"] == ids["lead_id"])
    assert lead["display_order"] == 3 and lead["calculation_order"] == 7
    assert lead["calculation_config_state"] == "draft" and lead["calculation_config_version"] == 1
    arsenic = next(rule for rule in rules if rule["analyte_id"] == ids["arsenic_id"])
    assert arsenic["calculation_order"] is None and arsenic["calculation_config_name"] is None


def test_a_later_analyte_reads_an_earlier_analytes_value_and_order_is_enforced(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    earlier = config(stage_copy(), name="first")
    assert client.put(_url(ids), headers=auth_headers, json=_body(earlier, order=1)).status_code == 200

    reader_stage = stage_copy()
    reader_stage["bindings"]["value"] = {"kind": "reference", "analyte_id": ids["lead_id"], "value": "calculated"}
    reader = config(reader_stage, name="second")
    ok = client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(reader, order=2))
    assert ok.status_code == 200, ok.text

    same = client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(reader, order=1))
    assert same.status_code == 400 and _code(same) in ("calculation_order_duplicate", "calculation_order_violation")
    sooner = client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(config(reader_stage, name="second"), order=1))
    assert sooner.status_code == 400

    moved = client.patch(_url(ids, suffix="calculation-order"), headers=auth_headers, json={"calculation_order": 3})
    assert moved.status_code == 400 and _code(moved) == "calculation_order_violation"
    moved = client.patch(_url(ids, "arsenic_id", "calculation-order"), headers=auth_headers, json={"calculation_order": 1})
    assert moved.status_code == 400

    gone = client.delete(_url(ids), headers=auth_headers)
    assert gone.status_code == 400 and _code(gone) == "configuration_in_use"

    forward = stage_copy()
    forward["bindings"]["value"] = {"kind": "reference", "analyte_id": ids["arsenic_id"], "value": "calculated"}
    r = client.put(_url(ids), headers=auth_headers, json=_body(config(forward, name="first"), order=1))
    assert r.status_code == 400 and _code(r) == "calculation_order_violation"


def test_patch_order_and_delete_a_draft(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    assert client.patch(_url(ids, suffix="calculation-order"), headers=auth_headers, json={"calculation_order": 4}).status_code == 400
    client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy()), order=1))
    r = client.patch(_url(ids, suffix="calculation-order"), headers=auth_headers, json={"calculation_order": 4})
    assert r.status_code == 200 and r.json()["calculation_order"] == 4 and r.json()["version"] == 2
    assert client.delete(_url(ids), headers=auth_headers).status_code == 204
    row = _row(db_session, ids)
    assert row.calculation_config is None and row.calculation_order is None
    assert client.get(_url(ids), headers=auth_headers).json()["configuration"] is None
    assert client.delete(_url(ids), headers=auth_headers).status_code == 404


def test_a_configuration_name_is_unique_in_the_analysis(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    assert client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy(), name="Same Name"), order=1)).status_code == 200
    r = client.put(_url(ids, "arsenic_id"), headers=auth_headers, json=_body(config(stage_copy(), name="same name"), order=2))
    assert r.status_code == 400 and _code(r) == "calculation_config_name_exists"


def test_the_analyte_must_be_in_the_analysis_and_the_analysis_must_exist(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    body = _body(config(stage_copy()))
    assert client.put(f"/v1/analyses/{ids['analysis_id']}/analytes/{uuid4()}/calculation-config", headers=auth_headers, json=body).status_code == 404
    assert client.put(f"/v1/analyses/{uuid4()}/analytes/{ids['lead_id']}/calculation-config", headers=auth_headers, json=body).status_code == 404


# ---- who may do what ---------------------------------------------------------


def test_a_caller_without_a_config_permission_cannot_save(
    client: TestClient, plain_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    r = client.put(_url(ids), headers=plain_headers, json=_body(config(stage_copy())))
    assert r.status_code == 403
    assert client.post(f"/v1/analyses/{ids['analysis_id']}/new-version", headers=plain_headers).status_code == 403


def test_only_an_admin_writes_a_formula_in_a_configuration(
    client: TestClient, auth_headers, manager_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    formula_cfg = config(stage_copy(), ad_hoc(), name="with formula")
    r = client.put(_url(ids), headers=manager_headers, json=_body(formula_cfg))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "formula_admin_only" and r.json()["detail"]["stage"] == "calc"

    catalog_only = config(stage_copy(), name="catalog only")
    assert client.put(_url(ids), headers=manager_headers, json=_body(catalog_only)).status_code == 200

    assert client.put(_url(ids), headers=auth_headers, json=_body(formula_cfg)).status_code == 200

    edited = config(stage_copy(), ad_hoc(), name="with formula")
    edited["stages"][0]["bindings"]["value"]["field_name"] = "OD 600"
    r = client.put(_url(ids), headers=manager_headers, json=_body(edited))
    assert r.status_code == 200, r.text

    edited["stages"][1]["formula_text"] = "od + blank"
    r = client.put(_url(ids), headers=manager_headers, json=_body(edited))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "formula_admin_only"

    edited = config(stage_copy(), name="with formula")
    assert client.put(_url(ids), headers=manager_headers, json=_body(edited)).status_code == 200


def test_the_ad_hoc_formula_version_counts_edits_by_an_admin(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    cfg = config(stage_copy(), ad_hoc(), name="v")
    first = client.put(_url(ids), headers=auth_headers, json=_body(cfg)).json()
    assert first["configuration"]["stages"][1]["formula_version"] == 1
    cfg["stages"][1]["formula_text"] = "ROUND(od - blank, 4)"
    second = client.put(_url(ids), headers=auth_headers, json=_body(cfg)).json()
    assert second["configuration"]["stages"][1]["formula_version"] == 2
    assert second["version"] == 2


# ---- active is immutable (CALC-REQ-40) ---------------------------------------


def _make_active(db_session, ids: Dict[str, str], analyte: str = "lead_id") -> None:
    row = _row(db_session, ids, analyte)
    row.calculation_config_state = "active"
    db_session.commit()


def test_an_active_configuration_is_refused_in_place_and_nothing_changes(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    cfg = config(stage_copy(), ad_hoc(), name="live")
    assert client.put(_url(ids), headers=auth_headers, json=_body(cfg)).status_code == 200
    _make_active(db_session, ids)
    before = _row(db_session, ids).calculation_config

    attempts = []
    for mutate in (
        lambda c: c["stages"][1].__setitem__("formula_text", "od + blank"),
        lambda c: c["stages"][0]["bindings"]["value"].__setitem__("field_name", "OD 600"),
        lambda c: c["stages"][0]["on_fail"].__setitem__("flag", "another_flag"),
    ):
        changed = config(stage_copy(), ad_hoc(), name="live")
        mutate(changed)
        attempts.append(changed)
    for changed in attempts:
        r = client.put(_url(ids), headers=auth_headers, json=_body(changed))
        assert r.status_code == 400 and _code(r) == "calculation_config_active", r.text
    r = client.patch(_url(ids, suffix="calculation-order"), headers=auth_headers, json={"calculation_order": 9})
    assert r.status_code == 400 and _code(r) == "calculation_config_active"
    r = client.delete(_url(ids), headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "calculation_config_active"
    assert _row(db_session, ids).calculation_config == before
    assert _row(db_session, ids).calculation_config_state == "active"


def test_changing_only_the_flag_a_stage_sets_is_refused_in_place_and_succeeds_as_a_new_version(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    base = lambda flag: config(  # noqa: E731
        stage_cv(),
        stage_limit(
            value={"kind": "stage_output", "stage": "cv", "output": "mean"},
            flag=flag,
        ),
        result={"stage": "limit", "output": "verdict"},
        name="flags",
    )
    assert client.put(_url(ids), headers=auth_headers, json=_body(base("above_limit"))).status_code == 200
    _make_active(db_session, ids)
    r = client.put(_url(ids), headers=auth_headers, json=_body(base("over_limit")))
    assert r.status_code == 400 and _code(r) == "calculation_config_active"

    nv = client.post(f"/v1/analyses/{ids['analysis_id']}/new-version", headers=auth_headers)
    assert nv.status_code == 200, nv.text
    assert nv.json()["drafted_analyte_ids"] == [ids["lead_id"]]
    assert _row(db_session, ids).calculation_config_state == "draft"

    r = client.put(_url(ids), headers=auth_headers, json=_body(base("over_limit")))
    assert r.status_code == 200, r.text
    assert r.json()["configuration"]["stages"][1]["on_fail"]["flag"] == "over_limit"
    assert r.json()["version"] == 2


def test_new_version_needs_an_active_configuration(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    r = client.post(f"/v1/analyses/{ids['analysis_id']}/new-version", headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "no_active_configuration"
    assert client.post(f"/v1/analyses/{uuid4()}/new-version", headers=auth_headers).status_code == 404


def test_the_analyte_routes_refuse_to_drop_an_active_configuration(
    client: TestClient, auth_headers, analysis_and_analyte, db_session
) -> None:
    ids = analysis_and_analyte
    client.put(_url(ids), headers=auth_headers, json=_body(config(stage_copy())))
    _make_active(db_session, ids)
    aid = ids["analysis_id"]
    r = client.delete(f"/analyses/{aid}/analyte-rules/{ids['lead_id']}", headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "calculation_config_active"
    r = client.delete(f"/analyses/{aid}/analytes/{ids['lead_id']}", headers=auth_headers)
    assert r.status_code == 400 and _code(r) == "calculation_config_active"
    r = client.put(f"/analyses/{aid}/analytes", headers=auth_headers, json={"analyte_ids": [ids["arsenic_id"]]})
    assert r.status_code == 400 and _code(r) == "calculation_config_active"
    r = client.put(f"/analyses/{aid}/analytes", headers=auth_headers, json={"analyte_ids": [ids["arsenic_id"], ids["lead_id"]]})
    assert r.status_code == 200
    # Other edits to the analyte rule stay possible: they are not the calculation.
    r = client.patch(f"/analyses/{aid}/analyte-rules/{ids['lead_id']}", headers=auth_headers, json={"display_order": 2})
    assert r.status_code == 200
    assert _row(db_session, ids).calculation_config_state == "active"


def test_the_analysis_response_carries_its_version(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    r = client.get(f"/analyses/{ids['analysis_id']}", headers=auth_headers)
    assert r.status_code == 200 and isinstance(r.json()["version"], int) and r.json()["version"] >= 1


# ---- saved formulas ------------------------------------------------------------


def test_admin_saves_a_formula_as_version_1_then_2_and_old_versions_stay(
    client: TestClient, auth_headers
) -> None:
    name = f"Blank Correct {uuid4().hex[:6]}"
    one = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": name, "formula_text": "od - blank"})
    assert one.status_code == 201, one.text
    assert one.json()["version"] == 1 and one.json()["terms"] == ["blank", "od"]
    same = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": name.lower(), "formula_text": "od - blank"})
    assert same.status_code == 400 and _code(same) == "formula_unchanged"
    two = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": name.lower(), "formula_text": "ROUND(od - blank, 3)"})
    assert two.status_code == 201 and two.json()["version"] == 2 and two.json()["name"] == name
    old = client.get(f"/v1/calculation-formulas/{name}/versions/1", headers=auth_headers)
    assert old.status_code == 200 and old.json()["formula_text"] == "od - blank"
    assert client.get(f"/v1/calculation-formulas/{name}/versions/9", headers=auth_headers).status_code == 404
    listed = client.get("/v1/calculation-formulas", headers=auth_headers).json()
    assert [(f["version"]) for f in listed if f["name"] == name] == [1, 2]


def test_a_formula_outside_the_grammar_is_not_saved(client: TestClient, auth_headers) -> None:
    for text, code in (
        ("SUM(A1:A3)", "formula_range_not_supported"),
        ("FOO(1)", "formula_unknown_function"),
        ("", "formula_empty"),
        ("1+", "formula_syntax"),
    ):
        r = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": f"bad-{uuid4().hex[:6]}", "formula_text": text})
        assert r.status_code == 400 and _code(r) == code, text
    r = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": "x", "formula_text": "1", "unit": "mg"})
    assert r.status_code == 400 and _code(r) == "unknown_field"
    r = client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": "", "formula_text": "1"})
    assert r.status_code == 400 and _code(r) == "formula_name_invalid"


def test_only_an_admin_saves_or_tries_a_formula(
    client: TestClient, manager_headers, plain_headers
) -> None:
    for headers in (manager_headers, plain_headers):
        r = client.post("/v1/calculation-formulas", headers=headers, json={"name": "x", "formula_text": "1"})
        assert r.status_code == 403
        r = client.post("/v1/calculation-formulas/evaluate", headers=headers, json={"formula_text": "1"})
        assert r.status_code == 403


def test_a_saved_formula_is_pinned_by_a_configuration(
    client: TestClient, auth_headers, analysis_and_analyte
) -> None:
    ids = analysis_and_analyte
    name = f"Pinned {uuid4().hex[:6]}"
    client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": name, "formula_text": "od - blank"})
    stage = {
        "id": "calc", "kind": "saved_formula", "formula_name": name, "formula_version": 1,
        "bindings": {"od": field("OD 450"), "blank": {"kind": "direct", "value": "0.05"}},
        "on_fail": declare(),
    }
    r = client.put(_url(ids), headers=auth_headers, json=_body(config(stage, result={"stage": "calc", "output": "result"})))
    assert r.status_code == 200, r.text
    assert r.json()["configuration"]["stages"][0]["formula_version"] == 1
    client.post("/v1/calculation-formulas", headers=auth_headers, json={"name": name, "formula_text": "od + blank"})
    assert client.get(_url(ids), headers=auth_headers).json()["configuration"]["stages"][0]["formula_version"] == 1
    stage["formula_version"] = 5
    r = client.put(_url(ids), headers=auth_headers, json=_body(config(stage, result={"stage": "calc", "output": "result"})))
    assert r.status_code == 400 and _code(r) == "saved_formula_unknown"


# ---- trying a formula (no attempt, no write) ----------------------------------


def _evaluate(client: TestClient, headers, text: str, terms: Dict[str, Any] | None = None):
    body: Dict[str, Any] = {"formula_text": text}
    if terms is not None:
        body["terms"] = terms
    return client.post("/v1/calculation-formulas/evaluate", headers=headers, json=body)


def test_evaluate_round_half_even_and_excel_errors_return_200(client: TestClient, auth_headers) -> None:
    assert _evaluate(client, auth_headers, "ROUND(2.5, 0)").json() == {"value": "2", "error": None, "detail": ""}
    assert _evaluate(client, auth_headers, "ROUND(3.5, 0)").json()["value"] == "4"
    r = _evaluate(client, auth_headers, "a/b", {"a": "1", "b": "0"})
    assert r.status_code == 200 and r.json()["error"] == "#DIV/0!" and r.json()["value"] is None
    r = _evaluate(client, auth_headers, "a+1", {"a": None})
    assert r.status_code == 200 and r.json()["error"] == "#N/A"
    r = _evaluate(client, auth_headers, "a+1", {"a": {"knocked_out": True}})
    assert r.status_code == 200 and r.json()["error"] == "#N/A"
    r = _evaluate(client, auth_headers, "a+1")
    assert r.status_code == 200 and r.json()["error"] == "#N/A"
    r = _evaluate(client, auth_headers, "SQRT(0-1)")
    assert r.json()["error"] == "#NUM!"
    r = _evaluate(client, auth_headers, "a+1", {"a": "abc"})
    assert r.json()["error"] == "#VALUE!"


def test_evaluate_refuses_what_is_not_a_formula_or_a_term(client: TestClient, auth_headers) -> None:
    r = _evaluate(client, auth_headers, "SUM(A1:A3)")
    assert r.status_code == 400 and _code(r) == "formula_range_not_supported"
    r = _evaluate(client, auth_headers, "a+1", {"zzz": "1"})
    assert r.status_code == 400 and _code(r) == "formula_unknown_name"
    r = _evaluate(client, auth_headers, "a+1", {"a": 5})
    assert r.status_code == 400 and _code(r) == "config_invalid"
    r = client.post("/v1/calculation-formulas/evaluate", headers=auth_headers, json={"formula_text": "1", "code": "1"})
    assert r.status_code == 400 and _code(r) == "unknown_field"


def test_evaluate_stdev_divides_by_n_minus_1_and_stdev_p_by_n(client: TestClient, auth_headers) -> None:
    terms = {"a": "2", "b": "4", "c": "4", "d": "4", "e": "5", "f": "5", "g": "7", "h": "9"}
    population = _evaluate(client, auth_headers, "STDEV.P(a,b,c,d,e,f,g,h)", terms).json()["value"]
    sample = _evaluate(client, auth_headers, "STDEV(a,b,c,d,e,f,g,h)", terms).json()["value"]
    assert population == "2"
    assert sample.startswith("2.13808993529939")


def test_evaluate_stores_nothing(client: TestClient, auth_headers, db_session) -> None:
    from models.calculation import CalculationFormula

    before = db_session.query(CalculationFormula).count()
    _evaluate(client, auth_headers, "1+1")
    assert db_session.query(CalculationFormula).count() == before


def test_versions_routes_require_the_analysis(client: TestClient, auth_headers) -> None:
    assert client.get(f"/v1/analyses/{uuid4()}/versions", headers=auth_headers).status_code == 404
    assert client.get(f"/v1/analyses/{uuid4()}/versions/1", headers=auth_headers).status_code == 404


def test_ABOVE_LIST_constant_is_the_one_the_tests_and_code_share() -> None:
    assert ABOVE_LIST == "above_list"
