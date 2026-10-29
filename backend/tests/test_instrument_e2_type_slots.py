"""E2 instrument type slots, run snapshot, substitution, Günter created_by."""
import threading
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from app.core.db_errors import pgcode
from app.services import configuring_agent_allow as allow
from app.services.configuring_agent_apply import CannotExpress, execute_step
from models.flexible_experiment import LimsRunImport, LimsRunTypeSubstitution
from models.instrument import InstrumentScheduleAudit
from tests.test_flexible_experiment import PLATE_READER_TYPE_ID, VALID_TEMPLATE_DEF
from tests.test_instrument_hardening_e1 import _role_user, _run_as_lims_app
from tests.test_instrument_tracking import (
    _instrument,
    _login,
    _name,
    _seeded_type,
)


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _typed_def(type_id=PLATE_READER_TYPE_ID, key="run_import"):
    return {
        **VALID_TEMPLATE_DEF,
        "entries": [
            {
                "entry_type": "instrument",
                "predefined_entry_key": "instruments",
                "name": "Instruments",
                "config": {
                    "slots": [
                        {
                            "key": key,
                            "label": "Import instrument",
                            "instrument_type_id": type_id,
                            "required": True,
                            "run_import": True,
                        }
                    ]
                },
            }
        ],
    }


def _create_template(client, headers, definition=None, name=None):
    r = client.post(
        "/v1/experiment-templates",
        headers=headers,
        json={
            "name": name or _name("T"),
            "template_definition": definition or _typed_def(),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_run(client, headers, template_id, analysis_id, name=None):
    r = client.post(
        "/v1/lims-runs",
        headers=headers,
        json={
            "name": name or _name("Run"),
            "experiment_template_id": template_id,
            "analysis_id": analysis_id,
        },
    )
    return r


def _start_run(client, headers, run_id, sample_id, **extra):
    return client.patch(
        f"/v1/lims-runs/{run_id}/start",
        headers=headers,
        json={"sample_ids": [sample_id], **extra},
    )


def test_run_import_slot_requires_type(client, admin_h):
    definition = _typed_def()
    definition["entries"][0]["config"]["slots"][0]["instrument_type_id"] = None
    r = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("NoType"), "template_definition": definition},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "instrument_entry_invalid"


def test_at_most_one_run_import_slot(client, admin_h):
    definition = _typed_def()
    definition["entries"][0]["config"]["slots"].append(
        {
            "key": "other",
            "label": "Second",
            "instrument_type_id": PLATE_READER_TYPE_ID,
            "required": False,
            "run_import": True,
        }
    )
    r = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("Two"), "template_definition": definition},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "instrument_entry_invalid"


def test_optional_slot_type_and_inactive_type_refused(client, admin_h):
    extra = {
        "key": "balance",
        "label": "Balance",
        "required": False,
        "run_import": False,
    }
    definition = _typed_def()
    definition["entries"][0]["config"]["slots"].append(extra)
    ok = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("Opt"), "template_definition": definition},
    )
    assert ok.status_code == 201, ok.text
    inactive = client.post(
        "/v1/instrument-types", headers=admin_h, json={"name": _name("Dead"), "active": False}
    )
    assert inactive.status_code == 201, inactive.text
    definition["entries"][0]["config"]["slots"][1]["instrument_type_id"] = inactive.json()["id"]
    bad = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("BadType"), "template_definition": definition},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["detail"]["code"] == "instrument_entry_invalid"


def test_create_run_requires_typed_run_import(client, admin_h, run_analysis_id):
    template = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={
            "name": _name("Bare"),
            "template_definition": {
                "experiment_name": "Bare",
                "description": "no slots",
                "protocol_steps": [],
            },
        },
    )
    assert template.status_code == 201, template.text
    r = _create_run(client, admin_h, template.json()["id"], run_analysis_id)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "run_template_type_required"


def test_start_copies_template_run_import_type(
    client, admin_h, run_analysis_id, cohort_sample_id
):
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert created.status_code == 201, created.text
    assert created.json()["instrument_type_id"] is None
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    assert started.json()["instrument_type_id"] == PLATE_READER_TYPE_ID
    assert started.json()["instrument_type_name"] == "Plate reader"


def test_run_import_type_locked_once_referenced(
    client, admin_h, run_analysis_id
):
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert created.status_code == 201, created.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    locked = client.patch(
        f"/v1/experiment-templates/{template['id']}",
        headers=admin_h,
        json={"template_definition": _typed_def(qpcr["id"])},
    )
    assert locked.status_code == 422, locked.text
    assert locked.json()["detail"]["code"] == "run_import_type_locked"


