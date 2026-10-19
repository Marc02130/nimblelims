"""Fail when server code writes a naive UTC clock.

Instant columns are ``timestamptz``. A write must be timezone-aware
(``datetime.now(timezone.utc)`` or a SQL ``now()`` default). ``datetime.utcnow``
and ``datetime.now()`` with no timezone are naive. The same calls are naive
when they are fully qualified (``datetime.datetime.now()``,
``datetime.datetime.utcnow()``) or written through an alias
(``from datetime import datetime as dt``, ``import datetime as d``).
``replace(tzinfo=None)`` strips the offset before the value is stored.

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
from typing import Dict, Iterable, List, Optional, Tuple

Finding = Tuple[str, int, str]


def _bindings(tree: ast.AST) -> Dict[str, str]:
    """Map a local name to ``module`` or ``class``. The last binding wins."""
    events: List[Tuple[int, int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "datetime":
                    events.append(
                        (
                            node.lineno or 0,
                            node.col_offset or 0,
                            alias.asname or alias.name,
                            "module",
                        )
                    )
        elif isinstance(node, ast.ImportFrom) and node.module == "datetime":
            for alias in node.names:
                if alias.name == "datetime":
                    events.append(
                        (
                            node.lineno or 0,
                            node.col_offset or 0,
                            alias.asname or alias.name,
                            "class",
                        )
                    )
    bound: Dict[str, str] = {}
    for _line, _col, name, kind in sorted(events):
        bound[name] = kind
    return bound


def _attribute_chain(node: ast.AST) -> Optional[List[str]]:
    parts: List[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    parts.reverse()
    return parts


def _clock_kind(node: ast.AST, bound: Dict[str, str]) -> Optional[str]:
    """Return ``now`` or ``utcnow`` when ``node`` is that datetime function."""
    chain = _attribute_chain(node)
    if chain is None or len(chain) < 2:
        return None
    attr = chain[-1]
    if attr not in ("now", "utcnow"):
        return None
    root = chain[0]
    middle = chain[1:-1]
    kind = bound.get(root)
    if kind is None and root == "datetime":
        if middle == []:
            kind = "class"
        elif middle == ["datetime"]:
            kind = "module"
    if kind == "class" and middle == []:
        return attr
    if kind == "module" and middle == ["datetime"]:
        return attr
    return None


def _utcnow(node: ast.AST, bound: Dict[str, str]) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    return _clock_kind(target, bound) == "utcnow"


def _naive_now(node: ast.AST, bound: Dict[str, str]) -> bool:
    if not isinstance(node, ast.Call) or _clock_kind(node.func, bound) != "now":
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
    bound = _bindings(tree)
    called_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called_funcs.add(id(node.func))
    findings: List[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _utcnow(node, bound):
            findings.append((filename, node.lineno, "datetime.utcnow is naive"))
        elif _clock_kind(node, bound) == "utcnow" and id(node) not in called_funcs:
            findings.append((filename, node.lineno, "datetime.utcnow is naive"))
        elif _naive_now(node, bound):
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
