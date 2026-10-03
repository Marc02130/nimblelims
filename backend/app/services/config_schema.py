"""Read-only Config v1 JSON Schema catalog.

Schema documents live as files under backend/schemas/config/. This module
loads and validates them. It does not persist configuration and does not
write JSONB (OQ-16).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from app.schemas.field_definition import DataType
from app.schemas.ui_schema import CARDINALITIES, P1_TYPES, SCREEN_KEYS, SOP_HINTS
from app.schemas.workflow import VALID_WORKFLOW_ACTIONS

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = _BACKEND_ROOT / "schemas" / "config"
_FILE_RE = re.compile(r"^([a-z][a-z0-9_]*)\.schema\.json$")
_FORMAT_CHECKER = Draft202012Validator.FORMAT_CHECKER
MAX_ERRORS = 50

_REQUIRED_NAMES = (
    "field_definition",
    "ui_schema_table",
    "ui_schema_column",
    "ui_schema_layout",
    "ui_schema_privilege",
    "ui_schema_relation",
    "workflow_template",
)


class UnknownConfigSchema(LookupError):
    def __init__(self, name: str, known: list[str]):
        self.name = name
        self.known = known
        super().__init__(name)


class ConfigSchemaCatalogError(RuntimeError):
    pass


def _pointer(path) -> str:
    if not path:
        return ""
    return "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1") for part in path
    )


def _error_paths(err) -> list[str]:
    """JSON Pointers for one schema error.

    additionalProperties reports the parent object. Point at each unexpected
    key so a 400 names the field (layout has no hide flag).
    """
    base = _pointer(err.absolute_path)
    if err.validator != "additionalProperties":
        return [base]
    names = re.findall(r"'([^']+)'", err.message)
    if not names:
        return [base]
    return [f"{base}/{name.replace('~', '~0').replace('/', '~1')}" for name in names]


def _assert_fits(schemas: Mapping[str, dict]) -> None:
    missing = [name for name in _REQUIRED_NAMES if name not in schemas]
    if missing:
        raise ConfigSchemaCatalogError(f"Config v1 catalog missing: {missing}")

    field_types = schemas["field_definition"]["properties"]["data_type"]["enum"]
    if list(field_types) != [item.value for item in DataType]:
        raise ConfigSchemaCatalogError(
            "field_definition data_type enum does not match DataType"
        )
    if "jsonb" in field_types:
        raise ConfigSchemaCatalogError("field_definition must not allow jsonb (OQ-16)")

    col_types = schemas["ui_schema_column"]["properties"]["data_type"]["enum"]
    if list(col_types) != list(P1_TYPES):
        raise ConfigSchemaCatalogError(
            "ui_schema_column data_type enum does not match P1_TYPES"
        )
    if "jsonb" in col_types:
        raise ConfigSchemaCatalogError("ui_schema_column must not allow jsonb (OQ-16)")

    screens = schemas["ui_schema_layout"]["properties"]["screen_key"]["enum"]
    if list(screens) != list(SCREEN_KEYS):
        raise ConfigSchemaCatalogError(
            "ui_schema_layout screen_key enum does not match SCREEN_KEYS"
        )

    hints = [
        hint
        for hint in schemas["ui_schema_column"]["properties"]["sop_hint"]["enum"]
        if hint is not None
    ]
    if hints != list(SOP_HINTS):
        raise ConfigSchemaCatalogError("sop_hint enum does not match SOP_HINTS")

    cardinalities = schemas["ui_schema_relation"]["properties"]["cardinality"]["enum"]
    if list(cardinalities) != list(CARDINALITIES):
        raise ConfigSchemaCatalogError(
            "ui_schema_relation cardinality enum does not match CARDINALITIES"
        )
    if "many_to_many" in cardinalities:
        raise ConfigSchemaCatalogError(
            "ui_schema_relation must not allow many_to_many (no junction tables this phase)"
        )

    actions = schemas["workflow_template"]["properties"]["template_definition"][
        "properties"
    ]["steps"]["items"]["properties"]["action"]["enum"]
    if list(actions) != list(VALID_WORKFLOW_ACTIONS):
        raise ConfigSchemaCatalogError(
            "workflow action enum does not match VALID_WORKFLOW_ACTIONS"
        )


@lru_cache(maxsize=1)
def load_schemas() -> Mapping[str, dict]:
    if not SCHEMA_DIR.is_dir():
        raise ConfigSchemaCatalogError(f"Config schema directory not found: {SCHEMA_DIR}")
    loaded: dict[str, dict] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        match = _FILE_RE.match(path.name)
        if not match:
            raise ConfigSchemaCatalogError(f"Unexpected config schema filename: {path.name}")
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, dict):
            raise ConfigSchemaCatalogError(f"{path.name} must be a JSON object")
        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as exc:
            raise ConfigSchemaCatalogError(
                f"{path.name} is not a valid JSON Schema: {exc.message}"
            ) from exc
        loaded[match.group(1)] = document
    _assert_fits(loaded)
    return loaded


def known_schema_names() -> list[str]:
    return sorted(load_schemas())


def get_schema(name: str) -> dict:
    schemas = load_schemas()
    if name not in schemas:
        raise UnknownConfigSchema(name, sorted(schemas))
    return schemas[name]


def catalog() -> dict[str, Any]:
    schemas = load_schemas()
    names = sorted(schemas)
    return {
        "version": "v1",
        "names": names,
        "schemas": {name: schemas[name] for name in names},
    }


def validation_errors(schema_name: str, document: Any) -> list[dict[str, str]]:
    """Return structured JSON Schema errors. Empty means the document is valid."""
    validator = Draft202012Validator(get_schema(schema_name), format_checker=_FORMAT_CHECKER)
    found = sorted(
        validator.iter_errors(document),
        key=lambda err: (_pointer(err.absolute_path), str(err.validator), err.message),
    )
    records: list[dict[str, str]] = []
    for err in found:
        for path in _error_paths(err):
            records.append(
                {
                    "path": path,
                    "message": err.message,
                    "keyword": str(err.validator),
                }
            )
            if len(records) >= MAX_ERRORS:
                return records
    return records
