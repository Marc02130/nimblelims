"""Fail when server code writes a naive UTC clock.

Instant columns are ``timestamptz``. A write must be timezone-aware
(``datetime.now(timezone.utc)`` or a SQL ``now()`` default). ``datetime.utcnow``
and ``datetime.now()`` with no timezone are naive. ``replace(tzinfo=None)``
strips the offset before the value is stored.

The scan covers ``backend/app``, ``backend/models``, top-level backend
scripts, and ``backend/scripts``. It does not scan ``backend/tests``:
fixtures still build naive datetimes for calendar columns such as
``start_date`` and ``received_date``. It does not scan ``backend/db/migrations``:
already-applied revisions inserted naive timestamps while those columns were
still ``timestamp without time zone``.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

Finding = Tuple[str, int, str]


def _datetime_attr(node: ast.AST, name: str) -> bool:
    """True for ``datetime.utcnow`` / ``datetime.now``, not ``func.now``."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == name
        and isinstance(node.value, ast.Name)
        and node.value.id == "datetime"
    )


def _utcnow(node: ast.AST) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    return _datetime_attr(target, "utcnow")


def _naive_now(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not _datetime_attr(node.func, "now"):
        return False
    if node.args:
        return False
    for keyword in node.keywords:
        if keyword.arg in ("tz", "timezone"):
            return False
    return True


def _strips_timezone(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "replace":
        return False
    for keyword in node.keywords:
        if keyword.arg == "tzinfo" and isinstance(keyword.value, ast.Constant):
            if keyword.value.value is None:
                return True
    return False


def find_python_source(source: str, filename: str) -> List[Finding]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [(filename, exc.lineno or 1, f"could not parse: {exc.msg}")]
    called_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called_funcs.add(id(node.func))
    findings: List[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _utcnow(node):
            findings.append((filename, node.lineno, "datetime.utcnow is naive"))
        elif _datetime_attr(node, "utcnow") and id(node) not in called_funcs:
            findings.append((filename, node.lineno, "datetime.utcnow is naive"))
        elif _naive_now(node):
            findings.append((filename, node.lineno, "datetime.now() has no timezone"))
        elif _strips_timezone(node):
            findings.append((filename, node.lineno, "replace(tzinfo=None) drops the offset"))
    return findings


def server_files(root: Path) -> List[Path]:
    backend = root / "backend"
    paths: List[Path] = []
    for folder in ("app", "models"):
        base = backend / folder
        if base.is_dir():
            paths.extend(sorted(base.rglob("*.py")))
    paths.extend(sorted(backend.glob("*.py")))
    scripts = backend / "scripts"
    if scripts.is_dir():
        paths.extend(sorted(scripts.rglob("*.py")))
    return paths


def scan_tree(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in server_files(root):
        findings.extend(
            find_python_source(path.read_text(encoding="utf-8"), _rel(root, path))
        )
    return findings


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main(argv: Iterable[str] | None = None) -> int:
    del argv
    root = Path(__file__).resolve().parents[2]
    findings = scan_tree(root)
    for filename, lineno, message in findings:
        print(f"{filename}:{lineno}: {message}")
    if findings:
        print(f"{len(findings)} naive instant write(s) failed", file=sys.stderr)
        return 1
    print("naive instant write checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
