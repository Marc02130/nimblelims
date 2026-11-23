"""RFC 8785 JSON Canonicalization Scheme for the activation review (calculations S8).

The review document holds objects, arrays, strings, integers, booleans, and
null. Floating-point numbers are refused rather than encoded: the document has
none, and the RFC's number formatting is the part most likely to differ
between implementations.

What the RFC requires, and what this module does:

* Object members are sorted by the UTF-16 code units of their names.
* No insignificant whitespace.
* Strings use the shortest escapes: ``\\b \\t \\n \\f \\r \\" \\\\`` and ``\\u00xx`` in
  lowercase hex for the other control characters; every other character is
  written as itself, as UTF-8. A lone surrogate is refused.
* Integers are written in decimal with no exponent. Integers outside the range
  a double holds exactly (+/- 2**53 - 1) are refused, as I-JSON requires.
"""
from __future__ import annotations

import hashlib
from typing import Any

MAX_SAFE_INTEGER = 2**53 - 1

_ESCAPES = {
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0C: "\\f",
    0x0D: "\\r",
    0x22: '\\"',
    0x5C: "\\\\",
}


class CanonicalizationError(ValueError):
    """The value has a type or content that has no canonical form here."""


def _string(value: str) -> str:
    out = ['"']
    for ch in value:
        code = ord(ch)
        if 0xD800 <= code <= 0xDFFF:
            raise CanonicalizationError("A lone surrogate has no UTF-8 form.")
        if code in _ESCAPES:
            out.append(_ESCAPES[code])
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _utf16_key(name: str) -> bytes:
    return name.encode("utf-16-be", errors="surrogatepass")


def _encode(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(_string(value))
    elif isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalizationError("An integer outside +/- (2**53 - 1) is not canonical.")
        out.append(str(int(value)))
    elif isinstance(value, float):
        raise CanonicalizationError("The review document holds no floating-point number.")
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _encode(item, out)
        out.append("]")
    elif isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("An object name is a string.")
        out.append("{")
        for index, key in enumerate(sorted(value, key=_utf16_key)):
            if index:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _encode(value[key], out)
        out.append("}")
    else:
        raise CanonicalizationError(f"{type(value).__name__} has no JSON form.")


def canonical_json(value: Any) -> str:
    """The RFC 8785 text of a JSON value."""
    out: list[str] = []
    _encode(value, out)
    return "".join(out)


def canonical_bytes(value: Any) -> bytes:
    """The RFC 8785 text as UTF-8."""
    return canonical_json(value).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Lowercase hex SHA-256 of the canonical UTF-8 bytes."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
