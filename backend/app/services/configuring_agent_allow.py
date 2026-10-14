"""Which existing APIs a configuring-agent step may call.

Scope is the confirming user's own permissions (Marc 2026-10-07, L-2): the agent
may call an allowed route only when that user holds the permission the route
already requires. The Schema screen's catalog is a display rule, not the agent's
scope; the only catalog fact kept here is that lists, list items, and units are
not Schema tables (FB-9). The API's own 422s (system tables, ADD_COLUMN_OUT)
still stop a row.

No drop and no delete, ever (L-B, L-3, FB-11). Removal is a status flag
(deprecate / ``active`` false) or, for a container, contents amount -> 0.
A path this module does not allow stops the run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.services.ui_schema_catalog import NOT_SCHEMA_TABLES

STOP_BANNER = "Can't apply this change through configuration APIs"
P1_TYPES = ("text", "numeric", "integer", "boolean", "date", "timestamptz", "list")
PROVIDERS = ("openai", "xai", "anthropic")

_OUT_OF_SCOPE = (
    ("/v1/asked-for", "Asked-for stays as built."),
    ("/v1/routing-map", "Routing stays as built."),
    ("/v1/eln-process-definitions", "ELN process definitions are not this configuration run."),
    ("/v1/data-parsers", "Parsers are not this configuration run."),
    ("/v1/lims-runs", "Run analysis and dose-response are not configuration."),
    ("/results", "Results stay as they are. Instrument rows are not a configuration write."),
    ("/admin/fields", "Custom fields are not a place to work."),
    ("/admin/custom-attributes", "Custom attributes are not a place to work."),
    ("/admin/custom-fields", "Custom fields are not a place to work."),
    ("/admin/workflow-templates", "Workflow templates are not this configuration run."),
    ("/samples/receive", "Receive is a lab motion, not a configuration write."),
)

_ALLOWED: tuple[tuple[str, re.Pattern[str], str, str, str], ...] = (
    ("POST", re.compile(r"^/v1/schema/tables$"), "schema_tables", "schema:edit", "table"),
    ("POST", re.compile(r"^/v1/schema/tables/[^/]+/deprecate$"), "schema_tables", "schema:edit", "table"),
    ("POST", re.compile(r"^/v1/schema/columns$"), "schema_columns", "schema:edit", "column"),
    ("POST", re.compile(r"^/v1/schema/columns/[^/]+/deprecate$"), "schema_columns", "schema:edit", "column"),
    ("PUT", re.compile(r"^/v1/schema/layouts$"), "layouts", "layout:edit", "layout"),
    ("PUT", re.compile(r"^/v1/schema/privileges$"), "privileges", "schema:edit", "privilege"),
    ("POST", re.compile(r"^/v1/schema/relations$"), "relations", "schema:edit", "relationship"),
    ("POST", re.compile(r"^/lists$"), "other", "config:edit", "list"),
    ("PATCH", re.compile(r"^/lists/[^/]+$"), "other", "config:edit", "list"),
    ("POST", re.compile(r"^/lists/[^/]+/entries$"), "other", "config:edit", "list_entry"),
    ("PATCH", re.compile(r"^/lists/[^/]+/entries/[^/]+$"), "other", "config:edit", "list_entry"),
    ("POST", re.compile(r"^/v1/experiment-templates$"), "other", "experiment:manage", "experiment_template"),
    ("PATCH", re.compile(r"^/v1/experiment-templates/[^/]+$"), "other", "experiment:manage", "experiment_template"),
    ("POST", re.compile(r"^/containers/types$"), "other", "config:edit", "container_type"),
    ("POST", re.compile(r"^/v1/sample-type-transitions$"), "other", "config:edit", "sample_type_transition"),
    ("PATCH", re.compile(r"^/users/[^/]+$"), "other", "config:edit", "user_role"),
    ("PUT", re.compile(r"^/roles/[^/]+/permissions$"), "other", "config:edit", "role_permissions"),
    # D-5 (UAT 06c630b): a measured result (Qubit concentration) lives on an
    # analyte of an analysis, recorded on the DNA sample's test (SPEC §11 item 5).
    ("POST", re.compile(r"^/analyses$"), "other", "config:edit", "analysis"),
    ("POST", re.compile(r"^/analytes$"), "other", "config:edit", "analyte"),
    ("POST", re.compile(r"^/analyses/[^/]+/analytes$"), "other", "config:edit", "analysis_analytes"),
    # Container retire: contents amount -> 0 is the only container removal (L-B).
    ("PATCH", re.compile(r"^/containers/[^/]+/contents/[^/]+$"), "other", "sample:update", "contents_amount"),
)

DROP_DELETE_GAP = (
    "Drop and delete are never applied by the configuring agent. "
    "Retire a record with its status flag (Set inactive), or a container with Amount \u2192 0."
)
RELATION_REMOVE_GAP = (
    "A relation has no status flag, and the agent never deletes. "
    "Removing a relation can't be done through configuration APIs."
)


def is_drop_or_delete(method: str, path: str) -> bool:
    """True for any DELETE and for the Schema drop routes. Never callable."""
    method = (method or "").upper()
    path = _norm_path(path)
    return method == "DELETE" or bool(re.search(r"/drop$", path)) or path.endswith("/truncate")


# Rows that need the second confirm (L-1): roles and privileges, schema changes,
# set-inactive, and amount -> 0.
HIGH_IMPACT_KINDS = {"role_permissions", "user_role", "privilege", "layout", "table", "column", "relationship"}


def verb_for(method: str, path: str, body: Any) -> str:
    """Admin verb for a row: Create, Update, Set inactive, or Amount \u2192 0."""
    method = (method or "").upper()
    path = _norm_path(path)
    data = body if isinstance(body, dict) else {}
    if re.match(r"^/containers/[^/]+/contents/[^/]+$", path):
        return "Amount \u2192 0"
    if path.endswith("/deprecate") or (method == "PATCH" and data.get("active") is False):
        return "Set inactive"
    if method == "POST":
        return "Create"
    return "Update"


def needs_second_confirm(method: str, path: str, body: Any, kind: Optional[str]) -> bool:
    if (kind or "") in HIGH_IMPACT_KINDS:
        return True
    return verb_for(method, path, body) in ("Set inactive", "Amount \u2192 0")


@dataclass
class Classified:
    ok: bool
    group: str
    permission: Optional[str]
    kind: Optional[str]
    gap: Optional[str]


def not_schema_tables() -> tuple[str, ...]:
    """Lists, list items, and units: never Schema tables, never a column add (FB-9)."""
    return tuple(sorted(NOT_SCHEMA_TABLES))


def _norm_path(path: str) -> str:
    path = (path or "").split("?", 1)[0].strip()
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _body_gap(method: str, path: str, body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        body = {}
    cardinality = str(body.get("cardinality") or "")
    if cardinality and cardinality not in ("one_to_many", "one_to_one"):
        return (
            "Relations accept one-to-many or one-to-one on an existing foreign key. "
            "There is no junction API."
        )
    data_type = body.get("data_type")
    if data_type is not None and data_type not in P1_TYPES:
        return (
            "Add-column types are text, numeric, integer, boolean, date, timestamptz, and list. "
            f"{data_type} is not one of them, and there is no foreign-key add-column type."
        )
    for key in ("physical_name", "table", "table_name"):
        value = body.get(key)
        if isinstance(value, str) and value in NOT_SCHEMA_TABLES:
            return (
                f"{value} is not a Schema table. "
                "Edit lists under Lists and units under Units. Do not add columns on them."
            )
    custom = body.get("custom_attributes")
    if isinstance(custom, dict) and custom:
        return "custom_attributes is not configuration. A field is a real column."
    if path.startswith("/users/") and method == "PATCH":
        extra = set(body) - {"role_id"}
        if extra:
            return "An existing user's role can be set. Other user fields, including a password, cannot."
        if "role_id" not in body:
            return "An existing user's role is the only user change this run can make."
    if re.search(r"/projects/[^/]+/users", path):
        return "No existing API grants a user access to a project. This run will not invent one."
    if re.match(r"^/containers/[^/]+/contents/[^/]+$", path):
        if set(body) != {"amount"} or body.get("amount") not in (0, 0.0):
            return (
                "The only container change this run makes is Amount \u2192 0 (retire). "
                "Send amount 0 and nothing else."
            )
    return None


def classify_call(method: str, path: str, body: Any = None) -> Classified:
    method = (method or "").upper()
    path = _norm_path(path)
    if is_drop_or_delete(method, path):
        gap = RELATION_REMOVE_GAP if "/v1/schema/relations/" in path else DROP_DELETE_GAP
        return Classified(False, "other", None, None, gap)
    if method == "POST" and path == "/users":
        return Classified(False, "other", None, None, "Personnel input uses existing users. This run does not create users.")
    if re.search(r"/projects/[^/]+/users", path):
        return Classified(
            False, "other", None, None, "No existing API grants a user access to a project. This run will not invent one."
        )
    for prefix, reason in _OUT_OF_SCOPE:
        if path == prefix or path.startswith(prefix + "/"):
            return Classified(False, "other", None, None, reason)
    gap = _body_gap(method, path, body)
    if gap and (
        "cardinality" in (body or {})
        or (isinstance(body, dict) and body.get("data_type") not in (None, *P1_TYPES))
        or gap.startswith("custom_attributes")
        or "not a Schema table" in gap
        or path.startswith("/users/")
        or path.startswith("/containers/")
    ):
        return Classified(False, "relations" if "junction" in gap else "other", None, None, gap)
    for allowed_method, pattern, group, permission, kind in _ALLOWED:
        if method == allowed_method and pattern.match(path):
            if gap:
                return Classified(False, group, None, None, gap)
            if path.startswith("/lists"):
                group = "other"
            return Classified(True, group, permission, kind, None)
    return Classified(
        False,
        "other",
        None,
        None,
        f"No configuration API matches {method} {path}.",
    )
