"""Shared reason rules (0121): every user-entered reason uses the void rules.

Trimmed 1-4000. Spaces, tab/newline, NBSP (U+00A0) and U+2007 are blank.
ZWSP (U+200B) and BOM (U+FEFF) stay visible. API tests run on the
create_all schema; DB CHECK tests run on the migrated chain.
"""
from __future__ import annotations

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_dose_response import _make_run, _make_template, dr_setup  # noqa: F401
from tests.test_elisa_run_gaps import _analysis, _publish, _run, _sample, _template
from tests.test_instrument_e2_type_slots import _create_run, _create_template, _start_run
from tests.test_instrument_tracking import _login, _seeded_type

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION_0121 = BACKEND / "db/migrations/versions/0121_shared_reason_rules.py"

NBSP = "\u00a0"
FIGURE_SPACE = "\u2007"
ZWSP = "\u200b"
BOM = "\ufeff"
BLANKS = (None, "", "   ", "\t\n", NBSP * 3, FIGURE_SPACE * 3)
BLANK_IDS = ("missing", "empty", "spaces", "tab-newline", "nbsp", "figure-space")

CONSTRAINTS = (
    ("lims_runs", "ck_lims_runs_status_reason"),
    ("result_acceptances", "ck_result_acceptances_reason"),
    ("lims_run_data_exclusions", "ck_lims_run_data_exclusions_reason"),
    ("lims_run_type_substitutions", "ck_lims_run_type_substitutions_reason"),
)


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _body(reason, **extra):
    body = dict(extra)
    if reason is not None:
        body["reason"] = reason
    return body


def _assert_code(response, code):
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == code, response.text


def _plate(client, admin_h, db_session, test_admin_user, test_org):
    sample = _sample(db_session, test_admin_user, test_org, f"SR-{uuid.uuid4().hex[:6]}")
    analysis, analyte = _analysis(db_session, test_admin_user)
    template_id = _template(client, admin_h)
    run_id = _run(client, admin_h, template_id, str(analysis.id), str(sample.id))
    return run_id, sample, analyte


def _import(client, admin_h, run_id, sample_id, value):
    imported = client.post(
        f"/v1/lims-runs/{run_id}/import",
        json={"rows": [{"sample_id": str(sample_id), "row_data": {"corr": value, "replicate": 1}}]},
        headers=admin_h,
    )
    assert imported.status_code == 200, imported.text


# ---------- API: fail / reject run ----------


@pytest.mark.parametrize("path", ["fail", "reject"])
@pytest.mark.parametrize("reason", BLANKS, ids=BLANK_IDS)
def test_fail_and_reject_refuse_blank_reasons_with_a_code(
    client, admin_h, db_session, test_admin_user, test_org, path, reason
):
    run_id, *_ = _plate(client, admin_h, db_session, test_admin_user, test_org)
    refused = client.post(f"/v1/lims-runs/{run_id}/{path}", json=_body(reason), headers=admin_h)
    _assert_code(refused, "fail_reason_required")
    assert client.get(f"/v1/lims-runs/{run_id}", headers=admin_h).json()["status"] != "failed"


