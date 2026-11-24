"""Calculations S9: migration 0127 on the real Alembic chain.

Guards run for the app role (``lims_app``). The migrator and superusers skip
them (``skip_app_row_guard``), so each guard test does ``SET ROLE lims_app``.
The last test runs ``calculate_row`` as the app role against the real
triggers, privileges, and row-level security.
"""
from __future__ import annotations

import json
import uuid
from typing import Dict

from alembic import command
from sqlalchemy import text

from tests.test_calculation_result_entry_s6_db import (
    _allowed,
    _as_app,
    _migrate_env,
    _refused,
    _result_entry,
    _run_entry,
    _world,
)

HEAD = "0127_calculation_attempts"
PREVIOUS = "0126_calculation_activation"
LOCK = "a" * 64
DIGEST = "sha256:" + "b" * 64

ATTEMPT_COLUMNS = (
    "id", "result_entry_id", "test_id", "analyte_id", "lims_run_id", "analysis_id", "status",
    "stop_code", "stop_stage", "stop_detail", "formula_error", "run_summary", "summary_check",
    "summary_code", "lock_hash", "built_image_digest", "configuration_name", "configuration_version",
    "analysis_version", "function_versions", "formula_versions", "inputs_read", "values_used",
    "knocked_out_points", "flags", "stages", "calculated_result", "reported_result", "result_note",
    "created_at", "created_by",
)

INSERT_ATTEMPT = (
    "INSERT INTO calculation_attempts (id, result_entry_id, test_id, analyte_id, lims_run_id, "
    "analysis_id, status, stop_code, stop_stage, formula_error, run_summary, summary_check, "
    "summary_code, lock_hash, built_image_digest, configuration_name, configuration_version, "
    "analysis_version, calculated_result, reported_result, created_at, created_by) VALUES "
    "(:id, :row, :test, :analyte, :run, :analysis, :status, :stop_code, :stop_stage, :formula_error, "
    ":summary, :check, :summary_code, :lock, :digest, 'cfg', 1, 1, :calculated, :reported, "
    "COALESCE(CAST(:created_at AS timestamptz), now()), :by)"
)


def _attempt(ids: Dict[str, uuid.UUID], row_id: uuid.UUID, **overrides) -> dict:
    return {
        "id": uuid.uuid4(),
        "row": row_id,
        "test": ids["test"],
        "analyte": ids["analyte"],
        "run": ids["run"],
        "analysis": ids["analysis"],
        "status": "completed",
        "stop_code": None,
        "stop_stage": None,
        "formula_error": None,
        "summary": "pass",
        "check": None,
        "summary_code": None,
        "lock": LOCK,
        "digest": DIGEST,
        "calculated": "0.026",
        "reported": "0.026",
        "created_at": None,
        "by": ids["admin"],
        **overrides,
    }


def _stopped(ids, row_id, **overrides) -> dict:
    stop = {
        "status": "stopped",
        "stop_code": "r_timeout",
        "stop_stage": "inv",
        "summary": "stopped",
        "check": "inv",
        "summary_code": "r_timeout",
        "calculated": None,
        "reported": None,
    }
    return _attempt(ids, row_id, **{**stop, **overrides})


def _row(conn) -> tuple[Dict[str, uuid.UUID], uuid.UUID]:
    ids = _world(conn)
    row_id = _result_entry(conn, ids, _run_entry(conn, ids))
    conn.execute(
        text("UPDATE result_entries SET raw_result = '0.026', raw_origin = 'typed' WHERE id = :id"),
        {"id": row_id},
    )
    return ids, row_id


def _other_client_user(conn) -> Dict[str, uuid.UUID]:
    """A non-admin user of a client that is not the world's client (inside the caller's transaction)."""
    role, user, client = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    conn.execute(
        text("INSERT INTO clients (id, name, active, billing_info) VALUES (:id, :n, true, '{}')"),
        {"id": client, "n": f"S9C-{client.hex[:6]}"},
    )
    conn.execute(
        text("INSERT INTO roles (id, name, description, active) VALUES (:id, :n, 'S9 test role', true)"),
        {"id": role, "n": f"S9Tech-{role.hex[:6]}"},
    )
    conn.execute(
        text(
            "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
            "VALUES (:id, 's9', :u, :e, 'x', :r, :c, true)"
        ),
        {"id": user, "u": f"s9-{user.hex[:6]}", "e": f"s9-{user.hex[:6]}@x.org", "r": role, "c": client},
    )
    return {"admin": user, "client": client}


# ---- schema shape -------------------------------------------------------------