def test_setting_type_on_template_that_had_none_is_allowed(
    client, admin_h, run_analysis_id
):
    """A template without a run_import type can gain one even if a run exists.

    create_run now requires a typed slot, so this uses a template that is
    later given a first type via PATCH after we attach a run through SQL-free
    create of an already-typed template... skipped: create_run refuses
    untyped. Setting-none-to-some is covered by PATCH on a template that
    already has a typed slot? That would be a change. Instead: template with
    optional other slots only cannot create_run. The allowed path is a
    template with a run_import slot that has no type — but create/update
    refuse that. The remaining allowed case is adding a run_import slot
    (with type) to a template that had none, after a run was created before
    E2. Simulate by creating a run from a typed template, then PATCH that
    keeps the same type (not a lock). The none→some case is PATCH of a
    template that is not yet referenced.
    """
    template = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={
            "name": _name("Later"),
            "template_definition": {
                "experiment_name": "Later",
                "description": "gain type",
                "protocol_steps": [],
                "entries": [
                    {
                        "entry_type": "instrument",
                        "predefined_entry_key": "instruments",
                        "name": "Instruments",
                        "config": {"slots": []},
                    }
                ],
            },
        },
    )
    assert template.status_code == 201, template.text
    patched = client.patch(
        f"/v1/experiment-templates/{template.json()['id']}",
        headers=admin_h,
        json={"template_definition": _typed_def()},
    )
    assert patched.status_code == 200, patched.text


