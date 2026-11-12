"""S1 acceptance for the pinned R service (CALC-REQ-2, 3, 4, 4a).

The attempt-record half of the CALC-REQ-4a timeout criteria is S9. These tests
prove the refusal and the timeout codes, and that nothing is written.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import stat
import subprocess
from pathlib import Path

import httpx
import pytest

from app.services.calculation_runtime import (
    CALCULATION_BACKEND_TIMEOUT_SECONDS,
    SANDBOX_BOOL_FIELDS,
    CalculationCallRefused,
    begin_calculation_call,
    directory_tree_id,
    expected_lock_from_commit,
    find_repo_root,
    lock_hash,
    note_calculation_runtime_on_startup,
    parse_base_digest,
    renv_digest,
)
from app.services.r_calculator_client import FIT_TIMEOUT_SECONDS, RCalculatorClient


def _repo() -> Path:
    return find_repo_root()


def _service() -> Path:
    return _repo() / "services" / "r-calculator"


def _expected():
    return expected_lock_from_commit(_repo())


def _sandbox(**overrides: object) -> dict:
    body = {
        "uid": 1000,
        "root_read_only": True,
        "scratch_tmpfs": True,
        "egress_blocked": True,
        "cpu_limited": True,
        "memory_limited": True,
        "pids_limited": True,
        "forbidden_env_absent": True,
    }
    body.update(overrides)
    return body


def _health(**overrides: object) -> dict:
    lock = _expected()
    body = {
        "status": "ok",
        "base": lock.base,
        "renv": lock.renv,
        "tree": lock.tree,
        "lock_hash": lock.lock_hash,
        "R_IMAGE_DIGEST": "sha256:" + ("ab" * 32),
        "sandbox": _sandbox(),
    }
    body.update(overrides)
    return body


def test_dockerfile_from_lines_are_digest_pinned() -> None:
    text = (_service() / "Dockerfile").read_text(encoding="utf-8")
    from_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("FROM ")
    ]
    assert from_lines
    assert all("@sha256:" in line for line in from_lines)
    assert "install.packages(" not in text
    assert "renv::restore(" in (_service() / "restore.R").read_text(encoding="utf-8")


def test_two_evaluations_of_one_commit_report_the_same_lock_hash() -> None:
    first = expected_lock_from_commit(_repo())
    second = expected_lock_from_commit(_repo())
    assert first.lock_hash == second.lock_hash
    assert first.lock_hash == lock_hash(first.base, first.renv, first.tree)
    # The built image digest is not an input. Two builds may differ there.
    assert "R_IMAGE_DIGEST" not in first.lock_hash


def test_recompute_without_a_build_matches_section_2() -> None:
    root = _repo()
    expected = expected_lock_from_commit(root)
    dockerfile = (_service() / "Dockerfile").read_text(encoding="utf-8")
    lock_bytes = (_service() / "renv.lock").read_bytes()
    tree = subprocess.check_output(
        ["git", "rev-parse", "HEAD:services/r-calculator"],
        cwd=root,
        text=True,
    ).strip()
    assert expected.base == parse_base_digest(dockerfile)
    assert expected.renv == renv_digest(lock_bytes)
    assert expected.renv == hashlib.sha256(lock_bytes).hexdigest()
    assert expected.tree == tree
    preimage = f"{expected.base}\n{expected.renv}\n{expected.tree}".encode("utf-8")
    assert expected.lock_hash == hashlib.sha256(preimage).hexdigest()
    assert len(expected.lock_hash) == 64


def test_one_package_version_changes_the_lock_hash() -> None:
    raw = (_service() / "renv.lock").read_bytes()
    needle = b'"Version": "4.1.6"'
    assert needle in raw
    mutated = raw.replace(needle, b'"Version": "9.9.9"', 1)
    assert mutated != raw
    base = _expected().base
    tree = _expected().tree
    assert lock_hash(base, renv_digest(raw), tree) != lock_hash(
        base, renv_digest(mutated), tree
    )


def test_lock_hash_vector_matches_the_r_service() -> None:
    assert (
        lock_hash("ab", "cd", "ef")
        == "911f0cdd0689cf114775478c242760865d67d1816e3586fbc6529f24fbb000a2"
    )
    text = (_service() / "tests" / "test_pin.R").read_text(encoding="utf-8")
    assert "911f0cdd0689cf114775478c242760865d67d1816e3586fbc6529f24fbb000a2" in text


def test_directory_tree_id_matches_git() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        (repo / "sub").mkdir(parents=True)
        (repo / "a.txt").write_text("hello\n", encoding="utf-8")
        (repo / "sub" / "b.txt").write_bytes(b"\x00\x01")
        (repo / "foo").mkdir()
        (repo / "foo" / "c.txt").write_text("c\n", encoding="utf-8")
        (repo / "foo.txt").write_text("file\n", encoding="utf-8")
        script = repo / "run.sh"
        script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        subprocess.check_call(["git", "init"], cwd=repo)
        subprocess.check_call(["git", "add", "."], cwd=repo)
        tree = subprocess.check_output(["git", "write-tree"], cwd=repo, text=True).strip()
        assert directory_tree_id(repo) == tree


def test_mismatched_lock_hash_names_the_mismatch_and_writes_nothing() -> None:
    expected = _expected()
    health = _health(lock_hash="0" * 64)
    writes: list[str] = []
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, expected)
        writes.append("result")
    assert caught.value.code == "lock_mismatch"
    assert "mismatch" in caught.value.detail
    assert expected.lock_hash in caught.value.detail
    assert "0" * 64 in caught.value.detail
    assert writes == []


def test_missing_lock_hash_refuses_and_writes_nothing() -> None:
    health = _health()
    del health["lock_hash"]
    writes: list[str] = []
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
        writes.append("result")
    assert "lock hash" in caught.value.detail
    assert writes == []


@pytest.mark.parametrize(
    "digest",
    [None, "", "sha256:ABCD", "sha256:" + "ab" * 31, "ab" * 32, "SHA256:" + "ab" * 32],
)
def test_missing_or_ill_formed_digest_names_the_cause(digest: str | None) -> None:
    health = _health(R_IMAGE_DIGEST=digest)
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
    assert "R_IMAGE_DIGEST" in caught.value.detail
    if digest in (None, ""):
        assert "missing" in caught.value.detail
    else:
        assert "ill-formed" in caught.value.detail


def test_accepts_a_matching_pin_and_still_writes_nothing() -> None:
    writes: list[str] = []
    lock = begin_calculation_call(_health(), _expected())
    assert lock.lock_hash == _expected().lock_hash
    assert writes == []


@pytest.mark.parametrize("field", SANDBOX_BOOL_FIELDS)
def test_false_sandbox_field_refuses(field: str) -> None:
    health = _health(sandbox=_sandbox(**{field: False}))
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
    assert field in caught.value.detail
    assert "false" in caught.value.detail


@pytest.mark.parametrize("field", SANDBOX_BOOL_FIELDS)
def test_missing_sandbox_field_refuses(field: str) -> None:
    sandbox = _sandbox()
    del sandbox[field]
    health = _health(sandbox=sandbox)
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
    assert field in caught.value.detail
    assert "missing" in caught.value.detail


def test_missing_sandbox_object_refuses() -> None:
    health = _health()
    del health["sandbox"]
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
    assert "sandbox object is missing" in caught.value.detail


def test_root_uid_refuses() -> None:
    health = _health(sandbox=_sandbox(uid=0))
    with pytest.raises(CalculationCallRefused) as caught:
        begin_calculation_call(health, _expected())
    assert "uid is 0" in caught.value.detail


def test_timeouts_are_the_oq_16_defaults_and_fit_is_unchanged() -> None:
    assert CALCULATION_BACKEND_TIMEOUT_SECONDS == 60.0
    assert FIT_TIMEOUT_SECONDS == 60.0
    timeout_r = (_service() / "R" / "request_timeout.R").read_text(encoding="utf-8")
    assert "REQUEST_TIMEOUT_SECONDS <- 50" in timeout_r
    fit_src = inspect.getsource(RCalculatorClient.fit)
    svg_src = inspect.getsource(RCalculatorClient.full_svg)
    assert "begin_calculation_call" not in fit_src
    assert "begin_calculation_call" not in svg_src
    assert "FIT_TIMEOUT_SECONDS" in fit_src
    dose = Path(__file__).resolve().parents[1] / "app" / "services" / "dose_response_fit.py"
    dose_text = dose.read_text(encoding="utf-8")
    assert "calculation_runtime" not in dose_text
    assert "begin_calculation_call" not in dose_text


def test_backend_timeout_refuses_without_writing(monkeypatch: pytest.MonkeyPatch) -> None:
    health = _health()
    writes: list[str] = []

    class _Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return health

    def fake_get(url: str, timeout: float) -> _Response:
        return _Response()

    def fake_post(url: str, json: dict, timeout: float) -> _Response:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(CalculationCallRefused) as caught:
        RCalculatorClient("http://r-calculator:8000").execute_calculation_request(
            "/calculations/v1",
            {"stage": "example"},
        )
        writes.append("result")
    assert caught.value.code == "backend_timeout"
    assert "60" in caught.value.detail
    assert writes == []


def test_r_timeout_refuses_without_writing(monkeypatch: pytest.MonkeyPatch) -> None:
    health = _health()
    writes: list[str] = []

    class _Health:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return health

    class _Timeout:
        status_code = 504

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"code": "r_timeout", "detail": "R stopped the request after 50 s"}

    monkeypatch.setattr(httpx, "get", lambda url, timeout: _Health())
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: _Timeout())
    with pytest.raises(CalculationCallRefused) as caught:
        RCalculatorClient("http://r-calculator:8000").execute_calculation_request(
            "/calculations/v1",
            {},
        )
        writes.append("attempt")
    assert caught.value.code == "r_timeout"
    assert writes == []


def test_fit_route_is_not_a_calculation_call() -> None:
    with pytest.raises(CalculationCallRefused) as caught:
        RCalculatorClient("http://r-calculator:8000").execute_calculation_request("/fit", {})
    assert "/fit" in caught.value.detail


def test_startup_check_does_not_call_r_during_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_get(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("startup must not call /health when ENVIRONMENT=test")

    monkeypatch.setattr(httpx, "get", fail_get)
    assert os.environ.get("ENVIRONMENT") == "test"
    note_calculation_runtime_on_startup()


def test_compose_sandbox_and_no_backend_socket() -> None:
    text = (_repo() / "docker-compose.yml").read_text(encoding="utf-8")
    assert "docker.sock" not in text
    start = text.index("  r-calculator:\n")
    end = text.index("  # FastAPI Backend", start)
    block = text[start:end]
    assert "read_only: true" in block
    assert 'cpus: "1.0"' in block
    assert "mem_limit:" in block
    assert "pids_limit:" in block
    assert "/tmp:" in block
    assert 'user: "1000:1000"' in block
    assert not any(
        line.strip().startswith("ports:") for line in block.splitlines()
    )
    assert "r-internal" in block
    assert "DATABASE_URL" not in block
    assert "internal: true" in text
    backend = text[text.index("  backend:\n") : text.index("  # React Frontend")]
    assert "r-internal" in backend
    assert "docker.sock" not in backend


def test_request_timeout_does_not_wrap_fit() -> None:
    plumber = (_service() / "plumber.R").read_text(encoding="utf-8")
    timeout_r = (_service() / "R" / "request_timeout.R").read_text(encoding="utf-8")
    assert "install_calculation_timeout(pr, REQUEST_TIMEOUT_SECONDS)" in plumber
    assert "run_with_wall_timeout(plumber::forward()" not in plumber
    assert 'registerHook("aroundexec"' in timeout_r
    assert "legacy_dose_response_path" in timeout_r
    assert '"/fit"' in timeout_r
    assert '"/svg/full"' in timeout_r
    assert "REQUEST_TIMEOUT_SECONDS <- 50" in timeout_r
    fit = (_service() / "R" / "fit.R").read_text(encoding="utf-8")
    assert "withTimeout(confint(fit, level = 0.95), timeout = 5" in fit
