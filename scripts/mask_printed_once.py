#!/usr/bin/env python3
"""Replace each line after a printed-once header. Exit non-zero on failure.

Read stdin, write stdout. The password line is replaced by position with
``[redacted]``. A missing header, a header with no following line, or a
missing mask token exits 1. Nothing is written to stdout in that case.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.secret_output import SecretOutputError, mask_printed_once  # noqa: E402


def main() -> int:
    text = sys.stdin.read()
    try:
        masked = mask_printed_once(text)
    except SecretOutputError:
        return 1
    sys.stdout.write(masked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