def test_referenced_template_may_gain_first_run_import_type(
    client, admin_h, db_session, test_admin_user, run_analysis_id
):
    from models.experiment import ExperimentTemplate
    from models.flexible_experiment import LimsRun

    template = ExperimentTemplate(
        name=_name("UntypedRef"),
        template_definition={
            "experiment_name": "UntypedRef",
            "description": "gain type while referenced",
            "protocol_steps": [],
            "entries": [
                {
                    "entry_type": "instrument",
                    "predefined_entry_key": "instruments",
                    "name": "Instruments",
                    "config": {"slots": []},
                }
            ],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(template)
    db_session.flush()
    db_session.add(
        LimsRun(
            name=_name("RefRun"),
            experiment_template_id=template.id,
            analysis_id=run_analysis_id,
            created_by=test_admin_user.id,
        )
    )
    db_session.commit()
    patched = client.patch(
        f"/v1/experiment-templates/{template.id}",
        headers=admin_h,
        json={"template_definition": _typed_def()},
    )
    assert patched.status_code == 200, patched.text


def test_update_run_cannot_change_instrument_type(
    client, admin_h, run_analysis_id, cohort_sample_id
):
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    locked = client.patch(
        f"/v1/lims-runs/{created.json()['id']}",
        headers=admin_h,
        json={"instrument_type_id": qpcr["id"]},
    )
    assert locked.status_code == 409, locked.text
    assert locked.json()["detail"]["code"] == "run_type_locked"


def test_ad_hoc_run_requires_type_at_start(
    client, admin_h, run_analysis_id, cohort_sample_id
):
    created = client.post(
        "/v1/lims-runs",
        headers=admin_h,
        json={"name": _name("Adhoc"), "analysis_id": run_analysis_id},
    )
    assert created.status_code == 201, created.text
    missing = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "run_type_required"
    started = _start_run(
        client,
        admin_h,
        created.json()["id"],
        cohort_sample_id,
        instrument_type_id=PLATE_READER_TYPE_ID,
    )
    assert started.status_code == 200, started.text
    assert started.json()["instrument_type_id"] == PLATE_READER_TYPE_ID


def test_eligible_picker_filters_server_side(client, admin_h):
    live = _instrument(client, admin_h)
    retired = _instrument(client, admin_h, status="retired")
    listed = client.get(
        f"/v1/instruments?instrument_type_id={live['instrument_type_id']}&eligible=true",
        headers=admin_h,
    )
    assert listed.status_code == 200, listed.text
    ids = {row["id"] for row in listed.json()}
    assert live["id"] in ids
    assert retired["id"] not in ids


def test_changing_slot_pick_voids_old_row(
    client, admin_h, db_session, test_admin_user
):
    from models.experiment import Experiment
    from models.entry import Entry

    type_id = _seeded_type(client, admin_h)["id"]
    first = _instrument(client, admin_h, instrument_type_id=type_id)
    second = _instrument(client, admin_h, instrument_type_id=type_id)
    exp = Experiment(name=_name("Exp"), created_by=test_admin_user.id, modified_by=test_admin_user.id)
    db_session.add(exp)
    db_session.flush()
    entry = Entry(
        experiment_id=exp.id,
        entry_type="instrument",
        name="Instruments",
        predefined_entry_key="instruments",
        sort_order=0,
        config={
            "slots": [
                {
                    "key": "reader",
                    "label": "Reader",
                    "instrument_type_id": type_id,
                    "required": True,
                    "run_import": False,
                }
            ],
            "allowed_instrument_ids": [first["id"], second["id"]],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(entry)
    db_session.commit()
    one = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": first["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert one.status_code == 201, one.text
    two = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": second["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert two.status_code == 201, two.text
    listed = client.get(
        f"/v1/instrument-uses?experiment_id={exp.id}&include_voided=true",
        headers=admin_h,
    )
    rows = listed.json()
    active = [r for r in rows if r["active"]]
    voided = [r for r in rows if not r["active"]]
    assert len(active) == 1
    assert active[0]["instrument_id"] == second["id"]
    assert len(voided) == 1
    assert voided[0]["instrument_id"] == first["id"]


def test_entry_slot_type_change_voids_use_and_does_not_change_template(
    client, admin_h, db_session, test_admin_user
):
    from models.experiment import Experiment, ExperimentTemplate
    from models.entry import Entry
    from models.instrument import InstrumentEntrySlotAudit, InstrumentUse

    plate = _seeded_type(client, admin_h, "Plate reader")
    qpcr = _seeded_type(client, admin_h, "qPCR")
    reader = _instrument(client, admin_h, instrument_type_id=plate["id"])
    template = ExperimentTemplate(
        name=_name("Keep"),
        template_definition=_typed_def(plate["id"]),
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(template)
    db_session.flush()
    exp = Experiment(
        name=_name("ExpSlots"),
        experiment_template_id=template.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(exp)
    db_session.flush()
    entry = Entry(
        experiment_id=exp.id,
        entry_type="instrument",
        name="Instruments",
        predefined_entry_key="instruments",
        sort_order=0,
        config={
            "slots": [
                {
                    "key": "reader",
                    "label": "Reader",
                    "instrument_type_id": plate["id"],
                    "required": True,
                    "run_import": False,
                }
            ],
            "allowed_instrument_ids": [reader["id"]],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(entry)
    db_session.commit()
    used = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": reader["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert used.status_code == 201, used.text
    patched = client.patch(
        f"/v1/entries/{entry.id}",
        headers=admin_h,
        json={
            "config": {
                "slots": [
                    {
                        "key": "reader",
                        "label": "Cycler",
                        "instrument_type_id": qpcr["id"],
                        "required": True,
                        "run_import": False,
                    }
                ],
                "allowed_instrument_ids": [reader["id"]],
            }
        },
    )
    assert patched.status_code == 200, patched.text
    db_session.expire_all()
    use_row = db_session.query(InstrumentUse).filter(InstrumentUse.id == used.json()["id"]).one()
    assert use_row.active is False
    kept = db_session.query(ExperimentTemplate).filter(ExperimentTemplate.id == template.id).one()
    assert kept.template_definition["entries"][0]["config"]["slots"][0]["instrument_type_id"] == plate["id"]
    audits = (
        db_session.query(InstrumentEntrySlotAudit)
        .filter(InstrumentEntrySlotAudit.entry_id == entry.id)
        .all()
    )
    assert len(audits) == 1
    assert audits[0].slot_key == "reader"
    assert str(audits[0].previous_instrument_type_id) == plate["id"]
    assert str(audits[0].new_instrument_type_id) == qpcr["id"]
    assert audits[0].created_by == test_admin_user.id


def test_use_type_mismatch_and_missing_slot(
    client, admin_h, db_session, test_admin_user
):
    from models.experiment import Experiment
    from models.entry import Entry

    plate = _seeded_type(client, admin_h, "Plate reader")
    qpcr = _seeded_type(client, admin_h, "qPCR")
    reader = _instrument(client, admin_h, instrument_type_id=plate["id"])
    cycler = _instrument(client, admin_h, instrument_type_id=qpcr["id"])
    exp = Experiment(name=_name("Exp"), created_by=test_admin_user.id, modified_by=test_admin_user.id)
    db_session.add(exp)
    db_session.flush()
    entry = Entry(
        experiment_id=exp.id,
        entry_type="instrument",
        name="Instruments",
        predefined_entry_key="instruments",
        sort_order=0,
        config={
            "slots": [
                {
                    "key": "reader",
                    "label": "Reader",
                    "instrument_type_id": plate["id"],
                    "required": True,
                }
            ],
            "allowed_instrument_ids": [reader["id"], cycler["id"]],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(entry)
    db_session.commit()
    mismatch = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": cycler["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert mismatch.status_code == 422, mismatch.text
    assert mismatch.json()["detail"]["code"] == "instrument_type_mismatch"
    missing = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": reader["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "nope",
        },
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "instrument_slot_not_found"


def test_import_type_mismatch_and_admin_override_note(
    client,
    admin_h,
    db_session,
    test_admin_user,
    run_analysis_id,
    cohort_sample_id,
):
    from models.flexible_experiment import DataParser, ParserAnalysis

    qpcr = _seeded_type(client, admin_h, "qPCR")
    other = _instrument(client, admin_h, instrument_type_id=qpcr["id"])
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    parser = DataParser(
        name=_name("P"),
        parser_config={
            "columns": [{"source_col": "Well", "field_name": "well", "data_type": "string"}],
            "well_col": "Well",
        },
        instrument_id=other["id"],
        version_group_id=uuid.uuid4(),
        version=1,
        active=True,
    )
    db_session.add(parser)
    db_session.flush()
    db_session.add(
        ParserAnalysis(parser_id=parser.id, analysis_id=run_analysis_id, is_default=True)
    )
    db_session.commit()
    mismatch = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "instrument_id": other["id"],
            "parser_id": str(parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert mismatch.status_code == 422, mismatch.text
    assert mismatch.json()["detail"]["code"] == "instrument_type_mismatch"
    assert db_session.query(LimsRunImport).filter(
        LimsRunImport.lims_run_id == created.json()["id"]
    ).count() == 0
    override = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={"rows": [{"well_position": "A1", "row_data": {"well": "A1"}}]},
    )
    assert override.status_code == 200, override.text
    row = (
        db_session.query(LimsRunImport)
        .filter(LimsRunImport.lims_run_id == created.json()["id"])
        .one()
    )
    assert row.filename == "admin_override"
    assert row.note == "type not checked"


def test_tech_substitutes_own_run_and_refuses_other(
    client, admin_h, db_session, test_org, run_analysis_id, cohort_sample_id
):
    tech = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    other = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    manager = _role_user(db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",))
    tech_h = _login(client, tech.username, "pass-word-1")
    other_h = _login(client, other.username, "pass-word-1")
    mgr_h = _login(client, manager.username, "pass-word-1")
    template = _create_template(client, admin_h)
    own = _create_run(client, tech_h, template["id"], run_analysis_id)
    assert own.status_code == 201, own.text
    started = _start_run(client, admin_h, own.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    ok = client.post(
        f"/v1/lims-runs/{own.json()['id']}/substitute-instrument-type",
        headers=tech_h,
        json={"instrument_type_id": qpcr["id"], "reason": "backup reader"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["instrument_type_id"] == qpcr["id"]
    rows = (
        db_session.query(LimsRunTypeSubstitution)
        .filter(LimsRunTypeSubstitution.lims_run_id == own.json()["id"])
        .all()
    )
    assert len(rows) == 1
    assert rows[0].created_by == tech.id
    assert rows[0].from_instrument_type_id == uuid.UUID(PLATE_READER_TYPE_ID)
    assert rows[0].to_instrument_type_id == uuid.UUID(qpcr["id"])
    assert rows[0].reason == "backup reader"
    someone = _create_run(client, other_h, template["id"], run_analysis_id)
    assert someone.status_code == 201, someone.text
    refused = client.post(
        f"/v1/lims-runs/{someone.json()['id']}/substitute-instrument-type",
        headers=tech_h,
        json={"instrument_type_id": qpcr["id"], "reason": "not mine"},
    )
    assert refused.status_code == 403, refused.text
    mgr_ok = client.post(
        f"/v1/lims-runs/{someone.json()['id']}/substitute-instrument-type",
        headers=mgr_h,
        json={"instrument_type_id": qpcr["id"], "reason": "manager override"},
    )
    assert mgr_ok.status_code == 200, mgr_ok.text


def test_substitute_refuses_inactive_type_and_terminal_run(
    client, admin_h, run_analysis_id, cohort_sample_id
):
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    inactive = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("Gone"), "active": False},
    )
    dead = client.post(
        f"/v1/lims-runs/{created.json()['id']}/substitute-instrument-type",
        headers=admin_h,
        json={"instrument_type_id": inactive.json()["id"], "reason": "no"},
    )
    assert dead.status_code == 422, dead.text
    failed = client.post(
        f"/v1/lims-runs/{created.json()['id']}/fail",
        headers=admin_h,
        json={"reason": "stop"},
    )
    assert failed.status_code == 200, failed.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    terminal = client.post(
        f"/v1/lims-runs/{created.json()['id']}/substitute-instrument-type",
        headers=admin_h,
        json={"instrument_type_id": qpcr["id"], "reason": "too late"},
    )
    assert terminal.status_code == 422, terminal.text
    assert terminal.json()["detail"]["code"] == "run_terminal"


def test_import_after_substitution_uses_new_type(
    client,
    admin_h,
    db_session,
    run_analysis_id,
    cohort_sample_id,
):
    from models.flexible_experiment import DataParser, ParserAnalysis

    plate = _seeded_type(client, admin_h, "Plate reader")
    qpcr = _seeded_type(client, admin_h, "qPCR")
    plate_inst = _instrument(client, admin_h, instrument_type_id=plate["id"])
    qpcr_inst = _instrument(client, admin_h, instrument_type_id=qpcr["id"])
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    cfg = {
        "columns": [{"source_col": "Well", "field_name": "well", "data_type": "string"}],
        "well_col": "Well",
    }
    plate_parser = DataParser(
        name=_name("PlateP"),
        parser_config=cfg,
        instrument_id=plate_inst["id"],
        version_group_id=uuid.uuid4(),
        version=1,
        active=True,
    )
    qpcr_parser = DataParser(
        name=_name("QpcP"),
        parser_config=cfg,
        instrument_id=qpcr_inst["id"],
        version_group_id=uuid.uuid4(),
        version=1,
        active=True,
    )
    db_session.add_all([plate_parser, qpcr_parser])
    db_session.flush()
    db_session.add_all(
        [
            ParserAnalysis(parser_id=plate_parser.id, analysis_id=run_analysis_id, is_default=True),
            ParserAnalysis(parser_id=qpcr_parser.id, analysis_id=run_analysis_id, is_default=True),
        ]
    )
    db_session.commit()
    sub = client.post(
        f"/v1/lims-runs/{created.json()['id']}/substitute-instrument-type",
        headers=admin_h,
        json={"instrument_type_id": qpcr["id"], "reason": "swap for qpcr"},
    )
    assert sub.status_code == 200, sub.text
    old = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "instrument_id": plate_inst["id"],
            "parser_id": str(plate_parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert old.status_code == 422, old.text
    assert old.json()["detail"]["code"] == "instrument_type_mismatch"
    new = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "instrument_id": qpcr_inst["id"],
            "parser_id": str(qpcr_parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert new.status_code == 200, new.text


def test_parser_type_scoped_mismatch(client, admin_h, db_session, run_analysis_id, cohort_sample_id):
    from models.flexible_experiment import DataParser, ParserAnalysis

    qpcr = _seeded_type(client, admin_h, "qPCR")
    plate_inst = _instrument(client, admin_h)
    parser = DataParser(
        name=_name("Q"),
        parser_config={
            "columns": [{"source_col": "Well", "field_name": "well", "data_type": "string"}],
            "well_col": "Well",
        },
        instrument_type_id=qpcr["id"],
        version_group_id=uuid.uuid4(),
        version=1,
        active=True,
    )
    db_session.add(parser)
    db_session.flush()
    db_session.add(
        ParserAnalysis(parser_id=parser.id, analysis_id=run_analysis_id, is_default=True)
    )
    db_session.commit()
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    r = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "instrument_id": plate_inst["id"],
            "parser_id": str(parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "instrument_type_mismatch"


def test_agent_can_set_run_import_type_and_refuses_substitute_and_uses():
    body = {
        "name": "Typed",
        "template_definition": _typed_def(),
    }
    classified = allow.classify_call("POST", "/v1/experiment-templates", body)
    assert classified.ok is True
    assert allow.needs_second_confirm("POST", "/v1/experiment-templates", body, classified.kind)
    sub = allow.classify_call(
        "POST",
        "/v1/lims-runs/00000000-0000-4000-8000-000000000001/substitute-instrument-type",
        {"instrument_type_id": PLATE_READER_TYPE_ID, "reason": "no"},
    )
    assert sub.ok is False
    assert "cannot substitute" in (sub.gap or "")
    use = allow.classify_call("POST", "/v1/instrument-uses", {"instrument_id": "x"})
    assert use.ok is False


def test_agent_apply_refuses_substitute(db_session, test_admin_user):
    with pytest.raises(CannotExpress):
        execute_step(
            db_session,
            test_admin_user,
            "POST",
            "/v1/lims-runs/00000000-0000-4000-8000-000000000001/substitute-instrument-type",
            {"instrument_type_id": PLATE_READER_TYPE_ID, "reason": "no"},
        )


def test_substitution_table_append_only_as_lims_app(migrated_engine):
    with migrated_engine.begin() as conn:
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e2a', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e2a-{uid.hex[:6]}",
                "e": f"e2a-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :u, :u)"
            ),
            {"id": run_id, "n": f"e2r-{run_id.hex[:6]}", "u": uid},
        )
        sub = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_type_substitutions "
                "(id, lims_run_id, from_instrument_type_id, to_instrument_type_id, reason, created_by) "
                "VALUES (:id, :r, :t, :t, 'seed', :u)"
            ),
            {"id": sub, "r": run_id, "t": type_id, "u": uid},
        )
    with migrated_engine.connect() as conn:
        for privilege in ("UPDATE", "DELETE"):
            allowed = conn.execute(
                text("SELECT has_table_privilege('lims_app', 'lims_run_type_substitutions', :p)"),
                {"p": privilege},
            ).scalar()
            assert allowed is False, privilege
        assert conn.execute(
            text("SELECT has_table_privilege('lims_app', 'lims_run_type_substitutions', 'INSERT')")
        ).scalar() is True
    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "UPDATE lims_run_type_substitutions SET reason = 'x' WHERE id = :id",
            {"id": sub},
        )
    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "DELETE FROM lims_run_type_substitutions WHERE id = :id",
            {"id": sub},
        )


def test_audit_insert_created_by_must_match_session(migrated_engine):
    with migrated_engine.begin() as conn:
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        other = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e2c', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e2c-{uid.hex[:6]}",
                "e": f"e2c-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e2o', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": other,
                "u": f"e2o-{other.hex[:6]}",
                "e": f"e2o-{other.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        inst = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, true, :u, :u)"
            ),
            {"id": inst, "n": f"E2c-{inst.hex[:6]}", "t": type_id, "u": uid},
        )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :u, :u)"
            ),
            {"id": run_id, "n": f"e2s-{run_id.hex[:6]}", "u": uid},
        )
    insert_maint = (
        "INSERT INTO instrument_maintenance_audits "
        "(id, instrument_id, previous_value, new_value, reason, created_by) "
        "VALUES (:id, :i, true, false, 'x', :u)"
    )
    insert_sched = (
        "INSERT INTO instrument_schedule_audits "
        "(id, instrument_id, action, reason, created_by) "
        "VALUES (:id, :i, 'first_due', 'x', :u)"
    )
    insert_sub = (
        "INSERT INTO lims_run_type_substitutions "
        "(id, lims_run_id, to_instrument_type_id, reason, created_by) "
        "VALUES (:id, :r, :t, 'x', :u)"
    )
    for sql, params in (
        (insert_maint, {"id": uuid.uuid4(), "i": inst, "u": other}),
        (insert_sched, {"id": uuid.uuid4(), "i": inst, "u": other}),
        (insert_sub, {"id": uuid.uuid4(), "r": run_id, "t": type_id, "u": other}),
        (insert_maint, {"id": uuid.uuid4(), "i": inst, "u": None}),
        (insert_sched, {"id": uuid.uuid4(), "i": inst, "u": None}),
        (insert_sub, {"id": uuid.uuid4(), "r": run_id, "t": type_id, "u": None}),
    ):
        with pytest.raises(ProgrammingError) as raised:
            _run_as_lims_app(migrated_engine, uid, sql, params)
        assert pgcode(raised.value) == "42501"
    _run_as_lims_app(
        migrated_engine,
        uid,
        insert_maint,
        {"id": uuid.uuid4(), "i": inst, "u": uid},
    )
    _run_as_lims_app(
        migrated_engine,
        uid,
        insert_sched,
        {"id": uuid.uuid4(), "i": inst, "u": uid},
    )
    _run_as_lims_app(
        migrated_engine,
        uid,
        insert_sub,
        {"id": uuid.uuid4(), "r": run_id, "t": type_id, "u": uid},
    )


def test_first_due_and_void_accept_reason(client, admin_h, db_session):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    kind = client.get("/lists/maintenance_types/entries", headers=admin_h).json()
    if isinstance(kind, dict):
        kind = kind.get("entries") or kind.get("items") or []
    kind_id = next(row["id"] for row in kind if row["name"] == "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind_id, "interval_days": 10},
    )
    assert sched.status_code == 201, sched.text
    first = client.post(
        f"/v1/instrument-maintenance-schedules/{sched.json()['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "initial due"},
    )
    assert first.status_code == 200, first.text
    from models.user import User

    admin = db_session.query(User).filter(User.username == "admin").first()
    event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched.json()["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(admin.id),
            "passed": True,
        },
    )
    assert event.status_code == 201, event.text
    voided = client.patch(
        f"/v1/instrument-maintenance-events/{event.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "void reason"},
    )
    assert voided.status_code == 200, voided.text
    audits = (
        db_session.query(InstrumentScheduleAudit)
        .filter(InstrumentScheduleAudit.instrument_id == inst["id"])
        .all()
    )
    first_due = [a for a in audits if a.action == "first_due"]
    voids = [a for a in audits if a.action == "event_void"]
    assert first_due and first_due[0].reason == "initial due"
    assert voids and voids[0].reason == "void reason"


def test_update_schedule_audits_kind_and_service_vendor(client, admin_h, db_session):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    kinds = client.get("/lists/maintenance_types/entries", headers=admin_h).json()
    if isinstance(kinds, dict):
        kinds = kinds.get("entries") or kinds.get("items") or []
    pm = next(row["id"] for row in kinds if row["name"] == "PM")
    cal = next(row["id"] for row in kinds if row["name"] == "calibration")
    vendor = client.post("/v1/vendors", headers=admin_h, json={"name": _name("Metrology")})
    assert vendor.status_code == 201, vendor.text
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": pm, "interval_days": 30},
    )
    assert sched.status_code == 201, sched.text
    changed = client.patch(
        f"/v1/instrument-maintenance-schedules/{sched.json()['id']}",
        headers=admin_h,
        json={
            "kind_id": cal,
            "service_vendor_id": vendor.json()["id"],
            "reason": "kind and vendor change",
        },
    )
    assert changed.status_code == 200, changed.text
    audits = (
        db_session.query(InstrumentScheduleAudit)
        .filter(InstrumentScheduleAudit.schedule_id == sched.json()["id"])
        .all()
    )
    kind_rows = [a for a in audits if a.action == "schedule_kind"]
    vendor_rows = [a for a in audits if a.action == "schedule_vendor"]
    assert len(kind_rows) == 1
    assert kind_rows[0].previous_value == pm
    assert kind_rows[0].new_value == cal
    assert kind_rows[0].created_by is not None
    assert kind_rows[0].created_at is not None
    assert kind_rows[0].reason == "kind and vendor change"
    assert len(vendor_rows) == 1
    assert vendor_rows[0].previous_value is None
    assert vendor_rows[0].new_value == vendor.json()["id"]
    assert vendor_rows[0].reason == "kind and vendor change"


def test_tech_cannot_void_only_passing_event_manager_can(
    client, admin_h, db_session, test_org
):
    from models.user import User

    tech = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    manager = _role_user(db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",))
    tech_h = _login(client, tech.username, "pass-word-1")
    mgr_h = _login(client, manager.username, "pass-word-1")
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    kinds = client.get("/lists/maintenance_types/entries", headers=admin_h).json()
    if isinstance(kinds, dict):
        kinds = kinds.get("entries") or kinds.get("items") or []
    kind_id = next(row["id"] for row in kinds if row["name"] == "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind_id, "interval_days": 10},
    ).json()
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "set first due"},
    )
    admin = db_session.query(User).filter(User.username == "admin").first()
    created = client.post(
        "/v1/instrument-maintenance-events",
        headers=tech_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(tech.id),
            "passed": True,
        },
    )
    assert created.status_code == 201, created.text
    only = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(admin.id),
            "passed": True,
        },
    )
    assert only.status_code == 201, only.text
    role_required = "One of the following roles required: Administrator, Lab Manager"
    void_last = client.patch(
        f"/v1/instrument-maintenance-events/{only.json()['id']}",
        headers=tech_h,
        json={"active": False},
    )
    assert void_last.status_code == 403, void_last.text
    assert void_last.json()["detail"] == role_required
    void_non_last = client.patch(
        f"/v1/instrument-maintenance-events/{created.json()['id']}",
        headers=tech_h,
        json={"active": False},
    )
    assert void_non_last.status_code == 403, void_non_last.text
    assert void_non_last.json()["detail"] == role_required
    failed = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(admin.id),
            "passed": False,
        },
    )
    assert failed.status_code == 201, failed.text
    void_failed = client.patch(
        f"/v1/instrument-maintenance-events/{failed.json()['id']}",
        headers=tech_h,
        json={"active": False},
    )
    assert void_failed.status_code == 403, void_failed.text
    assert void_failed.json()["detail"] == role_required
    field_edit = client.patch(
        f"/v1/instrument-maintenance-events/{created.json()['id']}",
        headers=tech_h,
        json={"note": "tech edit"},
    )
    assert field_edit.status_code == 403, field_edit.text
    assert field_edit.json()["detail"] == role_required
    manager_void = client.patch(
        f"/v1/instrument-maintenance-events/{created.json()['id']}",
        headers=mgr_h,
        json={"active": False, "reason": "manager void"},
    )
    assert manager_void.status_code == 200, manager_void.text
    unvoid = client.patch(
        f"/v1/instrument-maintenance-events/{created.json()['id']}",
        headers=tech_h,
        json={"active": True, "reason": "tech restore"},
    )
    assert unvoid.status_code == 403, unvoid.text
    assert unvoid.json()["detail"] == role_required
    manager_restore = client.patch(
        f"/v1/instrument-maintenance-events/{created.json()['id']}",
        headers=mgr_h,
        json={"active": True, "reason": "put back"},
    )
    assert manager_restore.status_code == 422, manager_restore.text
    assert manager_restore.json()["detail"]["code"] == "voided_event_stays_voided"
    admin_ok = client.patch(
        f"/v1/instrument-maintenance-events/{only.json()['id']}",
        headers=admin_h,
        json={"note": "admin edit"},
    )
    assert admin_ok.status_code == 200, admin_ok.text
    admin_void = client.patch(
        f"/v1/instrument-maintenance-events/{only.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "admin void last"},
    )
    assert admin_void.status_code == 200, admin_void.text


def test_update_schedule_waits_on_held_lock(migrated_engine):
    from fastapi import HTTPException

    from app.routers.instrument_ops import update_schedule
    from app.schemas.instrument_ops import MaintenanceScheduleUpdate
    from models.instrument import InstrumentMaintenanceSchedule
    from models.user import User

    Session = sessionmaker(bind=migrated_engine, autoflush=False)
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO lab_settings (id, timezone) "
                "VALUES ('b1a16ae0-0000-4000-8000-000000000001', 'UTC') "
                "ON CONFLICT (id) DO UPDATE SET timezone = 'UTC'"
            )
        )
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        kind_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'PM' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e2lock', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e2-lock-{uid.hex[:6]}",
                "e": f"e2-lock-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        inst = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, true, :u, :u)"
            ),
            {"id": inst, "n": f"E2lock-{inst.hex[:6]}", "t": type_id, "u": uid},
        )
        sched = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_schedules "
                "(id, instrument_id, kind_id, interval_days, next_due, last_done, "
                "active, created_by, modified_by) "
                "VALUES (:id, :i, :k, 10, NULL, NULL, true, :u, :u)"
            ),
            {"id": sched, "i": inst, "k": kind_id, "u": uid},
        )

    inside = threading.Event()
    release = threading.Event()
    box: dict = {}

    def hold():
        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(uid)},
            )
            s.query(InstrumentMaintenanceSchedule).filter(
                InstrumentMaintenanceSchedule.id == sched
            ).with_for_update().first()
            inside.set()
            assert release.wait(5), "test did not release the lock holder"
            s.commit()

    def do_update():
        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(uid)},
            )
            s.execute(text("SET LOCAL lock_timeout = '200ms'"))
            user = s.get(User, uid)
            try:
                update_schedule(
                    sched,
                    MaintenanceScheduleUpdate(interval_days=20),
                    current_user=user,
                    db=s,
                )
                box["ok"] = True
            except HTTPException as exc:
                box["status"] = exc.status_code
                box["code"] = (exc.detail or {}).get("code") if isinstance(exc.detail, dict) else None

    holder = threading.Thread(target=hold)
    waiter = threading.Thread(target=do_update)
    holder.start()
    assert inside.wait(5)
    waiter.start()
    waiter.join(5)
    release.set()
    holder.join(5)
    assert box.get("status") == 409
    assert box.get("code") == "schedule_busy"


