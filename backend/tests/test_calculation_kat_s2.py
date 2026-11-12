"""S2 KAT harness and run log (CALC-REQ-5, CALC-REQ-6).

Uses harness fixtures only (``tests/fixtures/calculation_kat_harness.py``).
No catalog function exists yet, and no case here is a catalog KAT.

``test_r_side_harness_kats_on_the_pinned_image`` runs only when
``KAT_R_CALCULATOR_URL`` points at a running pinned image (CI job
``r-calculator-pin``). A host R process cannot pass it: every R call goes
through the CALC-REQ-4 / 4a lock and sandbox gate.
"""
from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.services.calculation_kat import (
    FunctionVersion,
    KatRunLog,
    Tolerance,
    run_kats,
    version_fingerprint,
)
from app.services.calculation_runtime import (
    CalculationCallRefused,
    expected_lock_from_commit,
    find_repo_root,
)
from app.services.r_calculator_client import RCalculatorClient
from tests.fixtures import calculation_kat_harness as hf

CATALOG_NAMES = {
    "fit_4pl",
    "inverse_4pl",
    "fit_loglog_linear",
    "inverse_loglog_linear",
    "replicate_mean_cv",
    "spike_recovery",
    "limit_compare",
    "apply_dilution",
    "convert_units",
    "subtract",
    "copy_raw",
}

DIGEST = "sha256:" + ("ab" * 32)


def _health(**overrides: Any) -> dict:
    lock = expected_lock_from_commit(find_repo_root())
    body = {
        "status": "ok",
        "base": lock.base,
        "renv": lock.renv,
        "tree": lock.tree,
        "lock_hash": lock.lock_hash,
        "R_IMAGE_DIGEST": DIGEST,
        "sandbox": {
            "uid": 1000,
            "root_read_only": True,
            "scratch_tmpfs": True,
            "egress_blocked": True,
            "cpu_limited": True,
            "memory_limited": True,
            "pids_limited": True,
            "forbidden_env_absent": True,
        },
    }
    body.update(overrides)
    return body


def test_run_log_names_lock_digest_and_every_case_field() -> None:
    log = run_kats([hf.backend_sum()], health=_health())
    assert log.lock_hash == expected_lock_from_commit(find_repo_root()).lock_hash
    assert log.image_digest == DIGEST
    assert len(log.cases) == 1
    case = log.cases[0]
    assert case.passed
    assert case.function == "harness_fixture_backend_sum"
    assert case.version == 1
    assert case.side == "backend"
    assert case.citation == hf.HARNESS_CITATION
    out = case.outputs[0]
    assert (out.observed, out.expected) == ("2.572", "2.572")
    assert out.tolerance == Tolerance("absolute", "0", "1")
    assert out.passed
    data = json.loads(log.to_json())
    row = data["cases"][0]
    for key in ("function", "version", "side", "citation", "result", "outputs"):
        assert key in row
    for key in ("observed", "expected", "tolerance", "result", "unit"):
        assert key in row["outputs"][0]
    assert data["lock_hash"] == log.lock_hash and data["image_digest"] == DIGEST
    assert KatRunLog.from_dict(data).to_dict() == data


def test_backend_kat_is_exact_in_decimal() -> None:
    # 0.1 + 0.2 is 0.3 in decimal at tolerance 0; in binary it is not.
    fv = hf.backend_sum(kats=(hf.sum_case(case_id="hf-sum-tenths", a="0.1", b="0.2", total="0.3"),))
    log = run_kats([fv], health=_health())
    assert log.cases[0].passed
    assert log.cases[0].outputs[0].observed == "0.3"


def test_failing_case_is_reported_failed_with_observed_and_expected() -> None:
    fv = hf.backend_sum(kats=(hf.sum_case(), hf.failing_sum_case()))
    log = run_kats([fv], health=_health())
    by_id = {c.case_id: c for c in log.cases}
    assert by_id["hf-sum-exact"].passed
    wrong = by_id["hf-sum-deliberately-wrong"]
    assert not wrong.passed
    assert wrong.outputs[0].observed == "2.572"
    assert wrong.outputs[0].expected == "2.573"
    assert json.loads(log.to_json())["cases"][1]["result"] == "fail"


