"""Which existing APIs a configuring-agent step may call.

The schema names are the Schema screen's allow-list. Lists, list items, and units
are not schema tables. A path this module does not allow stops the run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.services.ui_schema_catalog import LAB_TABLES, NOT_SCHEMA_TABLES, SYSTEM_TABLES

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
    ("POST", re.compile(r"^/v1/schema/tables/[^/]+/drop$"), "schema_tables", "schema:edit", "table"),
    ("POST", re.compile(r"^/v1/schema/columns$"), "schema_columns", "schema:edit", "column"),
    ("POST", re.compile(r"^/v1/schema/columns/[^/]+/deprecate$"), "schema_columns", "schema:edit", "column"),
    ("POST", re.compile(r"^/v1/schema/columns/[^/]+/drop$"), "schema_columns", "schema:edit", "column"),
    ("PUT", re.compile(r"^/v1/schema/layouts$"), "layouts", "layout:edit", "layout"),
    ("PUT", re.compile(r"^/v1/schema/privileges$"), "privileges", "schema:edit", "privilege"),
    ("POST", re.compile(r"^/v1/schema/relations$"), "relations", "schema:edit", "relationship"),
    ("DELETE", re.compile(r"^/v1/schema/relations/[^/]+$"), "relations", "schema:edit", "relationship"),
    ("POST", re.compile(r"^/lists$"), "other", "config:edit", "list"),
    ("PATCH", re.compile(r"^/lists/[^/]+$"), "other", "config:edit", "list"),
    ("POST", re.compile(r"^/lists/[^/]+/entries$"), "other", "config:edit", "list_entry"),
    ("PATCH", re.compile(r"^/lists/[^/]+/entries/[^/]+$"), "other", "config:edit", "list_entry"),
    ("DELETE", re.compile(r"^/lists/[^/]+$"), "other", "config:edit", "list"),
    ("DELETE", re.compile(r"^/lists/[^/]+/entries/[^/]+$"), "other", "config:edit", "list_entry"),
    ("POST", re.compile(r"^/v1/experiment-templates$"), "other", "experiment:manage", "experiment_template"),
    ("PATCH", re.compile(r"^/v1/experiment-templates/[^/]+$"), "other", "experiment:manage", "experiment_template"),
    ("POST", re.compile(r"^/containers/types$"), "other", "config:edit", "container_type"),
    ("POST", re.compile(r"^/v1/sample-type-transitions$"), "other", "config:edit", "sample_type_transition"),
    ("PATCH", re.compile(r"^/users/[^/]+$"), "other", "config:edit", "user_role"),
    ("PUT", re.compile(r"^/roles/[^/]+/permissions$"), "other", "config:edit", "role_permissions"),
)


@dataclass
class Classified:
    ok: bool
    group: str
    permission: Optional[str]
    kind: Optional[str]
    gap: Optional[str]


def schema_table_names() -> dict[str, tuple[str, ...]]:
    """The Schema screen's list. The agent does not keep a second one."""
    return {
        "lab": LAB_TABLES,
        "system": SYSTEM_TABLES,
        "not_schema": tuple(sorted(NOT_SCHEMA_TABLES)),
    }


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
    return None


def classify_call(method: str, path: str, body: Any = None) -> Classified:
    method = (method or "").upper()
    path = _norm_path(path)
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
