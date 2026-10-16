"""Flag truthiness tests of numeric fields.

Zero is a real measurement. ``if amount``, ``amount or default``, and
``amount || default`` treat 0 as missing. Comparisons (``is None``, ``== 0``,
``> 0``) and ``??`` are explicit and are left alone.

The field set is amount, volume, concentration, temperature, cost, multiplier,
capacity, and the limit/plan names high_value, low_value, target_amount,
target_volume, target_concentration, value_number, and transfer_amount.
SQL ``limit`` and string/collection checks are not in this set.

``@typescript-eslint/prefer-nullish-coalescing`` is not used: it flags every
``||``, including strings and arrays, and ``npm run lint`` does not run in CI.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

Finding = Tuple[str, int, str]

NUMERIC_FIELDS = frozenset(
    {
        "amount",
        "volume",
        "concentration",
        "temperature",
        "cost",
        "multiplier",
        "capacity",
        "target_amount",
        "target_volume",
        "target_concentration",
        "high_value",
        "low_value",
        "value_number",
        "transfer_amount",
    }
)

_TS_FIELD = (
    r"(?:amount|volume|concentration|temperature|cost|multiplier|capacity|"
    r"target_amount|target_volume|target_concentration|high_value|low_value|"
    r"value_number|transfer_amount)"
)
_TS_OR = re.compile(rf"(?<![\w])({_TS_FIELD})\s*\|\|")
_TS_AND = re.compile(rf"\.({_TS_FIELD})\s*&&")
_TS_IF = re.compile(rf"if\s*\(\s*!?\s*(?:[\w?]+\.)*({_TS_FIELD})\s*\)")
_TS_TERNARY = re.compile(rf"\.({_TS_FIELD})\s*\?(?![.?])")
_TS_STRING = re.compile(r"`(?:\\.|[^`])*`|'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"")


def _numeric_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and node.id in NUMERIC_FIELDS:
        return node.id
    if isinstance(node, ast.Attribute) and node.attr in NUMERIC_FIELDS:
        return node.attr
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _numeric_name(node.operand)
    return None


def find_python_source(source: str, filename: str) -> List[Finding]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [(filename, exc.lineno or 1, f"could not parse: {exc.msg}")]
    findings: List[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for value in node.values:
                name = _numeric_name(value)
                if name:
                    findings.append(
                        (filename, node.lineno, f"numeric field {name} used with or")
                    )
        elif isinstance(node, (ast.If, ast.IfExp, ast.While, ast.Assert)):
            name = _numeric_name(node.test)
            if name:
                findings.append(
                    (
                        filename,
                        node.lineno,
                        f"numeric field {name} used as a truthiness test",
                    )
                )
    return findings


def find_typescript_source(source: str, filename: str) -> List[Finding]:
    findings: List[Finding] = []
    for lineno, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        line = _TS_STRING.sub('""', raw)
        for pattern, message in (
            (_TS_OR, "numeric field {name} used with ||"),
            (_TS_AND, "numeric field {name} used with &&"),
            (_TS_IF, "numeric field {name} used as a truthiness test"),
            (_TS_TERNARY, "numeric field {name} used as a ternary test"),
        ):
            match = pattern.search(line)
            if match:
                findings.append(
                    (filename, lineno, message.format(name=match.group(1)))
                )
    return findings


def scan_tree(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    app = root / "backend" / "app"
    frontend = root / "frontend" / "src"
    if app.is_dir():
        for path in sorted(app.rglob("*.py")):
            findings.extend(find_python_source(path.read_text(encoding="utf-8"), _rel(root, path)))
    if frontend.is_dir():
        for pattern in ("*.ts", "*.tsx"):
            for path in sorted(frontend.rglob(pattern)):
                findings.extend(
                    find_typescript_source(path.read_text(encoding="utf-8"), _rel(root, path))
                )
    return findings


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main(argv: Iterable[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    findings = scan_tree(root)
    for filename, lineno, message in findings:
        print(f"{filename}:{lineno}: {message}")
    if findings:
        print(f"{len(findings)} numeric truthiness check(s) failed", file=sys.stderr)
        return 1
    print("numeric truthiness checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
