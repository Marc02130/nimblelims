"""Expected R lock hash and the calculation-call gate (CALC-REQ-2, 3, 4, 4a).

The backend recomputes the Spec §2 lock hash from the commit: the base digest
in the Dockerfile ``FROM`` line, the SHA-256 of ``renv.lock``, and the git
tree id of ``services/r-calculator``. It does not build the image and it does
not talk to Docker.

S1 has no calculation-attempt store and writes no result. A refusal raises
``CalculationCallRefused`` and returns before any write. Recording
``r_timeout`` / ``backend_timeout`` on an attempt is S9. Dose-response
``POST /fit`` and ``POST /svg/full`` do not enter this gate.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

R_SERVICE_RELATIVE = Path("services") / "r-calculator"
# OQ-CALC-16 default. R stops at 50 s; this wait is longer so a silent R
# process is ``backend_timeout``. Shipped ``FIT_TIMEOUT_SECONDS`` stays 60
# for dose-response and is not this constant.
CALCULATION_BACKEND_TIMEOUT_SECONDS = 60.0

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_TREE_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_FROM_RE = re.compile(r"^FROM\s+\S+@sha256:([0-9a-f]{64})(?:\s|$)")

SANDBOX_BOOL_FIELDS = (
    "root_read_only",
    "scratch_tmpfs",
    "egress_blocked",
    "cpu_limited",
    "memory_limited",
    "pids_limited",
    "forbidden_env_absent",
)


class CalculationCallRefused(Exception):
    """A calculation call is refused before any attempt or result is written."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ExpectedLock:
    """The §2 preimage fields and the lock hash a calculation call must match."""

    base: str
    renv: str
    tree: str
    lock_hash: str


def lock_hash(base: str, renv: str, tree: str) -> str:
    """SHA-256 of ``<base>\\n<renv>\\n<tree>`` with no trailing LF."""
    preimage = f"{base}\n{renv}\n{tree}".encode("utf-8")
    return hashlib.sha256(preimage).hexdigest()


def renv_digest(lock_bytes: bytes) -> str:
    """SHA-256 of the raw bytes of ``renv.lock``."""
    return hashlib.sha256(lock_bytes).hexdigest()


def parse_base_digest(dockerfile_text: str) -> str:
    """The 64-hex digest from the first ``FROM <image>@sha256:<digest>`` line.

    Every ``FROM`` line must carry a digest (CALC-REQ-2). ``<base>`` is that
    pinned base image, not the built service image.
    """
    digests: list[str] = []
    for raw in dockerfile_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("FROM "):
            continue
        match = _FROM_RE.match(line)
        if match is None:
            raise CalculationCallRefused(
                "lock_hash",
                "Dockerfile FROM line has no @sha256: digest",
            )
        digests.append(match.group(1))
    if not digests:
        raise CalculationCallRefused(
            "lock_hash",
            "Dockerfile has no FROM line to supply the base digest",
        )
    return digests[0]


def find_repo_root() -> Path:
    """Directory that contains ``services/r-calculator/renv.lock``."""
    env = os.environ.get("NIMBLELIMS_REPO_ROOT")
    if env:
        root = Path(env)
        if (root / R_SERVICE_RELATIVE / "renv.lock").is_file():
            return root
        raise CalculationCallRefused(
            "lock_hash",
            "NIMBLELIMS_REPO_ROOT does not contain services/r-calculator/renv.lock",
        )
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / R_SERVICE_RELATIVE / "renv.lock").is_file():
            return parent
    raise CalculationCallRefused(
        "lock_hash",
        "Cannot recompute the lock hash: services/r-calculator/renv.lock is not in this tree",
    )


def _git_blob(data: bytes) -> bytes:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).digest()


def _git_tree(entries: list[tuple[str, str, bytes]]) -> bytes:
    """Git tree object. Directories sort as if the name had a trailing slash."""

    def sort_key(item: tuple[str, str, bytes]) -> bytes:
        mode, name, _sha = item
        raw = name.encode("utf-8")
        if mode == "40000":
            return raw + b"/"
        return raw

    body = b"".join(
        mode.encode("ascii") + b" " + name.encode("utf-8") + b"\0" + sha
        for mode, name, sha in sorted(entries, key=sort_key)
    )
    header = f"tree {len(body)}\0".encode("ascii")
    return hashlib.sha1(header + body).digest()


def directory_tree_id(path: Path) -> str:
    """Git tree id of ``path``, matching ``git rev-parse <commit>:<path>`` when the bytes match the commit."""

    def hash_path(node: Path) -> tuple[str, bytes]:
        if node.is_symlink():
            target = os.readlink(node).encode("utf-8")
            return "120000", _git_blob(target)
        if node.is_dir():
            entries: list[tuple[str, str, bytes]] = []
            for child in node.iterdir():
                if child.name == ".git":
                    continue
                mode, sha = hash_path(child)
                entries.append((mode, child.name, sha))
            return "40000", _git_tree(entries)
        mode = "100755" if node.stat().st_mode & stat.S_IXUSR else "100644"
        return mode, _git_blob(node.read_bytes())

    _mode, sha = hash_path(path)
    return sha.hex()