def test_relative_and_absolute_tolerance() -> None:
    rel = hf.sum_case(
        case_id="hf-sum-rel",
        a="1",
        b="2",
        total="3.0000003",
        tolerance=Tolerance("relative", "0.0000001", "1"),
    )
    rel_out = hf.sum_case(
        case_id="hf-sum-rel-out",
        a="1",
        b="2",
        total="3.0000004",
        tolerance=Tolerance("relative", "0.0000001", "1"),
    )
    absolute = hf.sum_case(
        case_id="hf-sum-abs",
        a="1",
        b="2",
        total="3.01",
        tolerance=Tolerance("absolute", "0.01", "1"),
    )
    log = run_kats([hf.backend_sum(kats=(rel, rel_out, absolute))], health=_health())
    assert [c.passed for c in log.cases] == [True, False, True]


def test_backend_kat_that_calls_r_fails() -> None:
    fv = hf.backend_sum(compute=hf.harness_sum_calls_r)
    log = run_kats([fv], health=_health())
    case = log.cases[0]
    assert not case.passed
    assert "backend KAT called R" in (case.error or "")
    # The guard is lifted after the case.
    assert httpx.Client.send is not None
    assert "refuse" not in httpx.Client.send.__name__


def test_case_without_citation_fails() -> None:
    fv = hf.backend_sum(kats=(hf.sum_case(citation="  "),))
    case = run_kats([fv], health=_health()).cases[0]
    assert not case.passed
    assert "citation" in (case.error or "")


@pytest.mark.parametrize(
    "case",
    [
        hf.sum_case(unit="mg"),
        hf.sum_case(tolerance=Tolerance("absolute", "0", "mg")),
        hf.sum_case(tolerance=Tolerance("relative", "0", "%")),
        hf.sum_case(total="2.572e"),
        hf.sum_case(tolerance=Tolerance("absolute", "-1", "1")),
    ],
)
def test_ill_declared_case_fails(case) -> None:
    result = run_kats([hf.backend_sum(kats=(case,))], health=_health()).cases[0]
    assert not result.passed
    assert result.error


@pytest.mark.parametrize(
    "health",
    [
        None,
        {},
        "lock_mismatch",
        "no_digest",
        "sandbox_false",
    ],
)
def test_no_run_log_without_the_pinned_service(health: Any) -> None:
    if health == "lock_mismatch":
        health = _health(lock_hash="0" * 64)
    elif health == "no_digest":
        health = _health(R_IMAGE_DIGEST=None)
    elif health == "sandbox_false":
        body = _health()
        body["sandbox"]["egress_blocked"] = False
        health = body
    with pytest.raises(CalculationCallRefused):
        run_kats([hf.backend_sum()], health=health)


class _FakeResponse:
    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://r"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> Any:
        return self._body


def test_r_side_kat_runs_over_http_through_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    health = _health()
    calls: list[tuple[str, str, Any]] = []

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        calls.append(("GET", url, None))
        return _FakeResponse(200, health)

    def fake_post(url: str, json: dict, timeout: float) -> _FakeResponse:
        calls.append(("POST", url, json))
        return _FakeResponse(200, {"value": json["value"]})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    client = RCalculatorClient("http://r-calculator:8000")
    log = run_kats([hf.r_round_trip()], health=client.fetch_health_body(), r_client=client)
    assert all(c.passed and c.side == "r" for c in log.cases)
    posts = [c for c in calls if c[0] == "POST"]
    assert len(posts) == len(hf.R_ROUND_TRIP_PASSING)
    assert all(url.endswith(hf.R_ROUND_TRIP_ROUTE) for _m, url, _b in posts)
    # Each POST is preceded by a /health gate check.
    assert sum(1 for c in calls if c[0] == "GET") == len(posts) + 1


def test_r_side_kat_fails_when_r_returns_a_json_number(monkeypatch: pytest.MonkeyPatch) -> None:
    health = _health()
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _FakeResponse(200, health))
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: _FakeResponse(200, {"value": 0.026}))
    client = RCalculatorClient("http://r-calculator:8000")
    log = run_kats([hf.r_round_trip()], health=health, r_client=client)
    assert not log.cases[0].passed


