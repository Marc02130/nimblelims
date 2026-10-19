"""Lab timezone stored on lab_settings.

There is no environment fallback. An empty row fails until an administrator
saves a real IANA zone. A lab manager may read it. A lab manager, lab
technician, client, or configuration editor cannot change it.
"""
import importlib.util
import inspect
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.exc import ProgrammingError

from app.core import lab_time
from app.core.security import get_password_hash
from app.services import configuring_agent_allow as allow
from models.lab_setting import LAB_SETTINGS_ID, LabSetting
from models.user import Permission, Role, User
from tests.conftest import _get_or_create, _grant


def _login(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _person(db, org, username, role_name, perms):
    role = _get_or_create(db, Role, role_name, role_name)
    _grant(db, role, [_get_or_create(db, Permission, name, name) for name in perms])
    user = User(
        name=username,
        username=username,
        email=f"{username}-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("pass-word-1"),
        role_id=role.id,
        client_id=org.id,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    return user


def test_migration_only_adds_lab_settings():
    path = Path(__file__).resolve().parents[1] / "db" / "migrations" / "versions" / "0095_lab_settings.py"
    spec = importlib.util.spec_from_file_location("mig0095", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "0095_lab_settings"
    assert mod.down_revision == "0094_routing_map_tat_min_zero"
    upgrade = inspect.getsource(mod.upgrade)
    assert "DROP" not in upgrade.upper()
    assert "DELETE FROM" not in upgrade.upper()


def test_env_seeds_an_empty_setting(monkeypatch, db_session):
    """LAB_TIMEZONE does not seed. An empty row stays empty and fails loudly."""
    _clear_lab_timezone(db_session)
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    with pytest.raises(lab_time.LabTimezoneUnset, match="lab timezone not configured"):
        lab_time.resolve_lab_timezone(db_session)
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    assert row is None or not (row.timezone or "").strip()


def test_saved_zone_wins_over_the_environment(monkeypatch, db_session):
    monkeypatch.setenv("LAB_TIMEZONE", "UTC")
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        db_session.add(LabSetting(id=LAB_SETTINGS_ID, timezone="America/Chicago"))
    else:
        row.timezone = "America/Chicago"
    db_session.flush()
    assert lab_time.resolve_lab_timezone(db_session) == "America/Chicago"
    monkeypatch.setenv("LAB_TIMEZONE", "Pacific/Honolulu")
    assert lab_time.resolve_lab_timezone(db_session) == "America/Chicago"


def test_invalid_env_does_not_seed(monkeypatch, db_session):
    _clear_lab_timezone(db_session)
    monkeypatch.setenv("LAB_TIMEZONE", "Mars/Olympus_Mons")
    with pytest.raises(lab_time.LabTimezoneUnset) as caught:
        lab_time.resolve_lab_timezone(db_session)
    assert not isinstance(caught.value, lab_time.LabTimezoneInvalid)
    message = str(caught.value)
    assert "lab timezone not configured: set lab_settings.timezone" in message
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    assert row is None or row.timezone is None


def test_missing_env_and_empty_row_refuse(monkeypatch, db_session):
    _clear_lab_timezone(db_session)
    monkeypatch.delenv("LAB_TIMEZONE", raising=False)
    with pytest.raises(lab_time.LabTimezoneUnset) as missing:
        lab_time.resolve_lab_timezone(db_session)
    assert not isinstance(missing.value, lab_time.LabTimezoneInvalid)
    message = str(missing.value)
    assert "lab timezone not configured: set lab_settings.timezone" in message
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).one()
    row.timezone = "   "
    db_session.flush()
    with pytest.raises(lab_time.LabTimezoneUnset, match="lab timezone not configured"):
        lab_time.resolve_lab_timezone(db_session)


def test_corrupt_saved_zone_is_not_replaced(monkeypatch, db_session):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        row = LabSetting(id=LAB_SETTINGS_ID, timezone="Not/AZone")
        db_session.add(row)
    else:
        row.timezone = "Not/AZone"
    db_session.flush()
    with pytest.raises(lab_time.LabTimezoneInvalid) as caught:
        lab_time.resolve_lab_timezone(db_session)
    assert isinstance(caught.value, RuntimeError)
    message = str(caught.value)
    assert "The saved lab timezone 'Not/AZone' is not a known IANA time zone" in message
    assert "UPDATE lab_settings SET timezone = 'America/New_York'" in message
    assert "PATCH /v1/lab-settings" in message
    assert "administrator" in message
    assert "Set LAB_TIMEZONE=" not in message
    db_session.refresh(row)
    assert row.timezone == "Not/AZone"


def test_missing_table_names_migrations():
    class Missing:
        def query(self, *_args, **_kwargs):
            raise ProgrammingError("SELECT", {}, Exception("lab_settings does not exist"))

        def rollback(self):
            self.rolled_back = True

    session = Missing()
    with pytest.raises(RuntimeError, match=r"Run migrations"):
        lab_time.resolve_lab_timezone(session)
    assert session.rolled_back is True


def test_startup_skips_the_database_during_tests(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("LAB_TIMEZONE", raising=False)
    lab_time.require_lab_timezone_on_startup()


def test_startup_resolves_and_commits_the_seed_outside_tests(monkeypatch):
    """Startup does not seed and does not require a zone."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    seen = {}

    def fake_resolve(_db, commit_seed=False):
        seen["called"] = True
        raise AssertionError("startup must not seed or require a zone")

    monkeypatch.setattr(lab_time, "resolve_lab_timezone", fake_resolve)
    lab_time.require_lab_timezone_on_startup()
    assert "called" not in seen


def test_agent_cannot_change_the_lab_timezone():
    classified = allow.classify_call("PATCH", "/v1/lab-settings", {"timezone": "America/New_York"})
    assert classified.ok is False
    assert "No configuration API matches" in classified.gap


@pytest.mark.parametrize("raw", ["Mars/Olympus_Mons", "", "   "])
def test_unknown_zone_is_invalid_timezone(client, test_admin_user, raw):
    headers = _login(client, "admin", "adminpassword")
    response = client.patch("/v1/lab-settings", headers=headers, json={"timezone": raw})
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_timezone"
    assert "America/New_York" in response.json()["detail"]["message"]


def test_admin_updates_and_lab_manager_can_only_read(client, db_session, test_org, test_admin_user, monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "UTC")
    admin = _login(client, "admin", "adminpassword")
    seeded = client.get("/v1/lab-settings", headers=admin)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["timezone"] == "UTC"

    saved = client.patch("/v1/lab-settings", headers=admin, json={"timezone": "America/New_York"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["timezone"] == "America/New_York"
    monkeypatch.setenv("LAB_TIMEZONE", "UTC")
    again = client.get("/v1/lab-settings", headers=admin)
    assert again.json()["timezone"] == "America/New_York"

    _person(db_session, test_org, "lab-manager", "Lab Manager", ["experiment:manage"])
    manager = _login(client, "lab-manager", "pass-word-1")
    seen = client.get("/v1/lab-settings", headers=manager)
    assert seen.status_code == 200, seen.text
    assert seen.json()["timezone"] == "America/New_York"
    changed = client.patch("/v1/lab-settings", headers=manager, json={"timezone": "America/Chicago"})
    assert changed.status_code == 403, changed.text
    assert "Administrator" in changed.json()["detail"]
    assert client.get("/v1/lab-settings", headers=admin).json()["timezone"] == "America/New_York"


@pytest.mark.parametrize(
    "username, role_name, perms",
    [
        ("lab-tech", "Lab Technician", ["experiment:manage"]),
        ("client-user", "Client", ["sample:read"]),
        ("config-editor", "Configuration Editor", ["config:edit"]),
    ],
)
def test_other_roles_cannot_edit_the_timezone(client, db_session, test_org, username, role_name, perms):
    _person(db_session, test_org, username, role_name, perms)
    headers = _login(client, username, "pass-word-1")
    denied = client.get("/v1/lab-settings", headers=headers)
    assert denied.status_code == 403, denied.text
    assert "Lab Manager" in denied.json()["detail"]
    changed = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "America/New_York"})
    assert changed.status_code == 403, changed.text
    assert "Administrator" in changed.json()["detail"]


def test_evening_expiry_and_usable_lots_follow_the_lab_date(client, test_admin_user, monkeypatch):
    headers = _login(client, "admin", "adminpassword")
    monkeypatch.setenv("LAB_TIMEZONE", "UTC")
    vendor = client.post("/v1/vendors", headers=headers, json={"name": f"Vendor {uuid.uuid4().hex[:6]}"}).json()
    reagent = client.post(
        "/v1/reagents",
        headers=headers,
        json={"name": f"Buffer {uuid.uuid4().hex[:6]}", "unit": "mL"},
    ).json()
    lot = client.post(
        "/v1/reagent-lots",
        headers=headers,
        json={
            "reagent_id": reagent["id"],
            "reagent_vendor_id": client.post(
                "/v1/reagent-vendors",
                headers=headers,
                json={"reagent_id": reagent["id"], "vendor_id": vendor["id"], "catalog_number": "B-1"},
            ).json()["id"],
            "lot_number": "EVE-1",
            "expiration_date": "2026-10-18",
            "quantity_received": 10,
            "quantity_remaining": 10,
            "released": True,
        },
    )
    assert lot.status_code == 201, lot.text
    lot_id = lot.json()["id"]

    saved = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "America/New_York"})
    assert saved.status_code == 200, saved.text
    evening = datetime(2026, 10, 19, 0, 30, tzinfo=timezone.utc)  # 8:30 PM EDT on Oct 18
    monkeypatch.setattr(lab_time, "_utcnow", lambda: evening)

    one = client.get(f"/v1/reagent-lots/{lot_id}", headers=headers)
    assert one.status_code == 200, one.text
    assert one.json()["expired"] is False
    usable = client.get("/v1/reagent-lots", headers=headers, params={"usable": "true", "reagent_id": reagent["id"]})
    assert lot_id in {row["id"] for row in usable.json()}
    on_hand = client.get("/v1/reagents", headers=headers)
    mine = next(row for row in on_hand.json() if row["id"] == reagent["id"])
    assert float(mine["quantity_on_hand"]) == 10

    utc = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "UTC"})
    assert utc.status_code == 200, utc.text
    expired = client.get(f"/v1/reagent-lots/{lot_id}", headers=headers)
    assert expired.json()["expired"] is True
    usable_utc = client.get(
        "/v1/reagent-lots", headers=headers, params={"usable": "true", "reagent_id": reagent["id"]}
    )
    assert lot_id not in {row["id"] for row in usable_utc.json()}
    on_hand_utc = client.get("/v1/reagents", headers=headers)
    mine_utc = next(row for row in on_hand_utc.json() if row["id"] == reagent["id"])
    assert float(mine_utc["quantity_on_hand"]) == 0
    assert vendor["id"]


def test_corrupt_saved_zone_is_503_and_patch_repairs_it(client, db_session, test_admin_user, monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        row = LabSetting(id=LAB_SETTINGS_ID, timezone="Not/AZone")
        db_session.add(row)
    else:
        row.timezone = "Not/AZone"
    db_session.flush()
    lab_time.clear_published_lab_zone()
    admin = _login(client, "admin", "adminpassword")
    got = client.get("/v1/lab-settings", headers=admin)
    assert got.status_code == 503, got.text
    detail = got.json()["detail"]
    assert detail["code"] == "lab_timezone_invalid"
    assert "Not/AZone" in detail["message"]
    assert "UPDATE lab_settings SET timezone = 'America/New_York'" in detail["message"]
    assert "PATCH /v1/lab-settings" in detail["message"]
    lots = client.get("/v1/reagent-lots", headers=admin)
    assert lots.status_code == 503, lots.text
    assert lots.json()["detail"]["code"] == "lab_timezone_invalid"
    repaired = client.patch("/v1/lab-settings", headers=admin, json={"timezone": "America/Chicago"})
    assert repaired.status_code == 200, repaired.text
    assert repaired.json()["timezone"] == "America/Chicago"
    again = client.get("/v1/lab-settings", headers=admin)
    assert again.status_code == 200, again.text
    assert again.json()["timezone"] == "America/Chicago"


def _clear_lab_timezone(db_session) -> None:
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        db_session.add(LabSetting(id=LAB_SETTINGS_ID, timezone=None))
    else:
        row.timezone = None
    db_session.flush()
    lab_time.clear_published_lab_zone()


def test_me_reports_timezone_configured_false_when_unset(client, db_session, test_admin_user):
    _clear_lab_timezone(db_session)
    headers = _login(client, "admin", "adminpassword")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["timezone_configured"] is False
    settings = client.get("/v1/lab-settings", headers=headers)
    assert settings.status_code == 200, settings.text
    assert settings.json()["timezone_configured"] is False
    assert settings.json()["timezone"] is None


def test_me_reports_timezone_configured_true_when_set(client, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["timezone_configured"] is True
    saved = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "America/Chicago"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["timezone"] == "America/Chicago"
    assert saved.json()["timezone_configured"] is True
    invalid = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "Not/AZone"})
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["detail"]["code"] == "invalid_timezone"


def test_non_admin_sees_unset_and_cannot_set_the_zone(client, db_session, test_org, test_admin_user):
    _person(db_session, test_org, "lab-tech-tz", "Lab Technician", ["sample:read"])
    _clear_lab_timezone(db_session)
    headers = _login(client, "lab-tech-tz", "pass-word-1")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["timezone_configured"] is False
    denied = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "UTC"})
    assert denied.status_code == 403, denied.text
    assert "Administrator" in denied.json()["detail"]
