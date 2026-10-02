"""Admin Config v1: serve JSON Schemas and validate documents. Read-only."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import require_any_permission
from app.services.config_schema import (
    UnknownConfigSchema,
    catalog,
    get_schema,
    validation_errors,
)

router = APIRouter(prefix="/admin/config", tags=["config"])

# Field definitions and workflows use config:edit. UI schema uses schema:edit.
# Either may read the catalog and dry-run a document. Nothing is stored.
require_config_schema_access = require_any_permission(["config:edit", "schema:edit"])


class ConfigValidateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: str = Field(..., alias="schema", min_length=1, max_length=64)
    document: Any


def _unknown(name: str, known: list[str]) -> dict:
    return {
        "valid": False,
        "schema": name,
        "errors": [
            {
                "path": "/schema",
                "message": f"Unknown config schema '{name}'. Known: {', '.join(known)}",
                "keyword": "schema",
            }
        ],
    }


@router.get("/schema")
def get_config_schema(
    name: Optional[str] = Query(None, description="Return one schema by name"),
    _user=Depends(require_config_schema_access),
):
    """Return the Config v1 catalog, or one schema when name is set."""
    if name is None:
        return catalog()
    try:
        document = get_schema(name)
    except UnknownConfigSchema as exc:
        return JSONResponse(status_code=404, content=_unknown(exc.name, exc.known))
    return {"name": name, "schema": document}


@router.post("/validate")
def validate_config(
    body: ConfigValidateIn,
    _user=Depends(require_config_schema_access),
):
    """Validate a document against a Config v1 schema. Does not persist."""
    try:
        errors = validation_errors(body.schema_name, body.document)
    except UnknownConfigSchema as exc:
        return JSONResponse(status_code=400, content=_unknown(exc.name, exc.known))
    if errors:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "schema": body.schema_name, "errors": errors},
        )
    return {"valid": True, "schema": body.schema_name}
