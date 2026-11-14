"""S3 R-side catalog functions (CALC-REQ-8, 9, 12, 17, 24, 37).

Unit tests, not KATs. No case here is a KAT of a catalog version, and none
carries a source citation. Curve data is generated in this file from stated
parameters. The four versions have no KAT cases yet (OQ-CALC-13), so the
release check refuses them.

``test_*_on_the_pinned_image`` runs only when ``KAT_R_CALCULATOR_URL`` points
at a running pinned image (CI job ``r-calculator-pin``).
"""
from __future__ import annotations

import math
import os
from decimal import Decimal
from typing import Any, Callable, Optional

import pytest

from app.services import calculation_catalog_r as cat
from app.services.calculation_kat import KatRunLog, version_fingerprint
from app.services.calculation_release import ReleaseRefused, prepare_release
from app.services.calculation_runtime import (
    CalculationCallRefused,
    expected_lock_from_commit,
    find_repo_root,
)
from app.services.r_calculator_client import RCalculatorClient


class StubR:
    """Records every R call. ``reply`` returns the R body for one call."""

    def __init__(self, reply: Optional[Callable[[str, dict], Any]] = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._reply = reply or (lambda path, payload: pytest.fail(f"unexpected R call {path}"))

    def execute_calculation_request(self, path: str, payload: dict[str, Any]) -> Any:
        self.calls.append((path, payload))
        return self._reply(path, payload)


def _replies(body: Any) -> StubR:
    return StubR(lambda _path, _payload: body)


FIT_OUT = {
    "bottom": "0.05",
    "top": "2.5",
    "slope": "1.5",
    "inflection": "40",
    "r_squared": "0.9999999999999999",
}


def _points(levels: list[str], responses: Optional[list[Optional[Any]]] = None) -> list[dict]:
    responses = responses if responses is not None else ["1.0"] * len(levels)
    return [
        {"concentration": c, "response": r, "replicate": f"r{i}"}
        for i, (c, r) in enumerate(zip(levels, responses))
    ]


# ---- fit_4pl ---------------------------------------------------------------


def test_fit_4pl_sends_decimal_strings_and_keeps_r_strings() -> None:
    stub = _replies(FIT_OUT)
    pts = _points(["5", "10", "20", "40", "80"], ["2.4", "2.1", "1.6", "1.275", "0.9"])
    result = cat.fit_4pl(pts, stub)
    assert result.stop is None and result.r_called
    path, payload = stub.calls[0]
    assert path == "/catalog/fit_4pl/v1"
    assert payload == {
        "concentration": ["5", "10", "20", "40", "80"],
        "response": ["2.4", "2.1", "1.6", "1.275", "0.9"],
    }
    assert all(isinstance(v, str) for v in payload["concentration"] + payload["response"])
    assert result.outputs == {**FIT_OUT, "points_used": "5", "points_excluded": "0"}


def test_fit_4pl_three_levels_stops_curve_not_fitted_without_r() -> None:
    stub = StubR()
    pts = _points(["10", "10", "40", "40", "160", "160"])
    result = cat.fit_4pl(pts, stub)
    assert result.stop == "curve_not_fitted"
    assert result.outputs == {} and not result.r_called and stub.calls == []


@pytest.mark.parametrize("missing", [None, "", "N/A"])
def test_fit_4pl_missing_response_is_excluded_and_counted(missing: Any) -> None:
    stub = _replies(FIT_OUT)
    pts = _points(["5", "10", "20", "40", "40"], ["2.4", "2.1", "1.6", "1.275", missing])
    result = cat.fit_4pl(pts, stub)
    assert result.outputs["points_used"] == "4"
    assert result.outputs["points_excluded"] == "1"
    assert len(stub.calls[0][1]["response"]) == 4
    assert "0" not in stub.calls[0][1]["response"]


def test_fit_4pl_missing_responses_can_drop_it_below_four_levels() -> None:
    pts = _points(["5", "10", "20", "40"], ["2.4", "2.1", "1.6", None])
    result = cat.fit_4pl(pts, StubR())
    assert result.stop == "curve_not_fitted" and not result.r_called


@pytest.mark.parametrize(
    "bad",
    [
        {"concentration": 5, "response": "1", "replicate": "r"},
        {"concentration": "5", "response": 1.0, "replicate": "r"},
        {"concentration": "5", "response": True, "replicate": "r"},
        {"concentration": "-5", "response": "1", "replicate": "r"},
        {"concentration": "NaN", "response": "1", "replicate": "r"},
        {"concentration": "5", "response": "1", "replicate": ""},
    ],
)
def test_fit_4pl_refuses_ill_typed_inputs_before_r(bad: dict) -> None:
    pts = _points(["10", "20", "40", "80"]) + [bad]
    with pytest.raises(cat.CatalogInputRefused):
        cat.fit_4pl(pts, StubR())


def test_fit_4pl_r_stop_is_passed_through() -> None:
    body = {"stop": "curve_not_fitted", "detail": "the fit did not converge"}
    result = cat.fit_4pl(_points(["5", "10", "20", "40"]), _replies(body))
    assert result.stop == "curve_not_fitted" and result.r_called and result.outputs == {}


@pytest.mark.parametrize("value", ["NaN", "Inf", "-Inf", "NA", None, 1.5, "1e999x"])
def test_fit_4pl_non_finite_r_output_stops_r_non_finite(value: Any) -> None:
    body = dict(FIT_OUT)
    body["slope"] = value
    result = cat.fit_4pl(_points(["5", "10", "20", "40"]), _replies(body))
    assert result.stop == "r_non_finite"
    assert result.outputs == {} and result.qualifier is None and result.flags == ()


def test_fit_4pl_r_non_finite_stop_from_r() -> None:
    body = {"stop": "r_non_finite", "detail": "R output r_squared is not finite"}
    result = cat.fit_4pl(_points(["5", "10", "20", "40"]), _replies(body))
    assert result.stop == "r_non_finite" and result.outputs == {}


def test_undeclared_r_stop_is_refused() -> None:
    body = {"stop": "pass"}
    with pytest.raises(CalculationCallRefused) as caught:
        cat.fit_4pl(_points(["5", "10", "20", "40"]), _replies(body))
    assert caught.value.code == "r_service"


@pytest.mark.parametrize("code", ["r_timeout", "backend_timeout"])
def test_timeout_is_a_stage_stop_with_no_result(code: str) -> None:
    def raise_timeout(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused(code, "timed out")

    result = cat.fit_4pl(_points(["5", "10", "20", "40"]), StubR(raise_timeout))
    assert result.stop == code and result.outputs == {}


@pytest.mark.parametrize("code", ["lock_mismatch", "sandbox", "missing_digest"])
def test_gate_refusal_is_raised_not_a_stop(code: str) -> None:
    def refuse(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused(code, "refused")

    with pytest.raises(CalculationCallRefused) as caught:
        cat.fit_4pl(_points(["5", "10", "20", "40"]), StubR(refuse))
    assert caught.value.code == code


# ---- inverse_4pl -----------------------------------------------------------

CURVE = {"bottom": "0.05", "top": "2.5", "slope": "-1.5", "inflection": "40"}


def _inv(response: Any, low: str = "0.1", high: str = "2.4", reply: Any = None) -> tuple:
    stub = _replies(reply if reply is not None else {"concentration": "30"})
    return cat.inverse_4pl(CURVE, response, low, high, stub), stub


def test_inverse_4pl_in_range_calls_r_and_keeps_its_string() -> None:
    result, stub = _inv("1.0", reply={"concentration": "30.000000000000004"})
    assert result.outputs == {"concentration": "30.000000000000004"}
    assert stub.calls == [("/catalog/inverse_4pl/v1", {**CURVE, "response": "1.0"})]


@pytest.mark.parametrize(
    "response,low,high,qualifier,end",
    [
        ("2.41", "0.1", "2.4", ">", "high"),  # increasing curve, past the high end
        ("0.09", "0.1", "2.4", "<", "low"),
        ("0.09", "2.4", "0.1", ">", "high"),  # decreasing curve
        ("2.41", "2.4", "0.1", "<", "low"),
    ],
)
def test_inverse_4pl_past_either_end_is_qualified_with_no_r_call(
    response: str, low: str, high: str, qualifier: str, end: str
) -> None:
    stub = StubR()
    result = cat.inverse_4pl(CURVE, response, low, high, stub)
    assert (result.qualifier, result.end) == (qualifier, end)
    assert result.outputs == {} and result.stop is None
    assert not result.r_called and stub.calls == []


@pytest.mark.parametrize("response", ["0.1", "2.4"])
def test_inverse_4pl_response_equal_to_an_end_mean_is_in_range(response: str) -> None:
    result, stub = _inv(response)
    assert result.qualifier is None and len(stub.calls) == 1


def test_inverse_4pl_range_check_is_decimal_not_binary() -> None:
    # 0.30000000000000001 and 0.3 are one double; in decimal the first is past the end.
    result, stub = _inv("0.30000000000000001", low="0.1", high="0.3")
    assert result.qualifier == ">" and stub.calls == []


@pytest.mark.parametrize("missing", [None, "", "N/A"])
def test_inverse_4pl_missing_response(missing: Any) -> None:
    stub = StubR()
    result = cat.inverse_4pl(CURVE, missing, "0.1", "2.4", stub)
    assert result.flags == ("missing_input",) and result.outputs == {} and stub.calls == []


def test_inverse_4pl_at_or_beyond_an_asymptote_is_flagged_not_a_number() -> None:
    curve = {"bottom": "0.2", "top": "2.0", "slope": "1", "inflection": "40"}
    for response in ("0.2", "2.0", "2.1"):
        stub = StubR()
        result = cat.inverse_4pl(curve, response, "0.1", "2.4", stub)
        assert result.flags == ("response_at_asymptote",), response
        assert result.outputs == {} and stub.calls == []


def test_inverse_4pl_non_finite_r_output_stops() -> None:
    result, _stub = _inv("1.0", reply={"concentration": "NaN"})
    assert result.stop == "r_non_finite" and result.outputs == {}


@pytest.mark.parametrize(
    "curve,low,high",
    [
        ({**CURVE, "slope": "0"}, "0.1", "2.4"),
        ({**CURVE, "top": 2.5}, "0.1", "2.4"),
        (CURVE, "0.1", "0.1"),
        (CURVE, 0.1, "2.4"),
    ],
)
def test_inverse_4pl_refuses_bad_inputs(curve: dict, low: Any, high: Any) -> None:
    with pytest.raises(cat.CatalogInputRefused):
        cat.inverse_4pl(curve, "1.0", low, high, StubR())


# ---- fit_loglog_linear -----------------------------------------------------

LL_OUT = {"slope": "-0.8", "intercept": "0.5", "r": "-1"}


def _ll_points(xs: list[str], ys: list[Any], reps: Optional[list] = None) -> list[dict]:
    out = []
    for i, (x, y) in enumerate(zip(xs, ys)):
        point = {"x": x, "y": y, "point_id": f"p{i}"}
        if reps is not None:
            point["replicates"] = reps[i]
        out.append(point)
    return out


def test_fit_loglog_linear_four_points() -> None:
    stub = _replies(LL_OUT)
    pts = _ll_points(["0.005", "0.05", "0.5", "5"], ["2200", "350", "56", "8.9"])
    result = cat.fit_loglog_linear(pts, stub)
    assert result.outputs == {**LL_OUT, "points_used": "4", "points_dropped": "0"}
    assert stub.calls[0] == (
        "/catalog/fit_loglog_linear/v1",
        {"x": ["0.005", "0.05", "0.5", "5"], "y": ["2200", "350", "56", "8.9"]},
    )


def test_fit_loglog_linear_drops_a_point_with_no_y_and_names_it() -> None:
    stub = _replies(LL_OUT)
    pts = _ll_points(["0.005", "0.05", "0.5", "5"], ["2200", None, "56", "8.9"])
    result = cat.fit_loglog_linear(pts, stub)
    assert result.outputs["points_used"] == "3"
    assert result.outputs["points_dropped"] == "1"
    assert result.dropped == ("p1",)
    assert stub.calls[0][1]["x"] == ["0.005", "0.5", "5"]


@pytest.mark.parametrize(
    "xs,ys,reps",
    [
        (["0", "0.05", "0.5", "5"], ["2200", "350", "56", "8.9"], None),
        (["-1", "0.05", "0.5", "5"], ["2200", "350", "56", "8.9"], None),
        (["0.005", "0.05", "0.5", "5"], ["0", "350", "56", "8.9"], None),
        (["0.005", "0.05", "0.5", "5"], ["2200", "-350", "56", "8.9"], None),
        (
            ["0.005", "0.05", "0.5", "5"],
            ["2200", "350", "56", "8.9"],
            [["2200", "0"], None, None, None],
        ),
    ],
)
def test_fit_loglog_linear_non_positive_stops_before_r(xs, ys, reps) -> None:
    stub = StubR()
    result = cat.fit_loglog_linear(_ll_points(xs, ys, reps), stub)
    assert result.stop == "non_positive_log_input"
    assert result.outputs == {} and stub.calls == []


def test_fit_loglog_linear_no_y_at_all_is_missing_input() -> None:
    stub = StubR()
    result = cat.fit_loglog_linear(_ll_points(["1", "10"], [None, "N/A"]), stub)
    assert result.flags == ("missing_input",) and result.dropped == ("p0", "p1")
    assert stub.calls == []


def test_fit_loglog_linear_non_finite_r_output_stops() -> None:
    result = cat.fit_loglog_linear(
        _ll_points(["1", "10"], ["1", "2"]), _replies({**LL_OUT, "r": "NA"})
    )
    assert result.stop == "r_non_finite" and result.outputs == {}


def test_fit_loglog_linear_refuses_json_numbers() -> None:
    with pytest.raises(cat.CatalogInputRefused):
        cat.fit_loglog_linear([{"x": 1.0, "y": "2", "point_id": "p"}], StubR())


# ---- inverse_loglog_linear -------------------------------------------------

NEG_FIT = {"slope": "-0.8", "intercept": "0.5"}
POS_FIT = {"slope": "0.8", "intercept": "0.5"}


@pytest.mark.parametrize(
    "fit,y,low_x,high_x,qualifier,end",
    [
        (NEG_FIT, "8.8", "2200", "8.9", ">", "high"),
        (NEG_FIT, "2201", "2200", "8.9", "<", "low"),
        (POS_FIT, "2201", "8.9", "2200", ">", "high"),
        (POS_FIT, "8.8", "8.9", "2200", "<", "low"),
    ],
)
def test_inverse_loglog_linear_follows_the_sign_of_the_slope(
    fit, y, low_x, high_x, qualifier, end
) -> None:
    stub = StubR()
    result = cat.inverse_loglog_linear(fit, y, low_x, high_x, stub)
    assert (result.qualifier, result.end) == (qualifier, end)
    assert result.outputs == {} and stub.calls == []


def test_inverse_loglog_linear_in_range_calls_r() -> None:
    stub = _replies({"x": "0.2"})
    result = cat.inverse_loglog_linear(NEG_FIT, "100", "2200", "8.9", stub)
    assert result.outputs == {"x": "0.2"}
    assert stub.calls == [
        ("/catalog/inverse_loglog_linear/v1", {"slope": "-0.8", "intercept": "0.5", "y": "100"})
    ]


@pytest.mark.parametrize("y", ["2200", "8.9"])
def test_inverse_loglog_linear_y_equal_to_an_endpoint_mean_is_in_range(y: str) -> None:
    stub = _replies({"x": "1"})
    cat.inverse_loglog_linear(NEG_FIT, y, "2200", "8.9", stub)
    assert len(stub.calls) == 1


def test_inverse_loglog_linear_missing_y() -> None:
    result = cat.inverse_loglog_linear(NEG_FIT, None, "2200", "8.9", StubR())
    assert result.flags == ("missing_input",) and result.outputs == {}


def test_inverse_loglog_linear_non_positive_endpoint_mean_stops() -> None:
    result = cat.inverse_loglog_linear(NEG_FIT, "1", "2200", "0", StubR())
    assert result.stop == "non_positive_log_input"


@pytest.mark.parametrize(
    "fit,low_x,high_x",
    [
        ({"slope": "0", "intercept": "0.5"}, "2200", "8.9"),
        (NEG_FIT, "8.9", "2200"),
        (POS_FIT, "2200", "8.9"),
        (POS_FIT, "8.9", "8.9"),
        ({"slope": -0.8, "intercept": "0.5"}, "2200", "8.9"),
    ],
)
def test_inverse_loglog_linear_refuses_bad_inputs(fit, low_x, high_x) -> None:
    with pytest.raises(cat.CatalogInputRefused):
        cat.inverse_loglog_linear(fit, "100", low_x, high_x, StubR())


def test_inverse_loglog_linear_non_finite_r_output_stops() -> None:
    result = cat.inverse_loglog_linear(NEG_FIT, "100", "2200", "8.9", _replies({"x": "Inf"}))
    assert result.stop == "r_non_finite" and result.outputs == {}


# ---- declarations and release state ----------------------------------------


def test_the_four_r_side_versions_are_declared_with_every_field() -> None:
    names = [fv.name for fv in cat.R_CATALOG_VERSIONS]
    assert names == ["fit_4pl", "inverse_4pl", "fit_loglog_linear", "inverse_loglog_linear"]
    for fv in cat.R_CATALOG_VERSIONS:
        assert fv.version == 1 and fv.side == "r"
        assert fv.route == f"/catalog/{fv.name}/v1"
        assert fv.description and fv.stop_rule and fv.missing_data_rule
        assert fv.inputs and fv.outputs and all(fv.outputs.values())
        assert not fv.name.startswith(("elisa", "lal"))
        assert fv.compute is None
        assert fv.r_sources == ("R/catalog.R", "R/serialise.R")
        version_fingerprint(fv, find_repo_root())


def test_no_r_side_version_has_kat_cases_yet() -> None:
    # OQ-CALC-13: no citable source with expected values is in the repo.
    for fv in cat.R_CATALOG_VERSIONS:
        assert fv.kats == ()


@pytest.mark.parametrize("fv", cat.R_CATALOG_VERSIONS, ids=lambda fv: fv.name)
def test_release_of_an_r_side_version_is_refused_for_an_absent_kat_run(fv) -> None:
    lock = expected_lock_from_commit(find_repo_root()).lock_hash
    empty_log = KatRunLog(lock_hash=lock, image_digest="sha256:" + "ab" * 32, ran_at="t", cases=())
    for run_log in (None, empty_log):
        with pytest.raises(ReleaseRefused) as caught:
            prepare_release(
                f"{fv.name}-v1",
                [fv.key],
                catalog=list(cat.R_CATALOG_VERSIONS),
                ledger=[],
                run_log=run_log,
                lock_hash=lock,
            )
        assert caught.value.code == "kat_absent"


def test_dose_response_routes_are_still_not_calculation_calls() -> None:
    client = RCalculatorClient("http://r-calculator:8000")
    for path in ("/fit", "/svg/full"):
        with pytest.raises(CalculationCallRefused) as caught:
            client.execute_calculation_request(path, {})
        assert caught.value.code == "route"


# ---- against the pinned image ----------------------------------------------

LIVE = pytest.mark.skipif(
    not os.environ.get("KAT_R_CALCULATOR_URL"),
    reason="needs the running pinned R image (KAT_R_CALCULATOR_URL); CI job r-calculator-pin",
)


class CountingClient:
    def __init__(self, inner: RCalculatorClient) -> None:
        self.inner = inner
        self.paths: list[str] = []

    def execute_calculation_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.paths.append(path)
        return self.inner.execute_calculation_request(path, payload)


def _live() -> CountingClient:
    return CountingClient(RCalculatorClient(os.environ["KAT_R_CALCULATOR_URL"]))


def _close(text: str, want: float, rel: float) -> bool:
    return abs(Decimal(text) - Decimal(repr(want))) <= Decimal(repr(rel)) * abs(Decimal(repr(want)))


@LIVE
def test_4pl_fit_and_inverse_on_the_pinned_image() -> None:
    client = _live()
    b, c, d, e = 1.5, 0.05, 2.5, 40.0

    def ll4(x: float) -> float:
        return c + (d - c) / (1 + math.exp(b * (math.log(x) - math.log(e))))

    concs = [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0]
    pts = [
        {"concentration": repr(x), "response": repr(ll4(x)), "replicate": f"r{i}"}
        for i, x in enumerate(concs)
    ]
    pts.append({"concentration": "320.0", "response": None, "replicate": "r-missing"})
    fit = cat.fit_4pl(pts, client)
    assert fit.stop is None, fit.detail
    assert fit.outputs["points_used"] == "7" and fit.outputs["points_excluded"] == "1"
    for name, want in (("slope", b), ("bottom", c), ("top", d), ("inflection", e)):
        assert _close(fit.outputs[name], want, 1e-6), (name, fit.outputs[name])
    for name in cat.FOUR_PL_PARAMETERS + ("r_squared",):
        assert cat.is_decimal_string(fit.outputs[name])

    three = [
        {"concentration": repr(x), "response": repr(ll4(x)), "replicate": f"r{i}"}
        for i, x in enumerate([10.0, 10.0, 40.0, 40.0, 160.0, 160.0])
    ]
    calls_before = len(client.paths)
    assert cat.fit_4pl(three, client).stop == "curve_not_fitted"
    assert len(client.paths) == calls_before

    low_mean, high_mean = repr(ll4(5.0)), repr(ll4(320.0))
    inv = cat.inverse_4pl(fit.outputs, repr(ll4(30.0)), low_mean, high_mean, client)
    assert inv.stop is None and _close(inv.outputs["concentration"], 30.0, 1e-6)

    # With slope > 0 drc's LL.4 decreases: the high-concentration end has the low response.
    calls_before = len(client.paths)
    past_low_conc = cat.inverse_4pl(fit.outputs, "2.49", low_mean, high_mean, client)
    past_high_conc = cat.inverse_4pl(fit.outputs, "0.01", low_mean, high_mean, client)
    assert (past_low_conc.qualifier, past_low_conc.end) == ("<", "low")
    assert (past_high_conc.qualifier, past_high_conc.end) == (">", "high")
    assert len(client.paths) == calls_before


@LIVE
def test_loglog_fit_and_inverse_on_the_pinned_image() -> None:
    client = _live()
    xs = [0.005, 0.05, 0.5, 5.0]
    pts = [
        {"x": repr(x), "y": repr(10 ** (0.5 - 0.8 * math.log10(x))), "point_id": f"p{i}"}
        for i, x in enumerate(xs)
    ]
    fit = cat.fit_loglog_linear(pts, client)
    assert fit.stop is None, fit.detail
    assert _close(fit.outputs["slope"], -0.8, 1e-12)
    assert _close(fit.outputs["intercept"], 0.5, 1e-12)
    assert _close(fit.outputs["r"], -1.0, 1e-12)

    low_x_mean, high_x_mean = pts[0]["y"], pts[-1]["y"]
    y = repr(10 ** (0.5 - 0.8 * math.log10(0.2)))
    inv = cat.inverse_loglog_linear(fit.outputs, y, low_x_mean, high_x_mean, client)
    assert inv.stop is None and _close(inv.outputs["x"], 0.2, 1e-9)

    calls_before = len(client.paths)
    past = cat.inverse_loglog_linear(fit.outputs, "0.5", low_x_mean, high_x_mean, client)
    assert past.qualifier == ">" and len(client.paths) == calls_before

    zero = cat.fit_loglog_linear([{**pts[0], "x": "0"}] + pts[1:], client)
    assert zero.stop == "non_positive_log_input" and len(client.paths) == calls_before

    one = cat.fit_loglog_linear(pts[:1], client)
    assert one.stop == "r_non_finite" and one.outputs == {}