def test_0127_schema_shape(migrated_engine):
    with migrated_engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == HEAD
        columns = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'calculation_attempts'"
                )
            ).scalars()
        )
        assert columns == set(ATTEMPT_COLUMNS)
        link = conn.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns WHERE table_name = 'result_entries' "
                "AND column_name = 'calculation_attempt_id'"
            )
        ).scalar()
        assert link == "YES"
        fk = conn.execute(
            text(
                "SELECT confrelid::regclass::text, confdeltype FROM pg_constraint "
                "WHERE conname = 'fk_result_entries_calculation_attempt'"
            )
        ).one()
        assert tuple(fk) == ("calculation_attempts", "r")
        for table, column in (
            ("calculation_test_case_results", "outcome"),
            ("calculation_test_case_results", "built_image_digest"),
            ("calculation_dry_runs", "outcome"),
            ("calculation_dry_runs", "lock_hash"),
            ("calculation_dry_runs", "built_image_digest"),
        ):
            assert conn.execute(
                text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
                {"t": table, "c": column},
            ).scalar(), (table, column)
        rls = conn.execute(
            text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'calculation_attempts'")
        ).one()
        assert tuple(rls) == (True, True)
        triggers = set(
            conn.execute(
                text(
                    "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN "
                    "('calculation_attempts'::regclass, 'calculation_test_case_results'::regclass, "
                    "'calculation_dry_runs'::regclass)"
                )
            ).scalars()
        )
        assert {
            "calculation_attempts_guard",
            "calculation_test_case_results_guard",
            "calculation_dry_runs_guard",
        } <= triggers
        privileges = {
            (table, privilege): conn.execute(
                text("SELECT has_table_privilege('lims_app', :t, :p)"), {"t": table, "p": privilege}
            ).scalar()
            for table in ("calculation_attempts", "calculation_test_case_results", "calculation_dry_runs")
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
        }
        for table in ("calculation_attempts", "calculation_test_case_results", "calculation_dry_runs"):
            assert privileges[(table, "SELECT")] and privileges[(table, "INSERT")], table
            assert not privileges[(table, "UPDATE")] and not privileges[(table, "DELETE")], table
        owners = conn.execute(
            text(
                "SELECT (SELECT proowner FROM pg_proc WHERE proname = 'guard_result_entry_write'), "
                "(SELECT relowner FROM pg_class WHERE relname = 'calculation_attempts')"
            )
        ).one()
        assert owners[0] == owners[1], "the result-entry guard can read the attempts it checks"
        catalog = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.columns WHERE table_name = 'result_entries' "
                "AND column_name = 'calculation_attempt_id'"
            )
        ).scalar()
        assert catalog == 1


def test_the_append_only_map_names_the_attempts_table():
    from db.append_only_tables import APPEND_ONLY_REVOKES, REGRANTED

    assert APPEND_ONLY_REVOKES["calculation_attempts"] == frozenset({"UPDATE", "DELETE"})
    assert "calculation_attempts" not in REGRANTED


# ---- the attempt guard ----------------------------------------------------------


