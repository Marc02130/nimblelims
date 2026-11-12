"""S2 release record acceptance (CALC-REQ-7, CALC-REQ-29, CALC-REQ-33).

Harness fixtures only. The functions here are ``harness_fixture_*`` versions,
not catalog functions, and the ledger is a temporary directory.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.services.calculation_kat import FunctionVersion, KatRunLog, run_kats
from app.services.calculation_release import (
    ReleaseRecord,
    ReleaseRefused,
    load_ledger,
    prepare_release,
    released_versions,
    verify_catalog,
    write_release,
)
from app.services.calculation_runtime import expected_lock_from_commit, find_repo_root
from tests.fixtures import calculation_kat_harness as hf
from tests.test_calculation_kat_s2 import _health

LOCK = expected_lock_from_commit(find_repo_root()).lock_hash
OTHER_LOCK = "f" * 64


def _run(*versions: FunctionVersion) -> KatRunLog:
    return run_kats(list(versions), health=_health())


def _release(
    ledger_dir: Path,
    release_id: str,
    adds: list[tuple[str, int]],
    catalog: list[FunctionVersion],
    run_log: KatRunLog | None,
    **kwargs: Any,
) -> ReleaseRecord:
    record = prepare_release(
        release_id,
        adds,
        catalog=catalog,
        ledger=load_ledger(ledger_dir),
        run_log=run_log,
        **kwargs,
    )
    write_release(ledger_dir, record)
    return record


def _snapshot(ledger_dir: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(ledger_dir.glob("*.json"))}


# CALC-REQ-7 -----------------------------------------------------------------


def test_release_with_passing_kats_on_the_lock_is_accepted(tmp_path: Path) -> None:
    fv = hf.backend_sum()
    log = _run(fv)
    record = _release(tmp_path, "r1", [fv.key], [fv], log)
    assert record.lock_hash == LOCK
    assert record.kat_run_log_sha256 == log.sha256()
    assert record.adds[0].kat_case_ids == ("hf-sum-exact",)
    assert [r.release_id for r in load_ledger(tmp_path)] == ["r1"]


def test_release_with_a_failing_kat_is_refused(tmp_path: Path) -> None:
    fv = hf.backend_sum(kats=(hf.sum_case(), hf.failing_sum_case()))
    log = _run(fv)
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [fv.key], [fv], log)
    assert caught.value.code == "kat_failed"
    assert "hf-sum-deliberately-wrong" in caught.value.detail
    assert _snapshot(tmp_path) == {}


@pytest.mark.parametrize("absent", ["no_run_log", "version_not_run", "other_lock", "no_kats"])
def test_release_with_an_absent_kat_run_is_refused(tmp_path: Path, absent: str) -> None:
    fv = hf.backend_sum()
    catalog = [fv]
    log: KatRunLog | None = _run(fv)
    if absent == "no_run_log":
        log = None
    elif absent == "version_not_run":
        other = hf.backend_sum(name="harness_fixture_backend_other")
        catalog = [fv, other]
        log = _run(other)
    elif absent == "other_lock":
        assert log is not None
        log = replace(log, lock_hash=OTHER_LOCK)
    elif absent == "no_kats":
        fv = hf.backend_sum(kats=())
        catalog = [fv]
        log = _run(fv)
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [fv.key], catalog, log)
    assert caught.value.code == "kat_absent"
    assert _snapshot(tmp_path) == {}


def test_release_on_a_lock_without_a_run_is_refused_even_if_another_lock_passed(
    tmp_path: Path,
) -> None:
    fv = hf.backend_sum()
    log = _run(fv)
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [fv.key], [fv], log, lock_hash=OTHER_LOCK)
    assert caught.value.code == "kat_absent"
    assert OTHER_LOCK in caught.value.detail


def test_a_run_on_an_older_definition_is_absent_for_the_edited_one(tmp_path: Path) -> None:
    old = hf.backend_sum()
    log = _run(old)
    edited = replace(old, stop_rule="stop when a is negative")
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [edited.key], [edited], log)
    assert caught.value.code == "kat_absent"


def test_one_failing_version_refuses_the_whole_release(tmp_path: Path) -> None:
    good = hf.backend_sum(name="harness_fixture_backend_good")
    bad = hf.backend_sum(name="harness_fixture_backend_bad", kats=(hf.failing_sum_case(),))
    log = _run(good, bad)
    with pytest.raises(ReleaseRefused):
        _release(tmp_path, "r1", [good.key, bad.key], [good, bad], log)
    assert _snapshot(tmp_path) == {}


# CALC-REQ-29 ----------------------------------------------------------------


def test_edit_to_a_released_version_is_refused_and_a_new_version_succeeds(tmp_path: Path) -> None:
    v1 = hf.backend_sum(version=1)
    _release(tmp_path, "r1", [v1.key], [v1], _run(v1))
    before = _snapshot(tmp_path)
    fp_v1 = released_versions(load_ledger(tmp_path))[v1.key].fingerprint

    change = {"description": "total = a + b, in decimal, as one sum"}
    edited_v1 = replace(v1, **change)

    with pytest.raises(ReleaseRefused) as caught:
        verify_catalog(load_ledger(tmp_path), [edited_v1])
    assert caught.value.code == "released_version_edited"

    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r2", [edited_v1.key], [edited_v1], _run(edited_v1))
    assert caught.value.code == "released_version_edited"

    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r2", [v1.key], [v1], _run(v1))
    assert caught.value.code == "released_version_immutable"
    assert _snapshot(tmp_path) == before

    v2 = replace(v1, version=2, **change)
    record = _release(tmp_path, "r2", [v2.key], [v1, v2], _run(v2), depends_on=["r1"])
    assert record.adds[0].key == ("harness_fixture_backend_sum", 2)

    after = _snapshot(tmp_path)
    assert after["r1.json"] == before["r1.json"]
    versions = released_versions(load_ledger(tmp_path))
    assert versions[v1.key].fingerprint == fp_v1
    assert set(versions) == {v1.key, v2.key}
    verify_catalog(load_ledger(tmp_path), [v1, v2])


@pytest.mark.parametrize(
    "field,value",
    [
        ("description", "total = b + a"),
        ("defaults", {"a": "0"}),
        ("stop_rule", "stop when a is negative"),
        ("missing_data_rule", "a missing a is 0"),
        ("inputs", {"a": "mg", "b": "1"}),
        ("kats", (hf.sum_case(tolerance=hf.Tolerance("absolute", "0.001", "1")),)),
        ("compute", hf.harness_sum_calls_r),
    ],
)
def test_every_kind_of_edit_to_a_released_version_is_refused(
    tmp_path: Path, field: str, value: Any
) -> None:
    v1 = hf.backend_sum()
    _release(tmp_path, "r1", [v1.key], [v1], _run(v1))
    with pytest.raises(ReleaseRefused) as caught:
        verify_catalog(load_ledger(tmp_path), [replace(v1, **{field: value})])
    assert caught.value.code == "released_version_edited"


def test_removing_a_released_version_is_refused(tmp_path: Path) -> None:
    v1 = hf.backend_sum()
    _release(tmp_path, "r1", [v1.key], [v1], _run(v1))
    with pytest.raises(ReleaseRefused) as caught:
        verify_catalog(load_ledger(tmp_path), [])
    assert caught.value.code == "released_version_removed"


def test_a_release_record_is_never_replaced(tmp_path: Path) -> None:
    v1 = hf.backend_sum()
    record = _release(tmp_path, "r1", [v1.key], [v1], _run(v1))
    before = _snapshot(tmp_path)
    with pytest.raises(ReleaseRefused) as caught:
        write_release(tmp_path, record)
    assert caught.value.code == "duplicate_release"
    v2 = replace(v1, version=2)
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [v2.key], [v1, v2], _run(v2))
    assert caught.value.code == "duplicate_release"
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("release_id", ["", "../escape", "Upper", "a/b"])
def test_release_id_is_a_plain_file_name(tmp_path: Path, release_id: str) -> None:
    v1 = hf.backend_sum()
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, release_id, [v1.key], [v1], _run(v1))
    assert caught.value.code == "invalid_release_id"


# CALC-REQ-33 ----------------------------------------------------------------


def test_a_new_version_of_one_function_leaves_every_other_version_unchanged(
    tmp_path: Path,
) -> None:
    a1 = hf.backend_sum(name="harness_fixture_backend_a")
    b1 = hf.backend_sum(name="harness_fixture_backend_b")
    r1 = hf.r_round_trip(version=1)
    catalog = [a1, b1]
    _release(tmp_path, "rel-a1", [a1.key], catalog, _run(a1))
    _release(tmp_path, "rel-b1", [b1.key], catalog, _run(b1))
    before = _snapshot(tmp_path)
    versions_before = released_versions(load_ledger(tmp_path))

    a2 = replace(a1, version=2, description="total = a + b, second harness version")
    catalog_after = [a1, b1, a2, r1]
    record = _release(
        tmp_path, "rel-a2", [a2.key], catalog_after, _run(a2), depends_on=["rel-a1"]
    )

    assert [v.key for v in record.adds] == [a2.key]
    assert record.depends_on == ("rel-a1",)
    after = _snapshot(tmp_path)
    assert {k: after[k] for k in before} == before
    versions_after = released_versions(load_ledger(tmp_path))
    for key, released in versions_before.items():
        assert versions_after[key] == released
    assert set(versions_after) == set(versions_before) | {a2.key}
    # The unreleased R fixture version stays unreleased.
    assert r1.key not in versions_after
    verify_catalog(load_ledger(tmp_path), catalog_after)


def test_a_release_naming_an_unknown_release_is_refused(tmp_path: Path) -> None:
    v1 = hf.backend_sum()
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [v1.key], [v1], _run(v1), depends_on=["missing"])
    assert caught.value.code == "unknown_dependency"
    assert _snapshot(tmp_path) == {}


def test_an_empty_release_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReleaseRefused) as caught:
        _release(tmp_path, "r1", [], [], _run())
    assert caught.value.code == "empty_release"