def test_0115_inactivates_untyped_referenced_templates(migrated_engine):
    with migrated_engine.begin() as conn:
        leftover = conn.execute(
            text(
                "SELECT count(*) FROM experiment_templates t "
                "WHERE t.active IS TRUE "
                "AND EXISTS (SELECT 1 FROM lims_runs r WHERE r.experiment_template_id = t.id) "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM jsonb_array_elements("
                "    COALESCE(t.template_definition->'entries', '[]'::jsonb)) e "
                "  CROSS JOIN LATERAL jsonb_array_elements("
                "    COALESCE(e->'config'->'slots', '[]'::jsonb)) s "
                "  WHERE COALESCE((s->>'run_import')::boolean, false) "
                "    AND NULLIF(btrim(s->>'instrument_type_id'), '') IS NOT NULL"
                ")"
            )
        ).scalar()
        assert leftover == 0


def test_0115_revision_id_and_single_head():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "db/migrations/versions/0115_instrument_type_slots.py"
    text_src = path.read_text()
    assert 'revision = "0115_instrument_type_slots"' in text_src
    assert len("0115_instrument_type_slots") == 26
    assert "down_revision = \"0114_instrument_hardening\"" in text_src
    assert "REVOKE DELETE ON lims_run_type_substitutions FROM lims_app" in text_src
    assert "GRANT DELETE" not in text_src
    assert "created_by = current_user_id()" in text_src
    versions = Path(__file__).resolve().parents[1] / "db/migrations/versions"
    heads = [
        p.name
        for p in versions.glob("*.py")
        if p.name.startswith("0115")
    ]
    assert heads == ["0115_instrument_type_slots.py"]
