"""Calculation-scoped, additive, incremental release records (CALC-REQ-7, 29, 33).

A release names the function versions it adds, their KAT case ids, the lock
hash they were proven on, the SHA-256 of that KAT run log, and the earlier
releases it depends on. It never removes or edits a version. The catalog is
code (CALC-REQ-22), so a release record is a committed JSON file written once;
no API route, UI, database row, or agent writes it.

Stop rules:

- CALC-REQ-7: a version is refused unless every one of its KATs has a passing
  result on the release's lock hash, run against the version's current
  definition. A failing case, a missing case, or a run on another lock hash is
  refused. This is a software-release check, not a lab validation gate (§5).
- CALC-REQ-29: a released version is immutable. Releasing it again is refused,
  and a catalog whose definition of a released version no longer matches the
  fingerprint recorded at release (or that drops it) is refused. The same
  change as a new version is allowed.
- CALC-REQ-33: a release only adds versions and names the releases it depends
  on. Every other version, and every earlier record, is left as it was.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from app.services.calculation_kat import FunctionVersion, KatRunLog, version_fingerprint
from app.services.calculation_runtime import expected_lock_from_commit

# The release id is the record's file name.
_RELEASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class ReleaseRefused(Exception):
    """A release or a catalog check is refused. Nothing is written."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ReleasedVersion:
    name: str
    version: int
    fingerprint: str
    kat_case_ids: tuple[str, ...]

    @property
    def key(self) -> tuple[str, int]:
        return (self.name, self.version)


@dataclass(frozen=True)
class ReleaseRecord:
    release_id: str
    lock_hash: str
    kat_run_log_sha256: str
    depends_on: tuple[str, ...]
    adds: tuple[ReleasedVersion, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "lock_hash": self.lock_hash,
            "kat_run_log_sha256": self.kat_run_log_sha256,
            "depends_on": list(self.depends_on),
            "adds": [
                {
                    "name": v.name,
                    "version": v.version,
                    "fingerprint": v.fingerprint,
                    "kat_case_ids": list(v.kat_case_ids),
                }
                for v in self.adds
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReleaseRecord":
        return cls(
            release_id=data["release_id"],
            lock_hash=data["lock_hash"],
            kat_run_log_sha256=data["kat_run_log_sha256"],
            depends_on=tuple(data.get("depends_on", ())),
            adds=tuple(
                ReleasedVersion(
                    name=v["name"],
                    version=int(v["version"]),
                    fingerprint=v["fingerprint"],
                    kat_case_ids=tuple(v["kat_case_ids"]),
                )
                for v in data["adds"]
            ),
        )


def _check_release_id(release_id: str) -> None:
    if not isinstance(release_id, str) or _RELEASE_ID_RE.fullmatch(release_id) is None:
        raise ReleaseRefused(
            "invalid_release_id",
            "release id must be lowercase letters, digits, '.', '_' or '-'",
        )


def released_versions(ledger: Sequence[ReleaseRecord]) -> dict[tuple[str, int], ReleasedVersion]:
    """Every released version, keyed by (name, version). Each is released once."""
    out: dict[tuple[str, int], ReleasedVersion] = {}
    for record in ledger:
        for v in record.adds:
            if v.key in out:
                raise ReleaseRefused(
                    "released_version_immutable",
                    f"{v.name} v{v.version} is released by more than one release",
                )
            out[v.key] = v
    return out


def verify_ledger(ledger: Sequence[ReleaseRecord]) -> None:
    """Release ids are unique, each version is released once, and dependencies exist."""
    ids = [r.release_id for r in ledger]
    if len(ids) != len(set(ids)):
        raise ReleaseRefused("duplicate_release", "two release records share one release id")
    known = set(ids)
    for record in ledger:
        for dep in record.depends_on:
            if dep not in known:
                raise ReleaseRefused(
                    "unknown_dependency",
                    f"release {record.release_id} depends on unknown release {dep}",
                )
    released_versions(ledger)


def verify_catalog(
    ledger: Sequence[ReleaseRecord],
    catalog: Sequence[FunctionVersion],
    repo_root: Optional[Path] = None,
) -> None:
    """Every released version is still in the catalog, unchanged (CALC-REQ-29)."""
    verify_ledger(ledger)
    by_key = {fv.key: fv for fv in catalog}
    for key, released in released_versions(ledger).items():
        fv = by_key.get(key)
        if fv is None:
            raise ReleaseRefused(
                "released_version_removed",
                f"released {key[0]} v{key[1]} is missing from the catalog",
            )
        if version_fingerprint(fv, repo_root) != released.fingerprint:
            raise ReleaseRefused(
                "released_version_edited",
                f"released {key[0]} v{key[1]} was edited; save the change as a new version",
            )


def _kat_refusal(
    fv: FunctionVersion,
    fingerprint: str,
    run_log: KatRunLog,
) -> Optional[ReleaseRefused]:
    label = f"{fv.name} v{fv.version}"
    if not fv.kats:
        return ReleaseRefused("kat_absent", f"{label} has no KATs")
    for case in fv.kats:
        hits = [
            c
            for c in run_log.cases
            if c.function == fv.name
            and c.version == fv.version
            and c.case_id == case.case_id
            and c.function_fingerprint == fingerprint
        ]
        if not hits:
            return ReleaseRefused(
                "kat_absent",
                f"{label} KAT {case.case_id} has no run on lock hash {run_log.lock_hash}",
            )
        if not all(c.passed for c in hits):
            return ReleaseRefused(
                "kat_failed",
                f"{label} KAT {case.case_id} failed on lock hash {run_log.lock_hash}",
            )
    return None


def prepare_release(
    release_id: str,
    adds: Sequence[tuple[str, int]],
    *,
    catalog: Sequence[FunctionVersion],
    ledger: Sequence[ReleaseRecord],
    run_log: Optional[KatRunLog],
    lock_hash: Optional[str] = None,
    depends_on: Sequence[str] = (),
    repo_root: Optional[Path] = None,
) -> ReleaseRecord:
    """Check a release and return its record, or raise ``ReleaseRefused``.

    ``lock_hash`` defaults to the lock recomputed from the commit.
    """
    lock = lock_hash if lock_hash is not None else expected_lock_from_commit(repo_root).lock_hash
    verify_catalog(ledger, catalog, repo_root)
    _check_release_id(release_id)
    if release_id in {r.release_id for r in ledger}:
        raise ReleaseRefused("duplicate_release", f"release id {release_id!r} is taken")
    known = {r.release_id for r in ledger}
    for dep in depends_on:
        if dep not in known:
            raise ReleaseRefused("unknown_dependency", f"depends on unknown release {dep}")
    if not adds:
        raise ReleaseRefused("empty_release", "a release adds at least one function version")
    if len(set(adds)) != len(adds):
        raise ReleaseRefused("duplicate_version", "a release names one version twice")

    by_key = {fv.key: fv for fv in catalog}
    released = released_versions(ledger)
    entries: list[ReleasedVersion] = []
    for name, version in adds:
        key = (name, int(version))
        if key in released:
            raise ReleaseRefused(
                "released_version_immutable",
                f"{name} v{version} is already released; a change is a new version",
            )
        fv = by_key.get(key)
        if fv is None:
            raise ReleaseRefused("unknown_version", f"{name} v{version} is not in the catalog")
        if run_log is None:
            raise ReleaseRefused("kat_absent", f"{name} v{version} has no KAT run on lock hash {lock}")
        if run_log.lock_hash != lock:
            raise ReleaseRefused(
                "kat_absent",
                f"{name} v{version} has no KAT run on lock hash {lock} "
                f"(run log is on {run_log.lock_hash})",
            )
        fingerprint = version_fingerprint(fv, repo_root)
        refused = _kat_refusal(fv, fingerprint, run_log)
        if refused is not None:
            raise refused
        entries.append(
            ReleasedVersion(
                name=name,
                version=int(version),
                fingerprint=fingerprint,
                kat_case_ids=tuple(c.case_id for c in fv.kats),
            )
        )
    return ReleaseRecord(
        release_id=release_id,
        lock_hash=lock,
        kat_run_log_sha256=run_log.sha256() if run_log is not None else "",
        depends_on=tuple(depends_on),
        adds=tuple(entries),
    )


def write_release(ledger_dir: Path, record: ReleaseRecord) -> Path:
    """Write ``<release_id>.json`` once. An existing record is never replaced."""
    _check_release_id(record.release_id)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / f"{record.release_id}.json"
    try:
        with path.open("x", encoding="utf-8") as fh:
            json.dump(record.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")
    except FileExistsError as exc:
        raise ReleaseRefused(
            "duplicate_release",
            f"release record {path.name} already exists and is not replaced",
        ) from exc
    return path


def load_ledger(ledger_dir: Path) -> list[ReleaseRecord]:
    if not ledger_dir.is_dir():
        return []
    return [
        ReleaseRecord.from_dict(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(ledger_dir.glob("*.json"))
    ]