def test_an_attempt_is_recorded_for_the_signed_in_user_with_the_database_clock(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            with _as_app(conn, ids):
                params = _attempt(ids, row_id, created_at="2001-01-01T00:00:00Z")
                _allowed(conn, INSERT_ATTEMPT, params)
                created_at = conn.execute(
                    text("SELECT created_at > now() - interval '1 hour' FROM calculation_attempts WHERE id = :id"),
                    {"id": params["id"]},
                ).scalar()
                assert created_at is True, "the database clock, not the caller's time"
                other = _other_client_user(conn)
                _refused(conn, INSERT_ATTEMPT, _attempt(ids, row_id, by=other["admin"]), "calculation_attempt_actor")
        finally:
            tx.rollback()


def test_an_attempt_names_the_test_analyte_run_and_analysis_of_its_row(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            other_ids, other_row = _row(conn)
            with _as_app(conn, ids):
                for key in ("test", "analyte", "run", "analysis"):
                    _refused(
                        conn,
                        INSERT_ATTEMPT,
                        _attempt(ids, row_id, **{key: other_ids[key]}),
                        "calculation_attempt_scope",
                    )
                _refused(conn, INSERT_ATTEMPT, _attempt(ids, other_row), "calculation_attempt_scope")
                _allowed(conn, INSERT_ATTEMPT, _attempt(ids, row_id))
        finally:
            tx.rollback()


def test_an_attempt_is_never_updated_or_deleted_by_the_application(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            params = _attempt(ids, row_id)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_ATTEMPT, params)
                _refused(
                    conn,
                    "UPDATE calculation_attempts SET calculated_result = '1' WHERE id = :id",
                    {"id": params["id"]},
                    "permission denied",
                )
                _refused(conn, "DELETE FROM calculation_attempts WHERE id = :id", {"id": params["id"]}, "permission denied")
            # Even with the privileges handed back, the trigger refuses.
            conn.execute(text("GRANT UPDATE, DELETE ON calculation_attempts TO lims_app"))
            conn.execute(text("SET ROLE lims_app"))
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            _refused(
                conn,
                "UPDATE calculation_attempts SET calculated_result = '1' WHERE id = :id",
                {"id": params["id"]},
                "calculation_attempt_append_only",
            )
            _refused(
                conn,
                "DELETE FROM calculation_attempts WHERE id = :id",
                {"id": params["id"]},
                "calculation_attempt_append_only",
            )
            conn.execute(text("RESET ROLE"))
            kept = conn.execute(
                text("SELECT calculated_result FROM calculation_attempts WHERE id = :id"), {"id": params["id"]}
            ).scalar()
            assert kept == "0.026"
        finally:
            tx.rollback()


def test_the_stop_and_summary_rules_are_checked_by_the_database(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_ATTEMPT, _stopped(ids, row_id))
                _allowed(
                    conn,
                    INSERT_ATTEMPT,
                    _stopped(ids, row_id, stop_code=None, formula_error="#DIV/0!", summary_code=None),
                )
                _allowed(conn, INSERT_ATTEMPT, _attempt(ids, row_id, summary="fail", check="ctrl", summary_code="run_failed"))
                cases = (
                    (_stopped(ids, row_id, stop_code=None, summary_code=None), "ck_calculation_attempts_stop"),
                    (_stopped(ids, row_id, formula_error="#DIV/0!"), "ck_calculation_attempts_stop"),
                    (_attempt(ids, row_id, stop_code="r_timeout"), "ck_calculation_attempts_stop"),
                    (_stopped(ids, row_id, calculated="1"), "ck_calculation_attempts_stop_clears"),
                    (_stopped(ids, row_id, reported="1"), "ck_calculation_attempts_stop_clears"),
                    (_stopped(ids, row_id, stop_stage=None), "ck_calculation_attempts_stop_clears"),
                    (_stopped(ids, row_id, summary="fail"), "ck_calculation_attempts_stop_clears"),
                    (_attempt(ids, row_id, check="ctrl"), "ck_calculation_attempts_summary_names_check"),
                    (_attempt(ids, row_id, summary="fail"), "ck_calculation_attempts_summary_names_check"),
                    (_attempt(ids, row_id, summary="unknown"), "ck_calculation_attempts_summary"),
                    (_attempt(ids, row_id, status="partial"), "ck_calculation_attempts_status"),
                    (_stopped(ids, row_id, stop_code=None, formula_error="#REF!"), "ck_calculation_attempts_formula_error"),
                    (_attempt(ids, row_id, lock="A" * 64), "ck_calculation_attempts_hashes"),
                    (_attempt(ids, row_id, digest="sha256:short"), "ck_calculation_attempts_hashes"),
                )
                for params, code in cases:
                    _refused(conn, INSERT_ATTEMPT, params, code)
                _refused(
                    conn,
                    "INSERT INTO calculation_attempts (result_entry_id, test_id, analyte_id, lims_run_id, "
                    "analysis_id, status, run_summary, lock_hash, built_image_digest, configuration_name, "
                    "configuration_version, analysis_version, stages, created_by) VALUES (:row, :test, "
                    ":analyte, :run, :analysis, 'completed', 'pass', :lock, :digest, 'cfg', 1, 1, "
                    "CAST('{}' AS jsonb), :by)",
                    _attempt(ids, row_id),
                    "ck_calculation_attempts_json",
                )
        finally:
            tx.rollback()


def test_the_migrator_skips_the_attempt_guard_but_not_the_checks(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            params = _attempt(ids, row_id, by=_other_client_user(conn)["admin"])
            _allowed(conn, INSERT_ATTEMPT, params)
            _refused(conn, INSERT_ATTEMPT, _stopped(ids, row_id, calculated="1"), "ck_calculation_attempts_stop_clears")
        finally:
            tx.rollback()


# ---- the link from the row to its attempt ----------------------------------------


def test_the_row_links_only_an_attempt_of_that_row_with_its_values_on_the_calculation_path(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            other_row = _result_entry(conn, ids, conn.execute(
                text("SELECT entry_id FROM result_entries WHERE id = :id"), {"id": row_id}
            ).scalar(), replicate=2)
            with _as_app(conn, ids):
                attempt = _attempt(ids, row_id)
                foreign = _attempt(ids, other_row)
                _allowed(conn, INSERT_ATTEMPT, attempt)
                _allowed(conn, INSERT_ATTEMPT, foreign)
                upd = (
                    "UPDATE result_entries SET calculated_result = :c, reported_result = :r, "
                    "calculation_attempt_id = :a WHERE id = :id"
                )
                link = {"c": "0.026", "r": "0.026", "a": attempt["id"], "id": row_id}
                _refused(conn, upd, link, "calculation_attempt_locked")
                _refused(
                    conn,
                    "UPDATE result_entries SET calculation_attempt_id = :a WHERE id = :id",
                    {"a": attempt["id"], "id": row_id},
                    "calculation_attempt_locked",
                )

                conn.execute(text("SELECT set_config('lims.calculation_write', 'on', true)"))
                _refused(conn, upd, {**link, "a": foreign["id"]}, "calculation_attempt_mismatch")
                _refused(conn, upd, {**link, "c": "0.027"}, "calculation_attempt_mismatch")
                _refused(conn, upd, {**link, "r": "0.03"}, "calculation_attempt_mismatch")
                _refused(conn, upd, {**link, "a": uuid.uuid4()}, "calculation_attempt_mismatch")
                _allowed(conn, upd, link)
                conn.execute(text("SELECT set_config('lims.calculation_write', 'off', true)"))

                # A person may still override the reported value; the link stays.
                _allowed(conn, "UPDATE result_entries SET reported_result = '0.03' WHERE id = :id", {"id": row_id})
                _refused(
                    conn,
                    "UPDATE result_entries SET calculation_attempt_id = NULL WHERE id = :id",
                    {"id": row_id},
                    "calculation_attempt_locked",
                )
                _refused(
                    conn,
                    "INSERT INTO result_entries (id, entry_id, test_id, analyte_id, replicate, calculation_attempt_id) "
                    "SELECT gen_random_uuid(), entry_id, test_id, analyte_id, 3, :a FROM result_entries WHERE id = :id",
                    {"a": attempt["id"], "id": row_id},
                    "calculation_attempt_locked",
                )
                linked = conn.execute(
                    text("SELECT calculation_attempt_id, reported_result FROM result_entries WHERE id = :id"),
                    {"id": row_id},
                ).one()
                assert tuple(linked) == (attempt["id"], "0.03")
        finally:
            tx.rollback()


def test_a_stopped_attempt_clears_both_values_on_the_row(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            with _as_app(conn, ids):
                stopped = _stopped(ids, row_id)
                _allowed(conn, INSERT_ATTEMPT, stopped)
                conn.execute(text("SELECT set_config('lims.calculation_write', 'on', true)"))
                _allowed(
                    conn,
                    "UPDATE result_entries SET calculated_result = NULL, reported_result = NULL, "
                    "calculation_attempt_id = :a WHERE id = :id",
                    {"a": stopped["id"], "id": row_id},
                )
                conn.execute(text("SELECT set_config('lims.calculation_write', 'off', true)"))
                # With nothing calculated, a reported value is still refused.
                _refused(
                    conn,
                    "UPDATE result_entries SET reported_result = '1' WHERE id = :id",
                    {"id": row_id},
                    "reported_before_calculation",
                )
        finally:
            tx.rollback()


# ---- row-level security ------------------------------------------------------------


def test_attempts_are_visible_only_with_their_result_entry(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids, row_id = _row(conn)
            params = _attempt(ids, row_id)
            outsider = _other_client_user(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_ATTEMPT, params)
                assert conn.execute(text("SELECT count(*) FROM calculation_attempts")).scalar() >= 1
            with _as_app(conn, outsider):
                seen = conn.execute(
                    text("SELECT count(*) FROM calculation_attempts WHERE id = :id"), {"id": params["id"]}
                ).scalar()
                rows = conn.execute(
                    text("SELECT count(*) FROM result_entries WHERE id = :id"), {"id": row_id}
                ).scalar()
                assert (seen, rows) == (0, 0)
        finally:
            tx.rollback()


# ---- downgrade and upgrade ----------------------------------------------------------


def _shape(engine) -> dict:
    with engine.connect() as conn:
        return {
            "version": conn.execute(text("SELECT version_num FROM alembic_version")).scalar(),
            "attempts": conn.execute(text("SELECT to_regclass('public.calculation_attempts')")).scalar(),
            "link": conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name = 'result_entries' "
                    "AND column_name = 'calculation_attempt_id'"
                )
            ).scalar(),
            "outcome": conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name IN "
                    "('calculation_test_case_results', 'calculation_dry_runs') AND column_name = 'outcome'"
                )
            ).scalar(),
            "insert": tuple(
                conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, 'INSERT')"), {"t": table}
                ).scalar()
                for table in ("calculation_test_case_results", "calculation_dry_runs")
            ),
            "functions": set(
                conn.execute(
                    text(
                        "SELECT proname FROM pg_proc WHERE proname IN "
                        "('guard_calculation_attempt', 'guard_calculation_run_record')"
                    )
                ).scalars()
            ),
            "guard": conn.execute(
                text("SELECT prosrc FROM pg_proc WHERE proname = 'guard_result_entry_write'")
            ).scalar(),
        }


def test_0127_downgrade_removes_attempts_and_upgrade_restores_them(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        command.downgrade(cfg, PREVIOUS)
        down = _shape(migrated_engine)
        assert down["version"] == PREVIOUS
        assert down["attempts"] is None
        assert (down["link"], down["outcome"]) == (0, 0)
        assert down["insert"] == (False, False)
        assert down["functions"] == set()
        assert "calculation_attempt" not in down["guard"]
        assert "calculated_locked" in down["guard"]

        with migrated_engine.connect() as conn:
            tx = conn.begin()
            try:
                ids, row_id = _row(conn)
                with _as_app(conn, ids):
                    conn.execute(text("SELECT set_config('lims.calculation_write', 'on', true)"))
                    _allowed(
                        conn,
                        "UPDATE result_entries SET calculated_result = '1', reported_result = '1' WHERE id = :id",
                        {"id": row_id},
                    )
            finally:
                tx.rollback()

        command.upgrade(cfg, HEAD)
        up = _shape(migrated_engine)
        assert up["version"] == HEAD
        assert up["attempts"] == "calculation_attempts"
        assert (up["link"], up["outcome"]) == (1, 2)
        assert up["insert"] == (True, True)
        assert up["functions"] == {"guard_calculation_attempt", "guard_calculation_run_record"}
        assert "calculation_attempt_mismatch" in up["guard"]


# ---- the service as the application role, against the real triggers ----------------


def test_calculate_row_runs_as_the_app_role_against_the_real_guards(migrated_engine):
    from sqlalchemy.orm import Session

    from app.database import set_rls_context
    from app.services.calculation_attempt_service import calculate_row
    from app.services.calculation_config import ConfigContext, parse_config
    from models.user import User
    from tests.test_calculation_attempts_s9_api import COPY_RAW_CFG, StubClient

    with migrated_engine.connect() as conn:
        outer = conn.begin()
        try:
            ids, row_id = _row(conn)
            ctx = ConfigContext(
                analyte_id=str(ids["analyte"]),
                calculation_order=1,
                analyte_orders={},
                units={},
                saved_formulas={},
            )
            stored = parse_config(COPY_RAW_CFG, ctx).to_json()
            conn.execute(
                text(
                    "UPDATE analysis_analytes SET calculation_order = 1, calculation_config_name = 'Lead copy', "
                    "calculation_config_version = 1, calculation_config = CAST(:c AS jsonb), "
                    "calculation_config_state = 'active' WHERE analysis_id = :a AND analyte_id = :b"
                ),
                {"c": json.dumps(stored), "a": ids["analysis"], "b": ids["analyte"]},
            )
            with _as_app(conn, ids):
                session = Session(bind=conn, join_transaction_mode="create_savepoint")
                set_rls_context(session, user_id=str(ids["admin"]), client_id=str(ids["client"]))
                admin = session.get(User, ids["admin"])
                stub = StubClient()
                attempt, row = calculate_row(session, admin, ids["run"], row_id, stub)
                assert stub.health_reads >= 1
                assert (row.calculated_result, row.reported_result) == ("0.026", "0.026")
                assert row.calculation_attempt_id == attempt.id
                stored_attempt = conn.execute(
                    text(
                        "SELECT status, run_summary, created_by, lock_hash, built_image_digest, "
                        "jsonb_array_length(inputs_read) FROM calculation_attempts WHERE id = :id"
                    ),
                    {"id": attempt.id},
                ).one()
                assert stored_attempt[0:3] == ("completed", "pass", ids["admin"])
                assert stored_attempt[3] == stub.health["lock_hash"]
                assert stored_attempt[4] == stub.health["R_IMAGE_DIGEST"]
                assert stored_attempt[5] >= 1
                flag = conn.execute(text("SELECT current_setting('lims.calculation_write', true)")).scalar()
                assert flag in (None, "", "off"), "the calculation flag is turned off again"
                session.close()
        finally:
            outer.rollback()
