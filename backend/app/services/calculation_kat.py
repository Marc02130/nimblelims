"""Known-answer test (KAT) harness and run log (CALC-REQ-5, CALC-REQ-6).

A catalog function version declares its inputs and outputs with units, its
stop and missing-data rules, a plain-language formula, and its KATs. A KAT
case supplies every input itself, so no case reads a constant from a
configuration.

The split follows CALC-REQ-37:

- R-side versions run against the built, pinned image over HTTP, through
  ``RCalculatorClient.execute_calculation_request``. Every call passes the
  CALC-REQ-4 / 4a lock and sandbox gate, so a host R process cannot pass.
- Backend versions run the backend's decimal code with no R call. Any HTTP
  request made while a backend case runs fails that case.

Values are decimal strings. Comparison is in Python ``decimal`` (precision
50, ROUND_HALF_EVEN). The run log names the lock hash and built image digest
it ran on, and per case the function name and version, R or backend, the
observed and expected values, the tolerance, pass or fail, and the citation.
"""
from __future__ import annotations

import contextlib
import decimal
import hashlib
import inspect
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Mapping, Optional, Protocol, Sequence

import httpx

from app.services.calculation_runtime import (
    R_SERVICE_RELATIVE,
    CalculationCallRefused,
    ExpectedLock,
    begin_calculation_call,
    find_repo_root,
)

Side = Literal["r", "backend"]
ToleranceKind = Literal["absolute", "relative"]

DECIMAL_PRECISION = 50
DECIMAL_ROUNDING = decimal.ROUND_HALF_EVEN
# A relative tolerance is a fraction of the expected value and carries this unit.
RELATIVE_TOLERANCE_UNIT = "1"


@dataclass(frozen=True)
class Quantity:
    """One decimal string with its unit."""

    value: str
    unit: str


@dataclass(frozen=True)
class Tolerance:
    """Absolute (in the output's unit) or relative (fraction, unit ``1``)."""

    kind: ToleranceKind
    value: str
    unit: str


@dataclass(frozen=True)
class KatCase:
    """One known-answer case. ``citation`` names the independent source (CALC-REQ-6)."""

    case_id: str
    inputs: Mapping[str, Quantity]
    expected: Mapping[str, Quantity]
    tolerance: Mapping[str, Tolerance]
    citation: str


BackendCompute = Callable[[Mapping[str, Decimal]], Mapping[str, Decimal | str]]


@dataclass(frozen=True)
class FunctionVersion:
    """One catalog function version and its KATs.

    ``route`` is the R route for an R-side version. ``compute`` is the
    backend decimal code for a backend version. ``r_sources`` lists files
    under ``services/r-calculator`` whose bytes are part of an R-side
    version's definition.
    """

    name: str
    version: int
    side: Side
    description: str
    inputs: Mapping[str, str]
    outputs: Mapping[str, str]
    stop_rule: str
    missing_data_rule: str
    kats: Sequence[KatCase]
    defaults: Mapping[str, str] = field(default_factory=dict)
    route: Optional[str] = None
    compute: Optional[BackendCompute] = None
    r_sources: Sequence[str] = ()

    @property
    def key(self) -> tuple[str, int]:
        return (self.name, self.version)


class RCalculationClient(Protocol):
    def execute_calculation_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class BackendKatCalledR(Exception):
    """A backend KAT made an HTTP request. CALC-REQ-5 fails that case."""


def _canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _case_dict(case: KatCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "inputs": {k: {"value": q.value, "unit": q.unit} for k, q in case.inputs.items()},
        "expected": {k: {"value": q.value, "unit": q.unit} for k, q in case.expected.items()},
        "tolerance": {
            k: {"kind": t.kind, "value": t.value, "unit": t.unit} for k, t in case.tolerance.items()
        },
        "citation": case.citation,
    }


def _implementation_text(fv: FunctionVersion, repo_root: Optional[Path]) -> dict[str, str]:
    if fv.side == "backend":
        if fv.compute is None:
            return {}
        return {"compute": inspect.getsource(fv.compute)}
    sources: dict[str, str] = {}
    if fv.r_sources:
        root = repo_root if repo_root is not None else find_repo_root()
        for rel in fv.r_sources:
            data = (root / R_SERVICE_RELATIVE / rel).read_bytes()
            sources[rel] = hashlib.sha256(data).hexdigest()
    return sources


def version_fingerprint(fv: FunctionVersion, repo_root: Optional[Path] = None) -> str:
    """SHA-256 over every declared field, the KATs, and the implementation.

    A change to a formula, default, tolerance, unit, stop rule, or
    missing-data rule changes this value (CALC-REQ-29).
    """
    body = {
        "name": fv.name,
        "version": fv.version,
        "side": fv.side,
        "description": fv.description,
        "inputs": dict(fv.inputs),
        "outputs": dict(fv.outputs),
        "defaults": dict(fv.defaults),
        "stop_rule": fv.stop_rule,
        "missing_data_rule": fv.missing_data_rule,
        "route": fv.route,
        "kats": [_case_dict(c) for c in fv.kats],
        "implementation": _implementation_text(fv, repo_root),
    }
    return hashlib.sha256(_canonical_json(body)).hexdigest()


@dataclass(frozen=True)
class OutputResult:
    name: str
    unit: str
    observed: Optional[str]
    expected: str
    tolerance: Tolerance
    passed: bool


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    function: str
    version: int
    side: Side
    function_fingerprint: str
    citation: str
    passed: bool
    outputs: Sequence[OutputResult]
    error: Optional[str] = None


@dataclass(frozen=True)
class KatRunLog:
    """The record of one KAT run on one lock hash and one built image digest."""

    lock_hash: str
    image_digest: str
    ran_at: str
    cases: Sequence[CaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "lock_hash": self.lock_hash,
            "image_digest": self.image_digest,
            "ran_at": self.ran_at,
            "cases": [
                {
                    "case_id": c.case_id,
                    "function": c.function,
                    "version": c.version,
                    "side": c.side,
                    "function_fingerprint": c.function_fingerprint,
                    "citation": c.citation,
                    "result": "pass" if c.passed else "fail",
                    "error": c.error,
                    "outputs": [
                        {
                            "name": o.name,
                            "unit": o.unit,
                            "observed": o.observed,
                            "expected": o.expected,
                            "tolerance": {
                                "kind": o.tolerance.kind,
                                "value": o.tolerance.value,
                                "unit": o.tolerance.unit,
                            },
                            "result": "pass" if o.passed else "fail",
                        }
                        for o in c.outputs
                    ],
                }
                for c in self.cases
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_dict())).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "KatRunLog":
        cases = []
        for c in data["cases"]:
            outputs = [
                OutputResult(
                    name=o["name"],
                    unit=o["unit"],
                    observed=o["observed"],
                    expected=o["expected"],
                    tolerance=Tolerance(**o["tolerance"]),
                    passed=o["result"] == "pass",
                )
                for o in c["outputs"]
            ]
            cases.append(
                CaseResult(
                    case_id=c["case_id"],
                    function=c["function"],
                    version=int(c["version"]),
                    side=c["side"],
                    function_fingerprint=c["function_fingerprint"],
                    citation=c["citation"],
                    passed=c["result"] == "pass",
                    outputs=outputs,
                    error=c.get("error"),
                )
            )
        return cls(
            lock_hash=data["lock_hash"],
            image_digest=data["image_digest"],
            ran_at=data["ran_at"],
            cases=cases,
        )


def _decimal(text: Any) -> Decimal:
    if not isinstance(text, str):
        raise ValueError(f"{text!r} is not a decimal string")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{text!r} is not a decimal string") from exc
    if not value.is_finite():
        raise ValueError(f"{text!r} is not a finite decimal")
    return value


def _within(observed: Decimal, expected: Decimal, tolerance: Tolerance) -> bool:
    bound = _decimal(tolerance.value)
    if bound < 0:
        raise ValueError("tolerance is negative")
    diff = abs(observed - expected)
    if tolerance.kind == "absolute":
        return diff <= bound
    if tolerance.kind == "relative":
        return diff <= bound * abs(expected)
    raise ValueError(f"unknown tolerance kind {tolerance.kind!r}")


def _case_problem(fv: FunctionVersion, case: KatCase) -> Optional[str]:
    """A declaration problem fails the case before it runs."""
    if not case.citation or not case.citation.strip():
        return "case has no source citation (CALC-REQ-6)"
    if set(case.inputs) != set(fv.inputs):
        return "case inputs do not match the declared inputs"
    if set(case.expected) != set(fv.outputs):
        return "case expected outputs do not match the declared outputs"
    if set(case.tolerance) != set(fv.outputs):
        return "case does not declare a tolerance for every output"
    for name, q in case.inputs.items():
        if q.unit != fv.inputs[name]:
            return f"input {name} unit {q.unit!r} is not the declared unit {fv.inputs[name]!r}"
        try:
            _decimal(q.value)
        except ValueError as exc:
            return f"input {name}: {exc}"
    for name, q in case.expected.items():
        if q.unit != fv.outputs[name]:
            return f"expected {name} unit {q.unit!r} is not the declared unit {fv.outputs[name]!r}"
        try:
            _decimal(q.value)
        except ValueError as exc:
            return f"expected {name}: {exc}"
    for name, tol in case.tolerance.items():
        want = fv.outputs[name] if tol.kind == "absolute" else RELATIVE_TOLERANCE_UNIT
        if tol.unit != want:
            return f"tolerance for {name} must have unit {want!r}"
        try:
            if _decimal(tol.value) < 0:
                return f"tolerance for {name} is negative"
        except ValueError as exc:
            return f"tolerance for {name}: {exc}"
    return None


@contextlib.contextmanager
def no_r_calls() -> Iterator[None]:
    """Any HTTP request in this block raises ``BackendKatCalledR``."""

    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise BackendKatCalledR("backend KAT made an HTTP request")

    original_sync = httpx.Client.send
    original_async = httpx.AsyncClient.send
    httpx.Client.send = refuse  # type: ignore[method-assign]
    httpx.AsyncClient.send = refuse  # type: ignore[method-assign]
    try:
        yield
    finally:
        httpx.Client.send = original_sync  # type: ignore[method-assign]
        httpx.AsyncClient.send = original_async  # type: ignore[method-assign]


def _observe_backend(fv: FunctionVersion, case: KatCase) -> Mapping[str, Any]:
    if fv.compute is None:
        raise ValueError("backend version has no compute")
    inputs = {name: _decimal(q.value) for name, q in case.inputs.items()}
    with decimal.localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = DECIMAL_ROUNDING
        with no_r_calls():
            out = fv.compute(inputs)
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in out.items()}


def _observe_r(
    fv: FunctionVersion,
    case: KatCase,
    r_client: Optional[RCalculationClient],
) -> Mapping[str, Any]:
    if r_client is None:
        raise ValueError("R-side KAT needs the pinned R service client")
    if not fv.route:
        raise ValueError("R-side version has no route")
    payload = {name: q.value for name, q in case.inputs.items()}
    return r_client.execute_calculation_request(fv.route, payload)


def _run_case(
    fv: FunctionVersion,
    fingerprint: str,
    case: KatCase,
    r_client: Optional[RCalculationClient],
) -> CaseResult:
    def result(passed: bool, outputs: list[OutputResult], error: Optional[str]) -> CaseResult:
        return CaseResult(
            case_id=case.case_id,
            function=fv.name,
            version=fv.version,
            side=fv.side,
            function_fingerprint=fingerprint,
            citation=case.citation,
            passed=passed,
            outputs=outputs,
            error=error,
        )

    def unobserved(error: str) -> CaseResult:
        outputs = [
            OutputResult(
                name=name,
                unit=fv.outputs.get(name, q.unit),
                observed=None,
                expected=q.value,
                tolerance=case.tolerance.get(name, Tolerance("absolute", "0", q.unit)),
                passed=False,
            )
            for name, q in case.expected.items()
        ]
        return result(False, outputs, error)

    problem = _case_problem(fv, case)
    if problem is not None:
        return unobserved(problem)
    try:
        if fv.side == "backend":
            observed = _observe_backend(fv, case)
        else:
            observed = _observe_r(fv, case, r_client)
    except BackendKatCalledR as exc:
        return unobserved(f"backend KAT called R: {exc}")
    except CalculationCallRefused as exc:
        return unobserved(f"{exc.code}: {exc.detail}")
    except Exception as exc:  # a stop inside the function fails the case
        return unobserved(f"{type(exc).__name__}: {exc}")

    outputs: list[OutputResult] = []
    errors: list[str] = []
    for name, want in case.expected.items():
        got = observed.get(name) if isinstance(observed, Mapping) else None
        tol = case.tolerance[name]
        try:
            ok = _within(_decimal(got), _decimal(want.value), tol)
        except ValueError as exc:
            errors.append(f"{name}: observed {exc}")
            ok = False
        outputs.append(
            OutputResult(
                name=name,
                unit=fv.outputs[name],
                observed=got if isinstance(got, str) else (None if got is None else repr(got)),
                expected=want.value,
                tolerance=tol,
                passed=ok,
            )
        )
    passed = all(o.passed for o in outputs)
    return result(passed, outputs, "; ".join(errors) or None)


def run_kats(
    versions: Sequence[FunctionVersion],
    *,
    health: Optional[Mapping[str, Any]],
    expected: Optional[ExpectedLock] = None,
    r_client: Optional[RCalculationClient] = None,
    repo_root: Optional[Path] = None,
) -> KatRunLog:
    """Run every KAT of ``versions`` and return the run log.

    ``health`` is the pinned service's ``/health`` body. It must pass the
    CALC-REQ-4 / 4a gate, or no run log is produced (``CalculationCallRefused``).
    The run log's lock hash is the expected lock the gate accepted, and its
    image digest is the one ``/health`` reported.
    """
    lock = begin_calculation_call(health, expected)
    digest = str((health or {})["R_IMAGE_DIGEST"])
    cases: list[CaseResult] = []
    for fv in versions:
        fingerprint = version_fingerprint(fv, repo_root)
        for case in fv.kats:
            cases.append(_run_case(fv, fingerprint, case, r_client))
    return KatRunLog(
        lock_hash=lock.lock_hash,
        image_digest=digest,
        ran_at=datetime.now(timezone.utc).isoformat(),
        cases=cases,
    )
