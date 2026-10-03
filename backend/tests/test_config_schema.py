"""Config v1 JSON Schema catalog and read-only validate API."""
import inspect
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.routers.config_schema import require_config_schema_access
from app.schemas.field_definition import DataType
from app.schemas.ui_schema import P1_TYPES, SCREEN_KEYS, SOP_HINTS
from app.schemas.workflow import VALID_WORKFLOW_ACTIONS
from app.services import config_schema as svc

TABLE_ID = "550e8400-e29b-41d4-a716-446655440000"
ROLE_ID = "550e8400-e29b-41d4-a716-446655440001"
COLUMN_ID = "550e8400-e29b-41d4-a716-446655440002"


def _client():
    app.dependency_overrides[require_config_schema_access] = lambda: SimpleNamespace(id=uuid4())
    return TestClient(app)


def setup_function():
    app.dependency_overrides.clear()


def teardown_function():
    app.dependency_overrides.clear()


def test_catalog_fits_live_contracts():
    schemas = svc.load_schemas()
    assert svc.known_schema_names() == [
        "field_definition",
        "ui_schema_column",
        "ui_schema_layout",
        "ui_schema_privilege",
        "ui_schema_relation",
        "ui_schema_table",
        "workflow_template",
    ]
    assert schemas["field_definition"]["properties"]["data_type"]["enum"] == [
        item.value for item in DataType
    ]
    assert "jsonb" not in schemas["field_definition"]["properties"]["data_type"]["enum"]
    assert schemas["ui_schema_column"]["properties"]["data_type"]["enum"] == list(P1_TYPES)
    assert "jsonb" not in schemas["ui_schema_column"]["properties"]["data_type"]["enum"]
    assert schemas["ui_schema_layout"]["properties"]["screen_key"]["enum"] == list(SCREEN_KEYS)
    hints = [
        hint
        for hint in schemas["ui_schema_column"]["properties"]["sop_hint"]["enum"]
        if hint is not None
    ]
    assert hints == list(SOP_HINTS)
    actions = schemas["workflow_template"]["properties"]["template_definition"]["properties"][
        "steps"
    ]["items"]["properties"]["action"]["enum"]
    assert actions == list(VALID_WORKFLOW_ACTIONS)


def test_service_does_not_touch_a_database():
    source = inspect.getsource(svc)
    assert "sqlalchemy" not in source
    assert "get_db" not in source
    router_source = inspect.getsource(__import__("app.routers.config_schema", fromlist=["router"]))
    assert "get_db" not in router_source
    assert "sqlalchemy" not in router_source
    assert "db" not in inspect.signature(svc.validation_errors).parameters


def test_field_definition_and_jsonb_rejection():
    assert svc.validation_errors(
        "field_definition",
        {
            "entity_type": "sample",
            "name": "volume_ml",
            "data_type": "number",
            "validation_rules": {"min": 0, "max": 10000},
        },
    ) == []
    errors = svc.validation_errors(
        "field_definition",
        {"entity_type": "sample", "name": "blob", "data_type": "jsonb"},
    )
    assert any(err["path"] == "/data_type" and err["keyword"] == "enum" for err in errors)
    bad_name = svc.validation_errors(
        "field_definition",
        {"entity_type": "sample", "name": "bad name", "data_type": "text"},
    )
    assert any(err["path"] == "/name" and err["keyword"] == "pattern" for err in bad_name)


def test_ui_schema_documents():
    assert svc.validation_errors(
        "ui_schema_table",
        {"display_name": "Plate map", "physical_name": "x_plate_map"},
    ) == []
    bad_table = svc.validation_errors(
        "ui_schema_table",
        {"display_name": "Samples", "physical_name": "samples"},
    )
    assert any(err["path"] == "/physical_name" for err in bad_table)

    assert svc.validation_errors(
        "ui_schema_column",
        {
            "table_id": TABLE_ID,
            "display_name": "Lot",
            "data_type": "text",
            "physical_name": "lot",
        },
    ) == []
    jsonb = svc.validation_errors(
        "ui_schema_column",
        {"table_id": TABLE_ID, "display_name": "Blob", "data_type": "jsonb"},
    )
    assert any(err["path"] == "/data_type" and err["keyword"] == "enum" for err in jsonb)
    missing_list = svc.validation_errors(
        "ui_schema_column",
        {"table_id": TABLE_ID, "display_name": "Matrix", "data_type": "list"},
    )
    assert any(err["keyword"] == "required" and "list_id" in err["message"] for err in missing_list)

    assert svc.validation_errors(
        "ui_schema_layout",
        {
            "role_id": ROLE_ID,
            "screen_key": "samples.detail",
            "fields": [{"column_id": COLUMN_ID, "sort_order": 1}],
        },
    ) == []
    hidden = svc.validation_errors(
        "ui_schema_layout",
        {
            "role_id": ROLE_ID,
            "screen_key": "receive",
            "fields": [{"column_id": COLUMN_ID, "hidden": True}],
        },
    )
    assert any(err["path"] == "/fields/0/hidden" and err["keyword"] == "additionalProperties" for err in hidden)

    assert svc.validation_errors(
        "ui_schema_privilege",
        {"role_id": ROLE_ID, "table_id": TABLE_ID, "access": "read"},
    ) == []
    inherit = svc.validation_errors(
        "ui_schema_privilege",
        {"role_id": ROLE_ID, "table_id": TABLE_ID, "access": "inherit"},
    )
    assert any(err["path"] == "/access" and err["keyword"] == "enum" for err in inherit)
    assert svc.validation_errors(
        "ui_schema_privilege",
        {
            "role_id": ROLE_ID,
            "table_id": TABLE_ID,
            "column_id": COLUMN_ID,
            "access": "inherit",
        },
    ) == []

    assert svc.validation_errors(
        "ui_schema_relation",
        {
            "display_name": "Project samples",
            "from_table_id": TABLE_ID,
            "to_table_id": ROLE_ID,
            "fk_column_id": COLUMN_ID,
            "cardinality": "one_to_many",
        },
    ) == []
    many = svc.validation_errors(
        "ui_schema_relation",
        {
            "display_name": "Tags",
            "from_table_id": TABLE_ID,
            "to_table_id": ROLE_ID,
            "fk_column_id": COLUMN_ID,
            "cardinality": "many_to_many",
        },
    )
    assert any(err["path"] == "/cardinality" and err["keyword"] == "enum" for err in many)
    junction = svc.validation_errors(
        "ui_schema_relation",
        {
            "display_name": "Tags",
            "from_table_id": TABLE_ID,
            "to_table_id": ROLE_ID,
            "fk_column_id": COLUMN_ID,
            "junction_table": "x_sample_tags",
        },
    )
    assert any(err["path"] == "/junction_table" and err["keyword"] == "additionalProperties" for err in junction)