def git_tree_id(repo_root: Path, commit: str = "HEAD") -> str:
    """``git rev-parse <commit>:services/r-calculator`` (Spec §2)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", f"{commit}:services/r-calculator"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CalculationCallRefused(
            "lock_hash",
            f"Cannot recompute the git tree id of services/r-calculator: {exc}",
        ) from exc
    tree = out.stdout.strip()
    if _TREE_RE.fullmatch(tree) is None:
        raise CalculationCallRefused(
            "lock_hash",
            "git rev-parse did not return a tree id for services/r-calculator",
        )
    return tree


def tree_id_for_commit(repo_root: Path, commit: str = "HEAD") -> str:
    """Tree id from git when the commit is present, else from the directory bytes.

    The image has no ``.git``. ``directory_tree_id`` is the same id when the
    copied files are the commit. Tests check that equality.
    """
    git_dir = repo_root / ".git"
    if git_dir.exists():
        return git_tree_id(repo_root, commit)
    return directory_tree_id(repo_root / R_SERVICE_RELATIVE)


def expected_lock_from_commit(
    repo_root: Path | None = None,
    commit: str = "HEAD",
) -> ExpectedLock:
    """Recompute the §2 lock hash from the commit. No image build."""
    root = repo_root if repo_root is not None else find_repo_root()
    dockerfile_path = root / R_SERVICE_RELATIVE / "Dockerfile"
    lock_path = root / R_SERVICE_RELATIVE / "renv.lock"
    if not dockerfile_path.is_file() or not lock_path.is_file():
        raise CalculationCallRefused(
            "lock_hash",
            "Cannot recompute the lock hash: Dockerfile or renv.lock is missing",
        )
    base = parse_base_digest(dockerfile_path.read_text(encoding="utf-8"))
    renv = renv_digest(lock_path.read_bytes())
    tree = tree_id_for_commit(root, commit)
    return ExpectedLock(
        base=base,
        renv=renv,
        tree=tree,
        lock_hash=lock_hash(base, renv, tree),
    )


def _sandbox_refusal(sandbox: Any) -> CalculationCallRefused | None:
    if not isinstance(sandbox, Mapping):
        return CalculationCallRefused("sandbox", "sandbox object is missing")
    if "uid" not in sandbox or sandbox.get("uid") is None:
        return CalculationCallRefused("sandbox", "sandbox field uid is missing")
    uid = sandbox.get("uid")
    if isinstance(uid, bool) or not isinstance(uid, int):
        return CalculationCallRefused("sandbox", "sandbox field uid is missing")
    if uid == 0:
        return CalculationCallRefused("sandbox", "sandbox uid is 0")
    for field in SANDBOX_BOOL_FIELDS:
        if field not in sandbox or sandbox.get(field) is None:
            return CalculationCallRefused(
                "sandbox",
                f"sandbox field {field} is missing",
            )
        value = sandbox.get(field)
        if value is False:
            return CalculationCallRefused(
                "sandbox",
                f"sandbox field {field} is false",
            )
        if value is not True:
            return CalculationCallRefused(
                "sandbox",
                f"sandbox field {field} is missing",
            )
    return None


def refusal_for_health(
    health: Mapping[str, Any] | None,
    expected: ExpectedLock,
) -> CalculationCallRefused | None:
    """CALC-REQ-4 and CALC-REQ-4a stop rules. None means the call may proceed."""
    if not isinstance(health, Mapping):
        return CalculationCallRefused(
            "lock_hash",
            "/health did not report a lock hash",
        )
    reported = health.get("lock_hash")
    if not isinstance(reported, str) or _HEX64_RE.fullmatch(reported) is None:
        return CalculationCallRefused(
            "lock_hash",
            "/health did not report a lock hash",
        )
    if reported != expected.lock_hash:
        return CalculationCallRefused(
            "lock_mismatch",
            "lock hash mismatch: reported "
            f"{reported} does not equal expected {expected.lock_hash}",
        )
    digest = health.get("R_IMAGE_DIGEST", None)
    if digest is None or digest == "":
        return CalculationCallRefused(
            "missing_digest",
            "built image digest missing: R_IMAGE_DIGEST is unset",
        )
    if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
        return CalculationCallRefused(
            "ill_formed_digest",
            "built image digest ill-formed: R_IMAGE_DIGEST must be "
            "sha256: followed by 64 lowercase hex digits",
        )
    return _sandbox_refusal(health.get("sandbox"))


def begin_calculation_call(
    health: Mapping[str, Any] | None,
    expected: ExpectedLock | None = None,
) -> ExpectedLock:
    """Accept or refuse one calculation call.

    Does not write an attempt or a result. On acceptance, returns the expected
    lock so a later slice can record it. S1 has nothing further to run.
    """
    lock = expected if expected is not None else expected_lock_from_commit()
    refused = refusal_for_health(health, lock)
    if refused is not None:
        raise refused
    return lock


def note_calculation_runtime_on_startup() -> None:
    """Check the lock and sandbox when the API process starts.

    A refusal is logged and calculation calls stay closed. The process keeps
    serving every other route, including dose-response ``POST /fit``. Tests
    set ``ENVIRONMENT=test`` and skip the live ``/health`` call.
    """
    if os.environ.get("ENVIRONMENT") == "test":
        logger.info("calculation runtime startup check skipped when ENVIRONMENT=test")
        return
    try:
        expected = expected_lock_from_commit()
    except CalculationCallRefused as exc:
        logger.error("calculation runtime startup refusal: %s", exc.detail)
        return
    except Exception:
        logger.exception("calculation runtime startup could not recompute the lock hash")
        return
    try:
        from app.services.r_calculator_client import RCalculatorClient

        health = RCalculatorClient().fetch_health_body()
    except Exception as exc:
        logger.error(
            "calculation runtime startup refusal: /health did not report a lock hash (%s)",
            exc,
        )
        return
    try:
        begin_calculation_call(health, expected)
    except CalculationCallRefused as exc:
        logger.error("calculation runtime startup refusal: %s", exc.detail)
        return
    logger.info(
        "calculation runtime lock and sandbox accepted at startup lock_hash=%s",
        expected.lock_hash,
    )
