"""Required change reasons and void-reason whitespace parity (0119)."""
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError

from app.core.db_errors import pgcode
from models.instrument import (
    InstrumentMaintenanceAudit,
    InstrumentScheduleAudit,
    InstrumentTypeDeactivation,
)
from tests.test_instrument_e2_review_fixes import _seed_schedule_event
from tests.test_instrument_e3_hardening import _grant_if_missing, _run_as_lims_app
from tests.test_instrument_hardening_e1 import _schedule
from tests.test_instrument_tracking import _instrument, _login, _name, _seeded_type


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


_PARITY = (
    ("nbsp", "\u00a0", False),
    ("figure_space", "\u2007", False),
    ("zwsp", "\u200b", True),
    ("bom", "\ufeff", True),
    ("spaces", "   ", False),
    ("tab_newline", "\t\n", False),
)


def test_void_reason_whitespace_parity_api_and_db(
    client, admin_h, test_admin_user, migrated_engine
):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "set first due"},
    )
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    for name, char, visible in _PARITY:
        created = client.post(
            "/v1/instrument-maintenance-events",
            headers=admin_h,
            json={
                "instrument_id": inst["id"],
                "schedule_id": sched["id"],
                "performed_on": date.today().isoformat(),
                "performed_by_user_id": str(test_admin_user.id),
                "passed": True,
            },
        )
        assert created.status_code == 201, created.text
        api = client.patch(
            f"/v1/instrument-maintenance-events/{created.json()['id']}",
            headers=admin_h,
            json={"active": False, "reason": char},
        )
        if visible:
            assert api.status_code == 200, (name, api.text)
        else:
            assert api.status_code == 422, (name, api.text)
            assert api.json()["detail"]["code"] == "void_reason_required"
        ids = _seed_schedule_event(migrated_engine, next_due=date.today())
        try:
            _run_as_lims_app(
                migrated_engine,
                ids["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = false, void_reason = :r WHERE id = :id",
                {"id": ids["event"], "r": char},
            )
            db_ok = True
            db_code = None
        except (IntegrityError, InternalError, ProgrammingError) as exc:
            db_ok = False
            db_code = pgcode(exc)
        assert db_ok is visible, (name, db_ok, db_code)
        if not visible:
            assert db_code == "23514", (name, db_code)


def test_first_due_whitespace_only_reason_is_required(client, admin_h):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    missing = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat()},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "schedule_change_reason_required"
    blank = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "\u00a0"},
    )
    assert blank.status_code == 422, blank.text
    assert blank.json()["detail"]["code"] == "schedule_change_reason_required"


def test_schedule_change_requires_reason_and_writes_audit(
    client, admin_h, db_session
):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    missing = client.patch(
        f"/v1/instrument-maintenance-schedules/{sched['id']}",
        headers=admin_h,
        json={"interval_days": 20},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "schedule_change_reason_required"
    ok = client.patch(
        f"/v1/instrument-maintenance-schedules/{sched['id']}",
        headers=admin_h,
        json={"interval_days": 20, "reason": "  interval review  "},
    )
    assert ok.status_code == 200, ok.text
    db_session.expire_all()
    rows = (
        db_session.query(InstrumentScheduleAudit)
        .filter(
            InstrumentScheduleAudit.schedule_id == sched["id"],
            InstrumentScheduleAudit.action == "schedule_interval",
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].reason == "interval review"


def test_maintenance_tracked_change_requires_reason_and_writes_audit(
    client, admin_h, db_session
):
    inst = _instrument(client, admin_h, maintenance_tracked=False)
    missing = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "maintenance_tracked_reason_required"
    ok = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True, "reason": "lab now tracks this"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["maintenance_tracked"] is True
    db_session.expire_all()
    rows = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == UUID(inst["id"]))
        .all()
    )
    seen = [
        (r.previous_value, r.new_value, r.reason) for r in rows
    ]
    changed = [
        r
        for r in rows
        if r.previous_value is False and r.new_value is True
    ]
    assert len(changed) == 1, seen
    assert changed[0].reason == "lab now tracks this"


def test_type_deactivate_requires_reason_and_writes_ledger(client, admin_h, db_session):
    created = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("ToRetire")},
    )
    assert created.status_code == 201, created.text
    type_id = created.json()["id"]
    missing = client.patch(
        f"/v1/instrument-types/{type_id}",
        headers=admin_h,
        json={"active": False},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "instrument_type_deactivate_reason_required"
    lists = client.patch(
        f"/lists/instrument_types/entries/{type_id}",
        headers=admin_h,
        json={"active": False},
    )
    assert lists.status_code == 422, lists.text
    assert lists.json()["detail"]["code"] == "instrument_type_deactivate_reason_required"
    ok = client.patch(
        f"/v1/instrument-types/{type_id}",
        headers=admin_h,
        json={"active": False, "reason": "no longer used"},
    )
    assert ok.status_code == 200, ok.text
    db_session.expire_all()
    rows = (
        db_session.query(InstrumentTypeDeactivation)
        .filter(InstrumentTypeDeactivation.instrument_type_id == type_id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].reason == "no longer used"


def test_admin_create_tracked_true_writes_schedule_audit_not_maintenance(
    client, admin_h, db_session, test_admin_user
):
    type_id = _seeded_type(client, admin_h)["id"]
    created = client.post(
        "/v1/instruments",
        headers=admin_h,
        json={
            "name": _name("CreateTrue"),
            "instrument_type_id": type_id,
            "maintenance_tracked": True,
        },
    )
    assert created.status_code == 201, created.text
    instrument_id = UUID(created.json()["id"])
    db_session.expire_all()
    maint = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == instrument_id)
        .all()
    )
    assert maint == []
    rows = (
        db_session.query(InstrumentScheduleAudit)
        .filter(
            InstrumentScheduleAudit.instrument_id == instrument_id,
            InstrumentScheduleAudit.action == "maintenance_tracked",
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].previous_value is None
    assert rows[0].new_value == "true"
    assert rows[0].reason is None
    assert rows[0].schedule_id is None
    assert rows[0].event_id is None
    assert rows[0].created_by == test_admin_user.id
    assert rows[0].created_at is not None


def test_create_tracked_schedule_audit_stays_append_only(migrated_engine):
    from sqlalchemy import text

    with migrated_engine.connect() as conn:
        for privilege in ("UPDATE", "DELETE"):
            allowed = conn.execute(
                text(
                    "SELECT has_table_privilege('lims_app', "
                    "'instrument_schedule_audits', :p)"
                ),
                {"p": privilege},
            ).scalar()
            assert allowed is False, privilege
        for privilege in ("UPDATE", "DELETE"):
            allowed = conn.execute(
                text(
                    "SELECT has_table_privilege('lims_app', "
                    "'instrument_type_deactivations', :p)"
                ),
                {"p": privilege},
            ).scalar()
            assert allowed is False, privilege
        insert_ok = conn.execute(
            text(
                "SELECT has_table_privilege('lims_app', "
                "'instrument_type_deactivations', 'INSERT')"
            )
        ).scalar()
        assert insert_ok is True


def test_admin_create_tracked_false_writes_no_schedule_tracked_audit(
    client, admin_h, db_session
):
    type_id = _seeded_type(client, admin_h)["id"]
    created = client.post(
        "/v1/instruments",
        headers=admin_h,
        json={
            "name": _name("CreateFalse"),
            "instrument_type_id": type_id,
            "maintenance_tracked": False,
        },
    )
    assert created.status_code == 201, created.text
    instrument_id = UUID(created.json()["id"])
    db_session.expire_all()
    rows = (
        db_session.query(InstrumentScheduleAudit)
        .filter(
            InstrumentScheduleAudit.instrument_id == instrument_id,
            InstrumentScheduleAudit.action == "maintenance_tracked",
        )
        .all()
    )
    assert rows == []
    maint = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == instrument_id)
        .all()
    )
    assert len(maint) == 1
    assert maint[0].previous_value is False
    assert maint[0].new_value is False
    assert maint[0].reason is None


def test_downtime_refuses_a_voided_maintenance_event(client, admin_h, test_admin_user):
    from datetime import datetime, timezone

    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "set first due"},
    )
    event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert event.status_code == 201, event.text
    event_id = event.json()["id"]
    later = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert later.status_code == 201, later.text
    reason = client.get("/lists/downtime_reasons/entries", headers=admin_h).json()
    if isinstance(reason, dict):
        reason = reason.get("entries") or reason.get("items") or []
    reason_id = next(row["id"] for row in reason if row["name"] == "Breakdown")
    started = datetime.now(timezone.utc).isoformat()
    linked = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": started,
            "reason_id": reason_id,
            "maintenance_event_id": event_id,
        },
    )
    assert linked.status_code == 201, linked.text
    voided = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False, "reason": "wrong date"},
    )
    assert voided.status_code == 200, voided.text
    keep = client.patch(
        f"/v1/instrument-downtime/{linked.json()['id']}",
        headers=admin_h,
        json={"note": "still linked after void"},
    )
    assert keep.status_code == 200, keep.text
    assert keep.json()["maintenance_event_id"] == event_id
    create_voided = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": started,
            "reason_id": reason_id,
            "maintenance_event_id": event_id,
        },
    )
    assert create_voided.status_code == 422, create_voided.text
    assert create_voided.json()["detail"]["code"] == "maintenance_event_voided"
    retarget = client.patch(
        f"/v1/instrument-downtime/{linked.json()['id']}",
        headers=admin_h,
        json={"maintenance_event_id": later.json()["id"]},
    )
    assert retarget.status_code == 200, retarget.text
    void_later = client.patch(
        f"/v1/instrument-maintenance-events/{later.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "also wrong"},
    )
    assert void_later.status_code == 200, void_later.text
    back = client.patch(
        f"/v1/instrument-downtime/{linked.json()['id']}",
        headers=admin_h,
        json={"maintenance_event_id": event_id},
    )
    assert back.status_code == 422, back.text
    assert back.json()["detail"]["code"] == "maintenance_event_voided"