def test_workflow_actions():
    assert svc.validation_errors(
        "workflow_template",
        {
            "name": "Receive",
            "template_definition": {
                "steps": [{"action": "accession_sample", "params": {"sample_id": "from-context"}}]
            },
        },
    ) == []
    bad = svc.validation_errors(
        "workflow_template",
        {"name": "Nope", "template_definition": {"steps": [{"action": "drop_database"}]}},
    )
    assert any(
        err["path"] == "/template_definition/steps/0/action" and err["keyword"] == "enum"
        for err in bad
    )
    params = svc.validation_errors(
        "workflow_template",
        {"name": "Nope", "template_definition": {"steps": [{"action": "update_status", "params": []}]}},
    )
    assert any(err["path"] == "/template_definition/steps/0/params" and err["keyword"] == "type" for err in params)


def test_unknown_schema_name():
    try:
        svc.get_schema("not_a_schema")
    except svc.UnknownConfigSchema as exc:
        assert exc.name == "not_a_schema"
        assert "field_definition" in exc.known
    else:
        raise AssertionError("expected UnknownConfigSchema")


def test_get_schema_catalog_and_one():
    client = _client()
    listed = client.get("/admin/config/schema")
    assert listed.status_code == 200
    body = listed.json()
    assert body["version"] == "v1"
    assert body["names"] == svc.known_schema_names()
    assert body["schemas"]["workflow_template"]["properties"]["template_definition"]["properties"]["steps"][
        "items"
    ]["properties"]["action"]["enum"] == list(VALID_WORKFLOW_ACTIONS)

    one = client.get("/admin/config/schema", params={"name": "field_definition"})
    assert one.status_code == 200
    assert one.json()["name"] == "field_definition"
    assert one.json()["schema"]["$id"] == "urn:nimblelims:config:v1:field_definition"

    missing = client.get("/admin/config/schema", params={"name": "jsonb_config"})
    assert missing.status_code == 404
    detail = missing.json()
    assert detail["valid"] is False
    assert detail["errors"][0]["keyword"] == "schema"
    assert detail["errors"][0]["path"] == "/schema"


def test_post_validate_success_and_structured_400():
    client = _client()
    ok = client.post(
        "/admin/config/validate",
        json={
            "schema": "ui_schema_column",
            "document": {
                "table_id": TABLE_ID,
                "display_name": "Note",
                "data_type": "text",
            },
        },
    )
    assert ok.status_code == 200
    assert ok.json() == {"valid": True, "schema": "ui_schema_column"}

    bad = client.post(
        "/admin/config/validate",
        json={
            "schema": "ui_schema_column",
            "document": {
                "table_id": TABLE_ID,
                "display_name": "Blob",
                "data_type": "jsonb",
            },
        },
    )
    assert bad.status_code == 400
    payload = bad.json()
    assert payload["valid"] is False
    assert payload["schema"] == "ui_schema_column"
    assert any(err["path"] == "/data_type" and err["keyword"] == "enum" for err in payload["errors"])

    unknown = client.post(
        "/admin/config/validate",
        json={"schema": "jsonb_config", "document": {}},
    )
    assert unknown.status_code == 400
    assert unknown.json()["errors"][0]["keyword"] == "schema"
    assert unknown.json()["errors"][0]["path"] == "/schema"


def test_validate_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/admin/config/validate",
        json={"schema": "field_definition", "document": {}},
    )
    assert response.status_code == 401


def test_validate_route_has_no_db_parameter():
    from app.routers import config_schema as router_mod

    for route in router_mod.router.routes:
        assert "db" not in inspect.signature(route.endpoint).parameters
        direct = [dep.call for dep in route.dependant.dependencies]
        assert require_config_schema_access in direct
