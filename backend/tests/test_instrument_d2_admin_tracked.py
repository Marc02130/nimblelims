"""D2: only an Administrator sets instruments.maintenance_tracked."""
import pytest

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_catalog as cat
from app.services.configuring_agent_apply import CannotExpress, execute_step
from app.services.configuring_agent_llm import _system_prompt
from models.instrument import InstrumentMaintenanceAudit
from tests.test_instrument_hardening_e1 import _role_user
from tests.test_instrument_tracking import _instrument, _login, _name, _seeded_type


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _code(response):
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        return detail.get("code")
    return None


def test_config_editor_and_other_roles_cannot_set_maintenance_tracked(
    client, admin_h, db_session, test_org, test_admin_user
):
    type_id = _seeded_type(client, admin_h)["id"]
    editor = _role_user(
        db_session, test_org, "Configuration Editor", extra_perms=("config:edit",)
    )
    manager = _role_user(
        db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",)
    )
    tech = _role_user(
        db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",)
    )
    client_user = _role_user(db_session, test_org, "CRO Partner")
    editor_h = _login(client, editor.username, "pass-word-1")
    manager_h = _login(client, manager.username, "pass-word-1")
    tech_h = _login(client, tech.username, "pass-word-1")
    client_h = _login(client, client_user.username, "pass-word-1")
    inst = _instrument(client, admin_h, maintenance_tracked=False)

    create_body = {
        "name": _name("Editor"),
        "instrument_type_id": type_id,
        "maintenance_tracked": True,
    }
    editor_create_on = client.post("/v1/instruments", headers=editor_h, json=create_body)
    assert editor_create_on.status_code == 403, editor_create_on.text
    assert _code(editor_create_on) == "maintenance_tracked_admin_only"

    create_off = {**create_body, "name": _name("EditorOff"), "maintenance_tracked": False}
    editor_create_off = client.post("/v1/instruments", headers=editor_h, json=create_off)
    assert editor_create_off.status_code == 403, editor_create_off.text
    assert _code(editor_create_off) == "maintenance_tracked_admin_only"

    omitted = client.post(
        "/v1/instruments",
        headers=editor_h,
        json={"name": _name("EditorPlain"), "instrument_type_id": type_id},
    )
    assert omitted.status_code == 201, omitted.text
    assert omitted.json()["maintenance_tracked"] is False
    other_field = client.patch(
        f"/v1/instruments/{omitted.json()['id']}",
        headers=editor_h,
        json={"description": "config editor may edit other fields"},
    )
    assert other_field.status_code == 200, other_field.text

    for headers in (editor_h, manager_h, tech_h, client_h):
        for flag in (True, False):
            refused = client.patch(
                f"/v1/instruments/{inst['id']}",
                headers=headers,
                json={"maintenance_tracked": flag},
            )
            assert refused.status_code == 403, refused.text
            if headers is editor_h:
                assert _code(refused) == "maintenance_tracked_admin_only"

    still = client.get(f"/v1/instruments/{inst['id']}", headers=admin_h).json()
    assert still["maintenance_tracked"] is False

    admin_on = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True, "reason": "start tracking"},
    )
    assert admin_on.status_code == 200, admin_on.text
    assert admin_on.json()["maintenance_tracked"] is True
    admin_off = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": False, "reason": "stop tracking"},
    )
    assert admin_off.status_code == 200, admin_off.text
    assert admin_off.json()["maintenance_tracked"] is False

    db_session.expire_all()
    audits = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == inst["id"])
        .order_by(InstrumentMaintenanceAudit.created_at)
        .all()
    )
    values = [(a.previous_value, a.new_value, a.created_by, a.created_at) for a in audits]
    assert any(prev is False and new is True for prev, new, *_ in values)
    assert any(prev is True and new is False for prev, new, *_ in values)
    assert all(who == test_admin_user.id and when is not None for _, _, who, when in values)