def test_r_side_kat_fails_when_the_gate_refuses_mid_run(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = _health(lock_hash="1" * 64)
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _FakeResponse(200, bad))
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: pytest.fail("no POST after refusal"))
    client = RCalculatorClient("http://r-calculator:8000")
    log = run_kats([hf.r_round_trip()], health=_health(), r_client=client)
    assert all(not c.passed for c in log.cases)
    assert "lock_mismatch" in (log.cases[0].error or "")


def test_r_side_kat_without_a_client_fails() -> None:
    log = run_kats([hf.r_round_trip()], health=_health())
    assert all(not c.passed for c in log.cases)


def _edit(fv: FunctionVersion, **changes: Any) -> FunctionVersion:
    from dataclasses import replace

    return replace(fv, **changes)


def test_fingerprint_changes_with_every_declared_field() -> None:
    base = hf.backend_sum()
    fp = version_fingerprint(base)
    assert version_fingerprint(hf.backend_sum()) == fp
    edits = [
        _edit(base, description="total = b + a"),
        _edit(base, defaults={"a": "0"}),
        _edit(base, stop_rule="stop when a is negative"),
        _edit(base, missing_data_rule="a missing a is 0"),
        _edit(base, inputs={"a": "mg", "b": "1"}),
        _edit(base, outputs={"total": "mg"}),
        _edit(base, kats=(hf.sum_case(tolerance=Tolerance("absolute", "0.001", "1")),)),
        _edit(base, compute=hf.harness_sum_calls_r),
    ]
    for edited in edits:
        assert version_fingerprint(edited) != fp


def test_r_side_fingerprint_covers_the_listed_r_source(tmp_path: Path) -> None:
    repo = tmp_path
    svc = repo / "services" / "r-calculator" / "R"
    svc.mkdir(parents=True)
    (svc / "serialise.R").write_text("one <- 1\n", encoding="utf-8")
    first = version_fingerprint(hf.r_round_trip(), repo)
    (svc / "serialise.R").write_text("one <- 2\n", encoding="utf-8")
    assert version_fingerprint(hf.r_round_trip(), repo) != first


def test_harness_fixtures_are_labelled_and_are_not_catalog_functions() -> None:
    fixtures = [hf.backend_sum(), hf.r_round_trip(with_failing_case=True)]
    for fv in fixtures:
        assert fv.name.startswith("harness_fixture_")
        assert fv.name not in CATALOG_NAMES
        for case in fv.kats:
            assert case.citation.startswith("KAT harness test fixture")
            assert "not an SOP" in case.citation


@pytest.mark.skipif(
    not os.environ.get("KAT_R_CALCULATOR_URL"),
    reason="needs the running pinned R image (KAT_R_CALCULATOR_URL); CI job r-calculator-pin",
)
def test_r_side_harness_kats_on_the_pinned_image() -> None:
    client = RCalculatorClient(os.environ["KAT_R_CALCULATOR_URL"])
    health = client.fetch_health_body()
    fv = hf.r_round_trip(with_failing_case=True)
    log = run_kats([fv, hf.backend_sum()], health=health, r_client=client)
    out_path = os.environ.get("KAT_RUN_LOG_PATH")
    if out_path:
        Path(out_path).write_text(log.to_json() + "\n", encoding="utf-8")
    print(log.to_json())

    assert log.lock_hash == expected_lock_from_commit(find_repo_root()).lock_hash
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", log.image_digest)
    by_id = {c.case_id: c for c in log.cases}
    for case_id, _value, expected in hf.R_ROUND_TRIP_PASSING:
        result = by_id[case_id]
        assert result.side == "r", case_id
        assert result.passed, (case_id, result.error, result.outputs)
        assert result.outputs[0].observed == expected
    wrong = by_id["hf-r-deliberately-wrong"]
    assert not wrong.passed
    assert wrong.outputs[0].observed == "0.1"
    assert by_id["hf-sum-exact"].side == "backend" and by_id["hf-sum-exact"].passed
    assert Decimal(by_id["hf-r-sum-0.1-0.2"].outputs[0].observed) != Decimal("0.3")
