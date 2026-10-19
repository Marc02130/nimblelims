"""Mask a generated-password line that follows a printed-once header.

The password line is replaced by position. The filter does not search for
password characters. A missing header, a header with no following line, or a
result that does not contain the mask token aborts.
"""
from __future__ import annotations

import sys

MASK_TOKEN = "[redacted]"
PRINTED_ONCE_HEADER = "printed once"


class SecretOutputError(RuntimeError):
    """The stream could not be masked. Callers exit non-zero."""


def _abort(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SecretOutputError(message)


def mask_printed_once(text: str) -> str:
    """Return ``text`` with each line after a printed-once header replaced.

    The whole following line becomes ``[redacted]``. Surrounding words on
    that line are removed with it.
    """
    if not MASK_TOKEN:
        _abort("mask token is missing")
    ends_with_newline = text.endswith("\n")
    lines = text.splitlines()
    masked = 0
    index = 0
    output: list[str] = []
    while index < len(lines):
        line = lines[index]
        output.append(line)
        if PRINTED_ONCE_HEADER in line:
            if index + 1 >= len(lines):
                _abort("printed-once header has no following line to mask")
            output.append(MASK_TOKEN)
            masked += 1
            index += 2
            continue
        index += 1
    if masked == 0:
        _abort("printed-once header is missing")
    rendered = "\n".join(output)
    if ends_with_newline:
        rendered += "\n"
    if MASK_TOKEN not in rendered:
        _abort("mask token is missing")
    return rendered
