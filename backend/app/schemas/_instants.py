"""Serialize instants as UTC with a Z suffix.

Audit columns are ``timestamp without time zone``. Writers store UTC wall
time (``datetime.utcnow()`` / ``func.now()`` in a UTC session) and SQLAlchemy
returns a naive datetime. Pydantic's default JSON encoding omits the offset,
so a browser reads ``2026-10-18T23:23:00`` as local time and shows 11:23 PM
in US Eastern for a 7:23 PM instant.

Calendar fields (received_date, due_date, used_on, and the other lab days)
are not in ``INSTANT_FIELDS``. A date-only value must not gain a Z.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, SerializationInfo, model_serializer

INSTANT_FIELDS = frozenset(
    {
        "created_at",
        "modified_at",
        "updated_at",
        "started_at",
        "completed_at",
        "published_at",
        "canceled_at",
        "cancelled_at",
        "failed_at",
        "imported_at",
        "assigned_at",
        "granted_at",
        "applied_at",
        "last_login",
        "last_fit_at",
        "fit_triggered_at",
        "reviewed_at",
        "excluded_at",
        "write_back_at",
        "confirmed_at",
        "window_started_at",
        "expires_at",
        "used_at",
        "locked_until",
        "locked_at",
        "revoked_at",
        "submitted_at",
        "plan_updated_at",
        "last_execute_at",
    }
)

# User-defined blobs. A key inside one of these is not an audit instant.
_SKIP_WALK = frozenset(
    {
        "custom_attributes",
        "extra_fields",
        "row_data",
        "params",
        "template_definition",
        "validation_rules",
        "billing_info",
    }
)

_NAIVE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?$")
_AWARE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _as_utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        aware = value.replace(tzinfo=timezone.utc)
    else:
        aware = value.astimezone(timezone.utc)
    text = aware.isoformat()
    if text.endswith("+00:00"):
        return text[: -len("+00:00")] + "Z"
    return text


def instant_to_utc_z(value: Any) -> Any:
    """UTC ISO-8601 ending in Z. None stays None. Non-instants stay as they are."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_utc_z(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return value
        if _NAIVE.match(text) is not None:
            return text.replace(" ", "T", 1) + "Z"
        if _AWARE.match(text) is not None:
            normalized = text.replace(" ", "T", 1)
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            return _as_utc_z(datetime.fromisoformat(normalized))
        return value
    return value


def stamp_instants(value: Any) -> Any:
    """Walk JSON-ready data and stamp instant field names. Idempotent."""
    if isinstance(value, dict):
        stamped: dict[Any, Any] = {}
        for key, item in value.items():
            if key in INSTANT_FIELDS:
                stamped[key] = instant_to_utc_z(item)
            elif key in _SKIP_WALK:
                stamped[key] = item
            else:
                stamped[key] = stamp_instants(item)
        return stamped
    if isinstance(value, list):
        return [stamp_instants(item) for item in value]
    return value


class APIModel(BaseModel):
    """Shared model. JSON output stamps instant fields as UTC with Z."""

    @model_serializer(mode="wrap", when_used="json")
    def _serialize_instants(self, handler, info: SerializationInfo) -> Any:
        data = handler(self)
        if getattr(info, "mode", None) != "json":
            return data
        return stamp_instants(data)
