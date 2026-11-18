"""S5 backend decimal catalog functions (CALC-REQ-14, 18, 19, 37, 22).

KATs are the known-answer cases on the three versions. They run in the
backend decimal context and make no R call. Other cases here are unit tests.
"""
from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import calculation_catalog as catalog
from app.services import calculation_catalog_decimal as dec
from app.services import calculation_catalog_r as rcat
from app.services import calculation_catalog_s5 as s5
from app.services.calculation_catalog_r import MISSING_INPUT, CatalogInputRefused
from app.services.calculation_kat import no_r_calls, run_kats, version_fingerprint
from app.services.calculation_release import prepare_release
from app.services.calculation_runtime import expected_lock_from_commit, find_repo_root

DIGEST = "sha256:" + ("ab" * 32)
CV_100_110 = "6.7343502970147383276270891629033241836651041684616"
CV_1400 = "0.010100082576582595692056054308025268380014796995978"
CV_480_520 = "5.6568542494923801952067548968387923142786875015078"
CLOSED = (
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
)


def _health() -> dict[str, Any]:
    lock = expected_lock_from_commit(find_repo_root())
    return {
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


def _client() -> TestClient:
    return TestClient(s5.s5_catalog_app())


# ---- replicate_mean_cv (CALC-REQ-14, OQ-CALC-5) ----------------------------


def test_mean_of_1400_1_and_1400_3_is_exactly_1400_2() -> None:
    result = s5.replicate_mean_cv(["1400.1", "1400.3"])
    assert result.outputs["mean"] == "1400.2"
    assert result.outputs["percent_cv"] == CV_1400
    assert result.flags == ()
    assert result.r_called is False
    assert result.stop is None


def test_onset_times_in_seconds_use_the_same_function() -> None:
    """100 s and 110 s, and 480 s and 520 s. The function takes no unit."""
    pair = s5.replicate_mean_cv(["100", "110"])
    assert pair.outputs == {"mean": "105", "percent_cv": CV_100_110}
    onset = s5.replicate_mean_cv(["480", "520"])
    assert onset.outputs == {"mean": "500", "percent_cv": CV_480_520}
    three = s5.replicate_mean_cv(["10", "20", "30"])
    assert three.outputs == {"mean": "20", "percent_cv": "50"}
    assert list(inspect.signature(s5.replicate_mean_cv).parameters) == ["replicates"]
    source = inspect.getsource(s5.replicate_mean_cv_compute)
    for word in ("onset", "concentration", "EU/mL", "second"):
        assert word not in source


def test_concentration_replicates_use_the_same_function() -> None:
    """0.01, 0.02, and 0.03 concentration units. Sample %CV is exactly 50."""
    result = s5.replicate_mean_cv(["0.01", "0.02", "0.03"])
    assert result.outputs == {"mean": "0.02", "percent_cv": "50"}
    finer = s5.replicate_mean_cv(["0.026", "0.028"])
    assert finer.outputs["mean"] == "0.027"


def test_cv_uses_sample_standard_deviation_not_population() -> None:
    result = s5.replicate_mean_cv(["1", "2", "3"])
    assert result.outputs == {"mean": "2", "percent_cv": "50"}
    population = (Decimal(2) / Decimal(3)).sqrt() / Decimal(2) * Decimal(100)
    assert result.outputs["percent_cv"] != format(population, "f")


def test_one_replicate_gives_the_mean_no_cv_and_replicate_missing() -> None:
    result = s5.replicate_mean_cv(["1400.2"])
    assert result.outputs == {"mean": "1400.2"}
    assert result.flags == (s5.REPLICATE_MISSING,)
    assert "percent_cv" not in result.outputs
    assert result.stop is None


def test_one_numeric_and_one_non_numeric_is_replicate_missing() -> None:
    result = s5.replicate_mean_cv(["1400.2", "N/A"])
    assert result.outputs == {"mean": "1400.2"}
    assert result.flags == (s5.REPLICATE_MISSING,)
    blank = s5.replicate_mean_cv(["10", None])
    assert blank.outputs == {"mean": "10"}
    assert blank.flags == (s5.REPLICATE_MISSING,)


@pytest.mark.parametrize(
    "replicates",
    [None, [], ["N/A", ""], [None, None], [">100", "<0.1"]],
)
def test_no_numeric_replicate_is_missing_input(replicates: Any) -> None:
    result = s5.replicate_mean_cv(replicates)
    assert result.outputs == {}
    assert result.flags == (MISSING_INPUT,)
    assert result.stop is None


def test_mean_zero_keeps_the_mean_and_sets_mean_zero() -> None:
    result = s5.replicate_mean_cv(["1", "-1"])
    assert result.outputs == {"mean": "0"}
    assert result.flags == (s5.MEAN_ZERO,)
    assert result.stop is None
    zeros = s5.replicate_mean_cv(["0", "0"])
    assert zeros.outputs == {"mean": "0"}
    assert zeros.flags == (s5.MEAN_ZERO,)


def test_one_zero_is_replicate_missing_not_mean_zero() -> None:
    result = s5.replicate_mean_cv(["0"])
    assert result.outputs == {"mean": "0"}
    assert result.flags == (s5.REPLICATE_MISSING,)


def test_equal_replicates_have_zero_cv() -> None:
    result = s5.replicate_mean_cv(["100", "100"])
    assert result.outputs == {"mean": "100", "percent_cv": "0"}


def test_negative_mean_is_not_refused() -> None:
    result = s5.replicate_mean_cv(["-5", "-3"])
    assert result.outputs["mean"] == "-4"
    assert result.outputs["percent_cv"].startswith("-")
    assert result.stop is None


def test_replicate_json_number_is_refused() -> None:
    with pytest.raises(CatalogInputRefused):
        s5.replicate_mean_cv([1400.1, "1400.3"])
    with pytest.raises(CatalogInputRefused):
        s5.replicate_mean_cv("1400.1")
    with pytest.raises(CatalogInputRefused):
        s5.replicate_mean_cv([True])


# ---- spike_recovery (CALC-REQ-18, OQ-CALC-6) -------------------------------


def test_spike_examples_are_exact_in_decimal() -> None:
    hundred = s5.spike_recovery("0.06", "0.01", "0.05")
    fifty = s5.spike_recovery("0.026", "0.001", "0.05")
    two_hundred = s5.spike_recovery("0.171", "0.071", "0.05")
    assert hundred.outputs == {"recovery": "100"}
    assert fifty.outputs == {"recovery": "50"}
    assert two_hundred.outputs == {"recovery": "200"}
    assert hundred.r_called is False
    binary = ((0.171 - 0.071) * 100) / 0.05
    assert binary != 200


def test_spike_does_not_hardcode_the_nominal() -> None:
    source = inspect.getsource(s5.spike_recovery) + inspect.getsource(s5.spike_recovery_compute)
    assert "0.05" not in source
    other = s5.spike_recovery("2", "1", "4")
    assert other.outputs == {"recovery": "25"}


def test_spike_zero_recovery_is_stored() -> None:
    result = s5.spike_recovery("0.05", "0.05", "0.05")
    assert result.outputs == {"recovery": "0"}
    assert result.stop is None


def test_spike_negative_recovery_is_not_refused() -> None:
    result = s5.spike_recovery("0.01", "0.06", "0.05")
    assert result.outputs == {"recovery": "-100"}


@pytest.mark.parametrize(
    "spiked,unspiked,nominal",
    [
        (None, "0.01", "0.05"),
        ("N/A", "0.01", "0.05"),
        (">0.06", "0.01", "0.05"),
        ("0.06", None, "0.05"),
        ("0.06", "<0.01", "0.05"),
        ("0.06", "0.01", None),
        ("0.06", "0.01", "N/A"),
    ],
)
def test_spike_missing_input_is_missing_input(spiked: Any, unspiked: Any, nominal: Any) -> None:
    result = s5.spike_recovery(spiked, unspiked, nominal)
    assert result.outputs == {}
    assert result.flags == (MISSING_INPUT,)
    assert result.stop is None


@pytest.mark.parametrize("nominal", ["0", "0.0", "-0.05"])
def test_spike_nominal_not_positive_is_refused(nominal: str) -> None:
    with pytest.raises(CatalogInputRefused) as caught:
        s5.spike_recovery("0.06", "0.01", nominal)
    assert caught.value.code == "invalid_input"
    with pytest.raises(CatalogInputRefused):
        s5.spike_recovery(None, None, nominal)


def test_spike_json_number_is_refused() -> None:
    with pytest.raises(CatalogInputRefused):
        s5.spike_recovery(0.06, "0.01", "0.05")


# ---- limit_compare (CALC-REQ-19) -------------------------------------------


def test_limit_compare_uses_the_value_it_is_fed() -> None:
    """A numeric feed and a qualified feed are different calls. Nothing picks one."""
    calculated = s5.limit_compare("90", comparison="at_most", limit="100")
    assert calculated.outputs == {"verdict": "pass"}
    assert calculated.qualifier is None
    reported = s5.limit_compare(">100", comparison="at_most", limit="100")
    assert reported.outputs == {}
    assert reported.flags == ()
    assert reported.no_verdict == s5.UNSPECIFIED
    assert reported.qualifier == ">"
    assert reported.qualifier_limit == "100"
    assert s5.limit_compare("150", comparison="at_most", limit="100").outputs == {"verdict": "fail"}
    wider = s5.limit_compare(">100", comparison="at_most", limit="150")
    assert wider.outputs == {}
    assert wider.flags == ()
    assert wider.no_verdict == s5.UNSPECIFIED
    assert wider.qualifier == ">"
    assert wider.qualifier_limit == "100"


def test_at_most_equal_bound_passes_and_above_fails() -> None:
    assert s5.limit_compare("0.5", comparison="at_most", limit="0.5").outputs == {"verdict": "pass"}
    assert s5.limit_compare("0.6", comparison="at_most", limit="0.5").outputs == {"verdict": "fail"}
    assert s5.limit_compare("0.50", comparison="at_most", limit="0.500").outputs == {"verdict": "pass"}


def test_within_is_inclusive_and_outside_fails() -> None:
    assert s5.limit_compare("50", comparison="within", low="50", high="200").outputs == {
        "verdict": "pass"
    }
    assert s5.limit_compare("200", comparison="within", low="50", high="200").outputs == {
        "verdict": "pass"
    }
    assert s5.limit_compare("49", comparison="within", low="50", high="200").outputs == {
        "verdict": "fail"
    }
    assert s5.limit_compare("201", comparison="within", low="50", high="200").outputs == {
        "verdict": "fail"
    }


def test_absolute_compare_does_not_round_before_the_bound() -> None:
    passed = s5.limit_compare("-0.98", comparison="at_least", limit="0.980", absolute=True)
    failed = s5.limit_compare("-0.97995", comparison="at_least", limit="0.980", absolute=True)
    same = s5.limit_compare("0.980", comparison="at_least", limit="0.980", absolute=True)
    assert passed.outputs == {"verdict": "pass"}
    assert failed.outputs == {"verdict": "fail"}
    assert same.outputs == {"verdict": "pass"}
    signed = s5.limit_compare("-0.98", comparison="at_least", limit="0.980", absolute=False)
    assert signed.outputs == {"verdict": "fail"}


def test_qualified_less_than_at_most_follows_calc_req_19() -> None:
    under = s5.limit_compare("<0.4", comparison="at_most", limit="0.5")
    equal = s5.limit_compare("<0.5", comparison="at_most", limit="0.5")
    over = s5.limit_compare("<0.6", comparison="at_most", limit="0.5")
    assert under.outputs == {"verdict": "pass"}
    assert under.qualifier == "<" and under.qualifier_limit == "0.4"
    assert equal.outputs == {"verdict": "pass"}
    assert over.outputs == {}
    assert over.flags == (s5.LIMIT_ABOVE_EL,)
    assert over.qualifier == "<" and over.qualifier_limit == "0.6"
    assert over.stop is None


def test_two_less_than_kinds_pass_and_stay_distinct() -> None:
    first = s5.limit_compare(
        {"qualifier": "<", "limit": "0.4", "kind": "below_range"},
        comparison="at_most",
        limit="0.5",
    )
    second = s5.limit_compare(
        {"qualifier": "<", "limit": "0.4", "kind": "non_detect"},
        comparison="at_most",
        limit="0.5",
    )
    assert first.outputs == {"verdict": "pass"}
    assert second.outputs == {"verdict": "pass"}
    assert first.kind == "below_range"
    assert second.kind == "non_detect"
    assert first.qualifier == "<" and second.qualifier == "<"


def test_qualified_greater_than_at_most_is_not_judged() -> None:
    at_bound = s5.limit_compare(">0.5", comparison="at_most", limit="0.5", kind="above_curve")
    under_bound = s5.limit_compare(
        {"qualifier": ">", "limit": "0.4", "kind": "above_curve"},
        comparison="at_most",
        limit="0.5",
    )
    for result, limit_text in ((at_bound, "0.5"), (under_bound, "0.4")):
        assert result.outputs == {}
        assert result.flags == ()
        assert result.no_verdict == s5.UNSPECIFIED
        assert result.qualifier == ">"
        assert result.qualifier_limit == limit_text
        assert result.kind == "above_curve"
        assert result.stop is None
    assert "limit_below_el" not in Path(s5.__file__).read_text(encoding="utf-8")


def test_qualified_value_on_at_least_or_within_has_no_verdict_and_no_new_flag() -> None:
    at_least = s5.limit_compare(">100", comparison="at_least", limit="50")
    within = s5.limit_compare("<0.4", comparison="within", low="0", high="1", kind="below_range")
    assert at_least.outputs == {}
    assert at_least.flags == ()
    assert at_least.no_verdict == s5.UNSPECIFIED
    assert at_least.qualifier == ">" and at_least.qualifier_limit == "100"
    assert within.no_verdict == s5.UNSPECIFIED
    assert within.flags == ()
    assert within.kind == "below_range"
    assert within.flags == ()


def test_missing_value_or_missing_limit_gives_no_verdict() -> None:
    missing_value = s5.limit_compare(None, comparison="at_most", limit="0.5")
    assert missing_value.outputs == {}
    assert missing_value.flags == (MISSING_INPUT,)
    assert missing_value.no_verdict is None
    text = s5.limit_compare("N/A", comparison="at_most", limit="0.5")
    assert text.flags == (MISSING_INPUT,)
    missing_limit = s5.limit_compare("0.5", comparison="at_most", limit=None)
    assert missing_limit.outputs == {}
    assert missing_limit.flags == ()
    assert missing_limit.no_verdict == s5.MISSING_LIMIT
    missing_high = s5.limit_compare("50", comparison="within", low="50", high=None)
    assert missing_high.no_verdict == s5.MISSING_LIMIT
    qualified = s5.limit_compare(">100", comparison="at_most", limit=None)
    assert qualified.no_verdict == s5.MISSING_LIMIT
    assert qualified.qualifier == ">" and qualified.qualifier_limit == "100"
    assert qualified.flags == ()


def test_limit_compare_refusals() -> None:
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare("0.5", comparison="below", limit="0.5")
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare(0.5, comparison="at_most", limit="0.5")
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare("1", comparison="within", low="2", high="1")
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare(">100", comparison="at_most", limit="100", absolute=True)
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare("1", comparison="at_most", limit="1", kind="below_range")
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare("> 100", comparison="at_most", limit="1")
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare(
            {"qualifier": "<", "limit": "0.4", "kind": "a"},
            comparison="at_most",
            limit="0.5",
            kind="b",
        )
    source = inspect.getsource(s5.limit_compare) + inspect.getsource(s5.numeric_verdict)
    assert "0.980" not in source
    assert "0.5" not in source


def test_low_above_high_is_refused_even_when_the_value_is_missing() -> None:
    with pytest.raises(CatalogInputRefused):
        s5.limit_compare(None, comparison="within", low="5", high="1")


# ---- HTTP: stops are not these outcomes; refusals are 400; missing is 200 --


def test_http_success_and_missing_input_are_200() -> None:
    with _client() as client:
        mean = client.post(
            "/catalog/replicate_mean_cv/v1",
            json={"replicates": ["1400.1", "1400.3"]},
        )
        assert mean.status_code == 200
        assert mean.json()["outputs"]["mean"] == "1400.2"
        assert mean.json()["r_called"] is False
        assert all(isinstance(item, str) for item in mean.json()["outputs"].values())

        missing = client.post("/catalog/replicate_mean_cv/v1", json={"replicates": None})
        assert missing.status_code == 200
        assert missing.json()["outputs"] == {}
        assert missing.json()["flags"] == ["missing_input"]
        assert "stop" not in missing.json()

        recovery = client.post(
            "/catalog/spike_recovery/v1",
            json={"spiked": "0.171", "unspiked": "0.071", "nominal_spike": "0.05"},
        )
        assert recovery.status_code == 200
        assert recovery.json()["outputs"] == {"recovery": "200"}

        verdict = client.post(
            "/catalog/limit_compare/v1",
            json={"comparison": "at_most", "value": "0.5", "limit": "0.5"},
        )
        assert verdict.status_code == 200
        assert verdict.json()["outputs"] == {"verdict": "pass"}
        assert "qualifier" not in verdict.json()


def test_http_refusal_is_400_and_flags_are_200() -> None:
    with _client() as client:
        number = client.post(
            "/catalog/spike_recovery/v1",
            json={"spiked": "0.06", "unspiked": 0.01, "nominal_spike": "0.05"},
        )
        assert number.status_code == 400
        assert number.json()["code"] == "invalid_input"
        assert "stop" not in number.json()

        nominal = client.post(
            "/catalog/spike_recovery/v1",
            json={"spiked": "0.06", "unspiked": "0.01", "nominal_spike": "0"},
        )
        assert nominal.status_code == 400

        extra = client.post(
            "/catalog/replicate_mean_cv/v1",
            json={"replicates": ["1", "2"], "model": "LL.4"},
        )
        assert extra.status_code == 400
        assert "unknown field" in extra.json()["detail"]

        low_form = client.post(
            "/catalog/limit_compare/v1",
            json={"comparison": "at_most", "value": "1", "limit": "1", "low": "0"},
        )
        assert low_form.status_code == 400

        mean_zero = client.post(
            "/catalog/replicate_mean_cv/v1",
            json={"replicates": ["1", "-1"]},
        )
        assert mean_zero.status_code == 200
        assert mean_zero.json()["outputs"] == {"mean": "0"}
        assert mean_zero.json()["flags"] == ["mean_zero"]
        assert "stop" not in mean_zero.json()

        above = client.post(
            "/catalog/limit_compare/v1",
            json={"comparison": "at_most", "value": "<0.6", "limit": "0.5", "kind": "below_range"},
        )
        assert above.status_code == 200
        body = above.json()
        assert body["outputs"] == {}
        assert body["flags"] == ["limit_above_el"]
        assert body["qualifier"] == "<"
        assert body["qualifier_limit"] == "0.6"
        assert body["kind"] == "below_range"
        assert "stop" not in body

        carried = client.post(
            "/catalog/limit_compare/v1",
            json={"comparison": "at_least", "value": ">100", "limit": "50"},
        )
        assert carried.status_code == 200
        assert carried.json()["outputs"] == {}
        assert carried.json()["no_verdict"] == "unspecified"
        assert carried.json()["qualifier"] == ">"
        assert "flags" not in carried.json()

        greater = client.post(
            "/catalog/limit_compare/v1",
            json={
                "comparison": "at_most",
                "value": ">100",
                "limit": "100",
                "kind": "above_curve",
            },
        )
        assert greater.status_code == 200
        body = greater.json()
        assert body["outputs"] == {}
        assert body["no_verdict"] == "unspecified"
        assert body["qualifier"] == ">"
        assert body["qualifier_limit"] == "100"
        assert body["kind"] == "above_curve"
        assert "flags" not in body
        assert "stop" not in body


def test_s5_routes_are_not_mounted_on_the_lims_app_or_in_r() -> None:
    root = find_repo_root()
    main = (root / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "calculation_catalog_s5" not in main
    assert "calculation_catalog.py" not in main
    plumber = (root / "services" / "r-calculator" / "plumber.R").read_text(encoding="utf-8")
    catalog_r = (root / "services" / "r-calculator" / "R" / "catalog.R").read_text(encoding="utf-8")
    for name in ("replicate_mean_cv", "spike_recovery", "limit_compare"):
        assert name not in plumber
        assert name not in catalog_r
        assert all(version.name != name for version in rcat.R_CATALOG_VERSIONS)


def test_functions_do_not_call_r() -> None:
    module = Path(s5.__file__).read_text(encoding="utf-8")
    assert "httpx" not in module
    assert "r_calculator" not in module
    with no_r_calls():
        s5.replicate_mean_cv(["10", "20", "30"])
        s5.spike_recovery("0.06", "0.01", "0.05")
        s5.limit_compare(">100", comparison="at_most", limit="100")


# ---- catalog of eleven and KATs --------------------------------------------


def test_catalog_lists_exactly_eleven_code_entries() -> None:
    versions = catalog.closed_catalog()
    names = [version.name for version in versions]
    assert names == list(CLOSED)
    assert len(names) == 11
    for name in names:
        assert not name.startswith("elisa_")
        assert not name.startswith("lal_")
    assert not hasattr(catalog, "register")
    assert not hasattr(catalog, "add_function")
    for version in versions:
        assert version.version == 1
        assert version.description and version.stop_rule and version.missing_data_rule
        version_fingerprint(version)
    s5_names = [version.name for version in s5.S5_CATALOG_VERSIONS]
    assert s5_names == ["replicate_mean_cv", "spike_recovery", "limit_compare"]
    for version in s5.S5_CATALOG_VERSIONS:
        assert version.side == "backend" and version.route is None and version.r_sources == ()
        assert version.kats
    assert [version.name for version in dec.DECIMAL_CATALOG_VERSIONS] == [
        "apply_dilution",
        "subtract",
        "copy_raw",
        "convert_units",
    ]
    assert all(version.kats == () for version in rcat.R_CATALOG_VERSIONS)


def test_kats_pass_at_tolerance_zero_and_do_not_call_r() -> None:
    log = run_kats(list(s5.S5_CATALOG_VERSIONS), health=_health())
    assert log.lock_hash == expected_lock_from_commit(find_repo_root()).lock_hash
    assert len(log.cases) == 13
    for case in log.cases:
        assert case.passed, (
            case.case_id,
            case.error,
            [(item.name, item.observed, item.expected) for item in case.outputs],
        )
        assert case.side == "backend"
        assert case.version == 1
        assert "Not an SOP" in case.citation
        for output in case.outputs:
            assert output.tolerance.kind == "absolute"
            assert output.tolerance.value == "0"
            assert output.passed
    by_id = {case.case_id: case for case in log.cases}
    mean = {item.name: item.observed for item in by_id["replicate-mean-1400.1-1400.3"].outputs}
    assert mean["mean"] == "1400.2"
    assert mean["percent_cv"] == CV_1400
    times = {item.name: item.observed for item in by_id["replicate-onset-time-100s-110s"].outputs}
    assert times == {"mean": "105", "percent_cv": CV_100_110}
    concentration = {
        item.name: item.observed
        for item in by_id["replicate-concentration-0.01-0.02-0.03"].outputs
    }
    assert concentration == {"mean": "0.02", "percent_cv": "50"}
    assert by_id["spike-0.171-0.071-0.05-is-200"].outputs[0].observed == "200"
    assert by_id["limit-at-most-0.5-passes"].outputs[0].observed == "pass"
    assert by_id["limit-at-most-0.6-fails"].outputs[0].observed == "fail"
    assert by_id["limit-within-49-fails"].outputs[0].observed == "fail"
    assert by_id["limit-at-least-abs-0.97995-fails"].outputs[0].observed == "fail"

    record = prepare_release(
        "s5-decimal-v1",
        [version.key for version in s5.S5_CATALOG_VERSIONS],
        catalog=list(s5.S5_CATALOG_VERSIONS),
        ledger=[],
        run_log=log,
    )
    assert record.lock_hash == log.lock_hash
    assert {item.name for item in record.adds} == {
        "replicate_mean_cv",
        "spike_recovery",
        "limit_compare",
    }
    assert "write_release" not in Path(s5.__file__).read_text(encoding="utf-8")