def test_agent_refuses_maintenance_tracked_in_classify_and_apply(
    client, admin_h, db_session, test_admin_user
):
    type_id = _seeded_type(client, admin_h)["id"]
    name = _name("Agent")
    post_body = {
        "name": name,
        "instrument_type_id": type_id,
        "maintenance_tracked": True,
    }
    classified = allow.classify_call("POST", "/v1/instruments", post_body)
    assert classified.ok is False
    assert "does not set maintenance tracking" in (classified.gap or "")
    try:
        execute_step(db_session, test_admin_user, "POST", "/v1/instruments", post_body)
    except CannotExpress as exc:
        assert "does not set maintenance tracking" in exc.gap
    else:
        raise AssertionError("apply should refuse an instrument POST with maintenance_tracked")

    omitted = allow.classify_call(
        "POST", "/v1/instruments", {"name": name, "instrument_type_id": type_id}
    )
    assert omitted.ok is True
    created = execute_step(
        db_session,
        test_admin_user,
        "POST",
        "/v1/instruments",
        {"name": name, "instrument_type_id": type_id},
    )
    assert created[0].kind == "instrument"
    row = client.get(f"/v1/instruments/{created[0].target_id}", headers=admin_h).json()
    assert row["maintenance_tracked"] is False

    patch_body = {"maintenance_tracked": False}
    path = f"/v1/instruments/{row['id']}"
    patched = allow.classify_call("PATCH", path, patch_body)
    assert patched.ok is False
    assert "does not set maintenance tracking" in (patched.gap or "")
    try:
        execute_step(db_session, test_admin_user, "PATCH", path, patch_body)
    except CannotExpress as exc:
        assert "does not set maintenance tracking" in exc.gap
    else:
        raise AssertionError("apply should refuse an instrument PATCH with maintenance_tracked")


def test_lab_manager_and_tech_with_config_edit_cannot_set_maintenance_tracked(
    client, admin_h, db_session, test_org
):
    type_id = _seeded_type(client, admin_h)["id"]
    manager = _role_user(
        db_session,
        test_org,
        "Lab Manager",
        extra_perms=("config:edit", "experiment:manage"),
    )
    tech = _role_user(
        db_session,
        test_org,
        "Lab Technician",
        extra_perms=("config:edit", "experiment:manage"),
    )
    manager_h = _login(client, manager.username, "pass-word-1")
    tech_h = _login(client, tech.username, "pass-word-1")
    inst = _instrument(client, admin_h, maintenance_tracked=False)
    for headers in (manager_h, tech_h):
        created = client.post(
            "/v1/instruments",
            headers=headers,
            json={
                "name": _name("Cfg"),
                "instrument_type_id": type_id,
                "maintenance_tracked": True,
            },
        )
        assert created.status_code == 403, created.text
        assert _code(created) == "maintenance_tracked_admin_only"
        for flag in (True, False):
            refused = client.patch(
                f"/v1/instruments/{inst['id']}",
                headers=headers,
                json={"maintenance_tracked": flag},
            )
            assert refused.status_code == 403, refused.text
            assert _code(refused) == "maintenance_tracked_admin_only"


def test_camel_case_maintenance_tracked_is_ignored(client, admin_h):
    type_id = _seeded_type(client, admin_h)["id"]
    created = client.post(
        "/v1/instruments",
        headers=admin_h,
        json={
            "name": _name("Camel"),
            "instrument_type_id": type_id,
            "maintenanceTracked": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["maintenance_tracked"] is False


def test_admin_create_with_tracked_true_writes_no_maintenance_audit(
    client, admin_h, db_session
):
    type_id = _seeded_type(client, admin_h)["id"]
    created = client.post(
        "/v1/instruments",
        headers=admin_h,
        json={
            "name": _name("Audited"),
            "instrument_type_id": type_id,
            "maintenance_tracked": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["maintenance_tracked"] is True
    db_session.expire_all()
    audits = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == created.json()["id"])
        .all()
    )
    assert audits == []


def test_agent_prompt_and_summary_do_not_instruct_setting_the_flag():
    prompt = _system_prompt(None, "")
    lowered = prompt.lower()
    assert "ask whether the lab tracks" not in lowered
    assert "and set maintenance_tracked" not in lowered
    assert "maintenance_tracked true or false" not in prompt
    assert "Do not set maintenance_tracked." in prompt
    assert "An Administrator can turn on maintenance tracking." in prompt
    formats = cat.route_formats_text()
    assert "maintenance_tracked" not in formats