def test_fail_reason_max_4000_trims_and_keeps_zwsp_bom(
    client, admin_h, db_session, test_admin_user, test_org
):
    run_id, *_ = _plate(client, admin_h, db_session, test_admin_user, test_org)
    too_long = client.post(
        f"/v1/lims-runs/{run_id}/fail", json={"reason": "x" * 4001}, headers=admin_h
    )
    assert too_long.status_code == 422, too_long.text
    ok = client.post(
        f"/v1/lims-runs/{run_id}/fail", json={"reason": f"  {'x' * 3996}  "}, headers=admin_h
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status_reason"] == "x" * 3996

    for visible in (ZWSP, BOM):
        other_id, *_ = _plate(client, admin_h, db_session, test_admin_user, test_org)
        kept = client.post(
            f"/v1/lims-runs/{other_id}/fail", json={"reason": visible}, headers=admin_h
        )
        assert kept.status_code == 200, kept.text
        assert kept.json()["status_reason"] == visible


# ---------- API: accept value ----------


def _rerun_with_choice(client, admin_h, db_session, test_admin_user, test_org):
    run_id, sample, analyte = _plate(client, admin_h, db_session, test_admin_user, test_org)
    _import(client, admin_h, run_id, sample.id, "1.10")
    failed = client.post(f"/v1/lims-runs/{run_id}/fail", json={"reason": "QC-H"}, headers=admin_h)
    assert failed.status_code == 200, failed.text
    rerun = client.post(f"/v1/lims-runs/{run_id}/rerun", json={}, headers=admin_h)
    assert rerun.status_code == 201, rerun.text
    rerun_id = rerun.json()["id"]
    started = client.patch(
        f"/v1/lims-runs/{rerun_id}/start", json={"sample_ids": [str(sample.id)]}, headers=admin_h
    )
    assert started.status_code == 200, started.text
    _import(client, admin_h, rerun_id, sample.id, "2.20")
    assert _publish(client, admin_h, rerun_id).status_code == 200
    base = {
        "sample_id": str(sample.id),
        "analyte_id": str(analyte.id),
        "replicate": 1,
        "accepted_lims_run_id": rerun_id,
    }
    return rerun_id, base


def test_accept_value_reason_uses_shared_rules(
    client, admin_h, db_session, test_admin_user, test_org
):
    from models.result_acceptance import ResultAcceptance

    rerun_id, base = _rerun_with_choice(client, admin_h, db_session, test_admin_user, test_org)
    url = f"/v1/lims-runs/{rerun_id}/value-choices"
    for reason in BLANKS:
        _assert_code(
            client.post(url, json=_body(reason, **base), headers=admin_h),
            "acceptance_reason_required",
        )
    too_long = client.post(url, json=_body("x" * 4001, **base), headers=admin_h)
    assert too_long.status_code == 422, too_long.text
    picks = db_session.query(ResultAcceptance).filter(
        ResultAcceptance.sample_id == uuid.UUID(base["sample_id"])
    )
    assert picks.count() == 0

    ok = client.post(url, json=_body(f" {ZWSP}rerun is valid ", **base), headers=admin_h)
    assert ok.status_code == 200, ok.text
    pick = picks.filter(ResultAcceptance.active == True).one()  # noqa: E712
    assert pick.reason == f"{ZWSP}rerun is valid"


# ---------- API: reset fit_in_progress ----------


def test_reset_fit_reason_uses_shared_rules(client, db_session, test_admin_user, admin_token):
    tmpl = _make_template(db_session, test_admin_user.id)
    run = _make_run(db_session, tmpl.id, test_admin_user.id, fit_in_progress=True)
    db_session.commit()
    headers = {"Authorization": f"Bearer {admin_token}"}
    url = f"/v1/lims-runs/{run.id}/dose-response/fit/reset"
    for reason in BLANKS:
        _assert_code(client.post(url, json=_body(reason), headers=headers), "reset_fit_reason_required")
    too_long = client.post(url, json={"reason": "x" * 4001}, headers=headers)
    assert too_long.status_code == 422, too_long.text
    db_session.refresh(run)
    assert run.fit_in_progress is True

    ok = client.post(url, json={"reason": "  worker crashed  "}, headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["reason"] == "worker crashed"
    db_session.refresh(run)
    assert run.fit_in_progress is False


# ---------- API: optional exclusion reason ----------


@pytest.mark.parametrize(
    "sent, stored",
    [
        (None, None),
        ("   ", None),
        (NBSP * 2, None),
        (FIGURE_SPACE, None),
        ("  outlier  ", "outlier"),
        (ZWSP, ZWSP),
        ("x" * 4000, "x" * 4000),
    ],
    ids=["missing", "spaces", "nbsp", "figure-space", "trimmed", "zwsp", "max"],
)
def test_exclusion_reason_is_optional_and_shares_the_rules(
    client, db_session, admin_token, dr_setup, sent, stored
):
    from models.dose_response import LimsRunDataExclusion

    data_row = dr_setup["test_data"]
    response = client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json=_body(sent),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    row = db_session.query(LimsRunDataExclusion).filter_by(lims_run_data_id=data_row.id).one()
    assert row.reason == stored


def test_exclusion_reason_over_4000_is_refused(client, db_session, admin_token, dr_setup):
    from models.dose_response import LimsRunDataExclusion

    data_row = dr_setup["test_data"]
    response = client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json={"reason": "x" * 4001},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422, response.text
    assert db_session.query(LimsRunDataExclusion).filter_by(lims_run_data_id=data_row.id).count() == 0


# ---------- API: substitute instrument type ----------


@pytest.mark.parametrize("reason", BLANKS, ids=BLANK_IDS)
def test_substitute_blank_reason_is_the_shared_code(
    client, admin_h, run_analysis_id, cohort_sample_id, reason
):
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert created.status_code == 201, created.text
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    refused = client.post(
        f"/v1/lims-runs/{created.json()['id']}/substitute-instrument-type",
        headers=admin_h,
        json=_body(reason, instrument_type_id=qpcr["id"]),
    )
    _assert_code(refused, "substitute_reason_required")


# ---------- DB CHECKs (migrated chain) ----------


def _constraint_def(conn, name):
    return conn.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar()


def _probe(conn):
    """Superuser test connection. Replica skips FK triggers; CHECKs still apply."""
    conn.execute(text("SET LOCAL session_replication_role = replica"))


def _insert(conn, table, reason):
    params = {"id": uuid.uuid4(), "a": uuid.uuid4(), "b": uuid.uuid4(), "c": uuid.uuid4(), "r": reason}
    sql = {
        "lims_runs": (
            "INSERT INTO lims_runs (id, name, status, created_by, modified_by, status_reason) "
            "VALUES (:id, 'sr-probe-' || :id, 'failed', :a, :a, :r)"
        ),
        "result_acceptances": (
            "INSERT INTO result_acceptances "
            "(id, sample_id, analyte_id, accepted_lims_run_id, accepted_value, reason) "
            "VALUES (:id, :a, :b, :c, '1', :r)"
        ),
        "lims_run_data_exclusions": (
            "INSERT INTO lims_run_data_exclusions "
            "(id, lims_run_data_id, excluded_by, client_id, reason) "
            "VALUES (:id, :a, :b, :c, :r)"
        ),
        "lims_run_type_substitutions": (
            "INSERT INTO lims_run_type_substitutions "
            "(lims_run_id, to_instrument_type_id, reason, created_by) "
            "VALUES (:a, :b, :r, :c)"
        ),
    }[table]
    conn.execute(text(sql), params)


NULLABLE = {"lims_runs", "lims_run_data_exclusions"}


@pytest.mark.parametrize("table, name", CONSTRAINTS, ids=[t for t, _ in CONSTRAINTS])
def test_db_check_matches_the_void_rules(migrated_engine, table, name):
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        try:
            _probe(conn)
            defn = _constraint_def(conn, name)
            assert defn and "4000" in defn, defn
            refused = ["", "   ", "\t\n", NBSP * 2, FIGURE_SPACE * 2, f" {NBSP}{FIGURE_SPACE} ", "x" * 4001]
            if table not in NULLABLE:
                refused.append(None)
            for value in refused:
                savepoint = conn.begin_nested()
                with pytest.raises(IntegrityError):
                    _insert(conn, table, value)
                savepoint.rollback()
            allowed = [ZWSP, BOM, "x" * 4000, f"  {'x' * 4000}  ", "ok"]
            if table in NULLABLE:
                allowed.append(None)
            for value in allowed:
                savepoint = conn.begin_nested()
                _insert(conn, table, value)
                savepoint.commit()
        finally:
            trans.rollback()


# ---------- migration 0121 ----------


def _load_0121():
    spec = importlib.util.spec_from_file_location("m0121", MIGRATION_0121)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_cfg(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_0121_revision_id_and_single_head():
    src = MIGRATION_0121.read_text()
    assert 'revision = "0121_shared_reason_rules"' in src
    assert len("0121_shared_reason_rules") <= 32
    assert 'down_revision = "0120_void_reason_4000"' in src
    assert "U&'\\00A0'" in src and "U&'\\2007'" in src
    assert "BETWEEN 1 AND 4000" in src
    code = src.split('"""', 2)[2]
    for verb in ("NOT VALID", "GRANT DELETE", "UPDATE ", "DELETE FROM", "left(", "substring("):
        assert verb not in code, verb
    heads = ScriptDirectory.from_config(_alembic_cfg("postgresql://unused")).get_heads()
    assert heads == ["0121_shared_reason_rules"], heads


def test_0121_upgrade_refuses_with_counts_when_a_stored_reason_breaks_the_rule(migrated_engine):
    m0121 = _load_0121()
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        try:
            _probe(conn)
            m0121.refuse_bad_reasons(conn)
            conn.execute(
                text(
                    "ALTER TABLE lims_run_data_exclusions "
                    "DROP CONSTRAINT ck_lims_run_data_exclusions_reason"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE lims_run_type_substitutions "
                    "DROP CONSTRAINT ck_lims_run_type_substitutions_reason"
                )
            )
            _insert(conn, "lims_run_data_exclusions", "   ")
            _insert(conn, "lims_run_type_substitutions", NBSP)
            _insert(conn, "lims_run_type_substitutions", "x" * 4001)
            with pytest.raises(RuntimeError) as refused:
                m0121.refuse_bad_reasons(conn)
            message = str(refused.value)
            assert message.startswith("0121 refuses CHECK")
            assert "lims_run_data_exclusions.reason=1" in message
            assert "lims_run_type_substitutions.reason=2" in message
            assert "lims_runs" not in message
        finally:
            trans.rollback()


def test_0121_downgrade_and_upgrade(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = _alembic_cfg(url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        command.downgrade(cfg, "0120_void_reason_4000")
        with migrated_engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            gone = [_constraint_def(conn, name) for _, name in CONSTRAINTS[:3]]
            subst = _constraint_def(conn, "ck_lims_run_type_substitutions_reason")
        assert version == "0120_void_reason_4000"
        assert gone == [None, None, None]
        assert "4000" in subst
        assert NBSP not in subst and "00A0" not in subst.upper()

        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            back = [_constraint_def(conn, name) for _, name in CONSTRAINTS]
        assert version == "0121_shared_reason_rules"
        assert all(d and "4000" in d for d in back), back
    finally:
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate
