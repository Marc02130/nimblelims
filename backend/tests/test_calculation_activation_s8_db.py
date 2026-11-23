"""Calculations S8: migrations 0125 and 0126 on the real Alembic chain.

The guards run for the application role (``lims_app``): an activation row's
actor is ``current_user_id()`` and an Admin, an activation row is never updated
or deleted, a confirm token is consumed once and its other fields never change,
and the stage runner's tables (test-case results, dry runs) are read-only for
the application. The migrator and superusers skip the guards
(``skip_app_row_guard``), as in S7.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Dict

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.test_calculation_config_s7_db import (
    SET_CONFIG,
    _commit_analysis,
    _params,
    _versions,
)
from tests.test_calculation_result_entry_s6_db import (
    _admin_id,
    _allowed,
    _as_app,
    _migrate_env,
    _refused,
)

HEAD = "0126_calculation_activation"
PREVIOUS = "0125_analysis_version_no_change"
LOCK = "a" * 64
REVIEW = "b" * 64

ACTIVATION_COLUMNS = (
    "analysis_id", "analyte_id", "configuration_name", "configuration_version", "function_versions",
    "lock_hash", "validation_state", "review_document", "review_hash", "created_at", "created_by",
)

INSERT_ACTIVATION = (
    "INSERT INTO calculation_activations (analysis_id, analyte_id, configuration_name, "
    "configuration_version, function_versions, lock_hash, validation_state, review_document, "
    "review_hash, created_by) VALUES (:a, :b, 'cfg', 1, CAST('[]' AS jsonb), :lock, :state, "
    "CAST('{}' AS jsonb), :review, :by)"
)

INSERT_TOKEN = (
    "INSERT INTO calculation_confirm_tokens (token_hash, user_id, analysis_id, analyte_id, "
    "configuration_version, review_hash, session_jti, issued_at) "
    "VALUES (:h, :u, :a, :b, 1, :review, 'jti-1', COALESCE(CAST(:issued AS timestamptz), now()))"
)

INSERT_CASE = (
    "INSERT INTO calculation_test_cases (analysis_id, analyte_id, configuration_version, name, "
    "inputs, expected, expected_source, created_by) VALUES (:a, :b, 1, :n, CAST('{}' AS jsonb), "
    "CAST('{}' AS jsonb), :src, :by)"
)


def _sqlstate(conn, sql: str, params: dict) -> str:
    """The SQLSTATE the database raised for a statement (rolled back to a savepoint)."""
    savepoint = conn.begin_nested()
    with pytest.raises(DBAPIError) as refused:
        conn.execute(text(sql), params)
    savepoint.rollback()
    return refused.value.orig.pgcode


def _ids(conn) -> Dict[str, uuid.UUID]:
    return {
        "admin": _admin_id(conn),
        "client": uuid.uuid4(),
        "analysis": uuid.uuid4(),
        "analyte": uuid.uuid4(),
    }


def _other_user(conn) -> uuid.UUID:
    """A user who is not an Administrator, inserted inside the caller's transaction."""
    role = uuid.uuid4()
    user = uuid.uuid4()
    client = conn.execute(text("SELECT id FROM clients ORDER BY created_at, id LIMIT 1")).scalar()
    conn.execute(
        text("INSERT INTO roles (id, name, description, active) VALUES (:id, :n, 'S8 test role', true)"),
        {"id": role, "n": f"S8Tech-{role.hex[:6]}"},
    )
    conn.execute(
        text(
            "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
            "VALUES (:id, 's8', :u, :e, 'x', :r, :c, true)"
        ),
        {"id": user, "u": f"s8-{user.hex[:6]}", "e": f"s8-{user.hex[:6]}@x.org", "r": role, "c": client},
    )
    return user


def _activation(ids: Dict[str, uuid.UUID], **overrides) -> dict:
    return {
        "a": ids["analysis"],
        "b": ids["analyte"],
        "lock": LOCK,
        "state": "no_test_cases",
        "review": REVIEW,
        "by": ids["admin"],
        **overrides,
    }


def _token_row(ids: Dict[str, uuid.UUID], **overrides) -> dict:
    return {
        "h": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "u": ids["admin"],
        "a": ids["analysis"],
        "b": ids["analyte"],
        "review": REVIEW,
        "issued": None,
        **overrides,
    }


# ---- schema shape -------------------------------------------------------------


def test_0126_schema_shape(migrated_engine):
    with migrated_engine.connect() as conn:
        cols = {
            (t, c): n
            for t, c, n in conn.execute(
                text(
                    "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name IN ('calculation_activations', "
                    "'calculation_confirm_tokens', 'calculation_test_cases', "
                    "'calculation_test_case_results', 'calculation_dry_runs')"
                )
            )
        }
        for column in ACTIVATION_COLUMNS:
            assert ("calculation_activations", column) in cols, column
        assert cols[("calculation_activations", "created_by")] == "NO"
        assert cols[("calculation_activations", "review_document")] == "NO"
        for column in (
            "token_hash", "user_id", "analysis_id", "analyte_id", "configuration_version",
            "review_hash", "session_jti", "issued_at", "consumed_at",
        ):
            assert ("calculation_confirm_tokens", column) in cols, column
        assert cols[("calculation_confirm_tokens", "consumed_at")] == "YES"
        for column in ("name", "inputs", "expected", "expected_source", "configuration_version"):
            assert ("calculation_test_cases", column) in cols, column
        for column in ("test_case_id", "lock_hash", "passed", "run_at"):
            assert ("calculation_test_case_results", column) in cols, column
        for column in ("configuration_version", "input", "run_at"):
            assert ("calculation_dry_runs", column) in cols, column
        assert not any(c == "reason" or c == "password" for (_t, c) in cols), "activation adds no reason or password field"

        constraints = set(conn.execute(text("SELECT conname FROM pg_constraint")).scalars())
        for name in (
            "ck_calculation_activations_state",
            "ck_calculation_activations_hashes",
            "ck_calculation_confirm_tokens_hashes",
            "ck_calculation_test_cases_source",
        ):
            assert name in constraints, name

        triggers = set(
            conn.execute(
                text(
                    "SELECT tgname FROM pg_trigger WHERE tgname IN "
                    "('calculation_activations_guard', 'calculation_confirm_tokens_guard')"
                )
            ).scalars()
        )
        assert triggers == {"calculation_activations_guard", "calculation_confirm_tokens_guard"}

        expected = {
            "calculation_activations": {"SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False},
            "calculation_confirm_tokens": {"SELECT": True, "INSERT": True, "UPDATE": True, "DELETE": False},
            "calculation_test_cases": {"SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False},
            "calculation_test_case_results": {"SELECT": True, "INSERT": False, "UPDATE": False, "DELETE": False},
            "calculation_dry_runs": {"SELECT": True, "INSERT": False, "UPDATE": False, "DELETE": False},
        }
        for table, privileges in expected.items():
            for privilege, granted in privileges.items():
                actual = conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, :p)"),
                    {"t": f"public.{table}", "p": privilege},
                ).scalar()
                assert actual is granted, (table, privilege)
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0, "no row is seeded"


def test_the_append_only_map_matches_the_migration():
    from db.append_only_tables import APPEND_ONLY_REVOKES

    assert APPEND_ONLY_REVOKES["calculation_activations"] == frozenset({"UPDATE", "DELETE"})
    assert APPEND_ONLY_REVOKES["calculation_confirm_tokens"] == frozenset({"DELETE"})
    assert APPEND_ONLY_REVOKES["calculation_test_cases"] == frozenset({"UPDATE", "DELETE"})
    assert APPEND_ONLY_REVOKES["calculation_test_case_results"] == frozenset({"INSERT", "UPDATE", "DELETE"})
    assert APPEND_ONLY_REVOKES["calculation_dry_runs"] == frozenset({"INSERT", "UPDATE", "DELETE"})


def test_the_validation_state_is_a_closed_list_without_the_word_validated(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            for state in ("no_test_cases", "tests_none_passed", "tests_some_passed", "tests_all_passed"):
                _allowed(conn, INSERT_ACTIVATION, _activation(ids, state=state))
            for state in ("validated", "passed", "", "NO_TEST_CASES"):
                _refused(conn, INSERT_ACTIVATION, _activation(ids, state=state), "ck_calculation_activations_state")
            _refused(conn, INSERT_ACTIVATION, _activation(ids, lock="short"), "ck_calculation_activations_hashes")
            _refused(conn, INSERT_ACTIVATION, _activation(ids, review="G" * 64), "ck_calculation_activations_hashes")
        finally:
            tx.rollback()


# ---- the activation row: the database enforces the actor and append-only -------


def test_an_activation_row_is_written_only_by_the_signed_in_admin(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            other = _other_user(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_ACTIVATION, _activation(ids))
                _refused(conn, INSERT_ACTIVATION, _activation(ids, by=other), "calculation_activation_actor")
                _refused(conn, INSERT_ACTIVATION, _activation(ids, by=uuid.uuid4()), "calculation_activation_actor")
                assert conn.execute(text("SELECT count(*) FROM calculation_activations")).scalar() == 1

                conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(other)})
                _refused(conn, INSERT_ACTIVATION, _activation(ids, by=other), "calculation_activation_admin_only")
                conn.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        finally:
            tx.rollback()


def test_a_forged_actor_leaves_no_row(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            other = _other_user(conn)
            with _as_app(conn, ids):
                assert _sqlstate(conn, INSERT_ACTIVATION, _activation(ids, by=other)) == "42501"
                assert _sqlstate(conn, INSERT_ACTIVATION, _activation(ids, by=uuid.uuid4())) == "42501"
                assert conn.execute(text("SELECT count(*) FROM calculation_activations")).scalar() == 0
        finally:
            tx.rollback()


def test_update_and_delete_of_an_activation_row_are_refused_and_leave_it_unchanged(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_ACTIVATION, _activation(ids))
                _refused(conn, "UPDATE calculation_activations SET configuration_name = 'changed'", {}, "permission denied")
                _refused(conn, "DELETE FROM calculation_activations", {}, "permission denied")
                conn.execute(text("RESET ROLE"))
                conn.execute(text("GRANT UPDATE, DELETE ON calculation_activations TO lims_app"))
                conn.execute(text("SET ROLE lims_app"))
                _refused(conn, "UPDATE calculation_activations SET configuration_name = 'changed'", {}, "calculation_activation_append_only")
                _refused(conn, "DELETE FROM calculation_activations", {}, "calculation_activation_append_only")
                assert _sqlstate(conn, "UPDATE calculation_activations SET configuration_name = 'changed'", {}) == "42501"
                assert _sqlstate(conn, "DELETE FROM calculation_activations", {}) == "42501"
                assert conn.execute(text("SELECT configuration_name FROM calculation_activations")).scalar() == "cfg"
                assert conn.execute(text("SELECT count(*) FROM calculation_activations")).scalar() == 1
        finally:
            tx.rollback()


def test_the_migrator_and_superusers_skip_the_activation_guard(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            _allowed(conn, INSERT_ACTIVATION, _activation(ids, by=_other_user(conn)))
        finally:
            tx.rollback()


# ---- the confirm token --------------------------------------------------------


def test_a_token_row_is_issued_to_the_signed_in_user_and_timed_by_the_database(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            other = _other_user(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_TOKEN, _token_row(ids, issued="2000-01-01T00:00:00+00:00"))
                _refused(conn, INSERT_TOKEN, _token_row(ids, u=other), "calculation_confirm_token_user")
                age = conn.execute(
                    text("SELECT now() - issued_at FROM calculation_confirm_tokens")
                ).scalar()
                assert age.total_seconds() < 5, "the app cannot back-date issued_at"
        finally:
            tx.rollback()


def test_a_token_is_consumed_once_and_nothing_else_about_it_changes(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            with _as_app(conn, ids):
                row = _token_row(ids)
                _allowed(conn, INSERT_TOKEN, row)
                for column, value in (
                    ("review_hash", "'" + "c" * 64 + "'"),
                    ("configuration_version", "9"),
                    ("session_jti", "'other'"),
                    ("issued_at", "now() + interval '1 day'"),
                    ("analyte_id", "gen_random_uuid()"),
                ):
                    _refused(
                        conn,
                        f"UPDATE calculation_confirm_tokens SET {column} = {value}",
                        {},
                        "calculation_confirm_token_immutable",
                    )
                _refused(conn, "DELETE FROM calculation_confirm_tokens", {}, "permission denied")
                _allowed(conn, "UPDATE calculation_confirm_tokens SET consumed_at = now()", {})
                assert conn.execute(text("SELECT consumed_at IS NOT NULL FROM calculation_confirm_tokens")).scalar()
                _refused(conn, "UPDATE calculation_confirm_tokens SET consumed_at = NULL", {}, "calculation_confirm_token_used")
                _refused(conn, "UPDATE calculation_confirm_tokens SET consumed_at = now()", {}, "calculation_confirm_token_used")
        finally:
            tx.rollback()


def test_a_token_hash_is_unique_and_hex(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            row = _token_row(ids)
            _allowed(conn, INSERT_TOKEN, row)
            _refused(conn, INSERT_TOKEN, row, "calculation_confirm_tokens_token_hash_key")
            _refused(conn, INSERT_TOKEN, _token_row(ids, h="not-hex"), "ck_calculation_confirm_tokens_hashes")
        finally:
            tx.rollback()


# ---- test cases, results, and dry runs ----------------------------------------


def test_test_cases_are_insert_only_and_their_source_is_closed(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            with _as_app(conn, ids):
                _allowed(conn, INSERT_CASE, {"a": ids["analysis"], "b": ids["analyte"], "n": "one", "src": "independent", "by": ids["admin"]})
                _allowed(conn, INSERT_CASE, {"a": ids["analysis"], "b": ids["analyte"], "n": "two", "src": "system_output", "by": ids["admin"]})
                _refused(conn, INSERT_CASE, {"a": ids["analysis"], "b": ids["analyte"], "n": "x", "src": "guess", "by": ids["admin"]}, "ck_calculation_test_cases_source")
                _refused(conn, "UPDATE calculation_test_cases SET expected_source = 'independent'", {}, "permission denied")
                _refused(conn, "DELETE FROM calculation_test_cases", {}, "permission denied")
        finally:
            tx.rollback()


def test_the_application_cannot_write_test_case_results_or_dry_runs(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            conn.execute(
                text(INSERT_CASE),
                {"a": ids["analysis"], "b": ids["analyte"], "n": "one", "src": "independent", "by": ids["admin"]},
            )
            case = conn.execute(text("SELECT id FROM calculation_test_cases")).scalar_one()
            with _as_app(conn, ids):
                _refused(
                    conn,
                    "INSERT INTO calculation_test_case_results (test_case_id, lock_hash, passed) VALUES (:c, :l, true)",
                    {"c": case, "l": LOCK},
                    "permission denied",
                )
                _refused(
                    conn,
                    "INSERT INTO calculation_dry_runs (analysis_id, analyte_id, configuration_version, input) "
                    "VALUES (:a, :b, 1, CAST('{}' AS jsonb))",
                    {"a": ids["analysis"], "b": ids["analyte"]},
                    "permission denied",
                )
                assert conn.execute(text("SELECT count(*) FROM calculation_test_case_results")).scalar() == 0
            conn.execute(
                text("INSERT INTO calculation_test_case_results (test_case_id, lock_hash, passed) VALUES (:c, :l, true)"),
                {"c": case, "l": LOCK},
            )
            with _as_app(conn, ids):
                assert conn.execute(text("SELECT count(*) FROM calculation_test_case_results")).scalar() == 1
        finally:
            tx.rollback()


# ---- activating a configuration needs the flag, and bumps the version once -----


def test_the_activation_flag_moves_a_draft_to_active_and_the_version_bumps_once(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            conn.execute(text(SET_CONFIG), _params(ids, order=1, name="Draft", state="draft"))
        version_draft, rows_draft = _versions(migrated_engine, ids["analysis"])
        assert version_draft == 2

        with migrated_engine.connect() as conn:
            tx = conn.begin()
            with _as_app(conn, {**ids, "client": uuid.uuid4()}):
                sql = (
                    "UPDATE analysis_analytes SET calculation_config_state = 'active' "
                    "WHERE analysis_id = :a AND analyte_id = :b"
                )
                _refused(conn, sql, {"a": ids["analysis"], "b": ids["analyte"]}, "calculation_activation_required")
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'on', true)"))
                conn.execute(text(sql), {"a": ids["analysis"], "b": ids["analyte"]})
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'off', true)"))
            tx.rollback()

        with migrated_engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            conn.execute(text("SELECT set_config('lims.calculation_activate', 'on', true)"))
            conn.execute(
                text(
                    "UPDATE analysis_analytes SET calculation_config_state = 'active' "
                    "WHERE analysis_id = :a AND analyte_id = :b"
                ),
                {"a": ids["analysis"], "b": ids["analyte"]},
            )
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 3, "activation is a real change: one new analysis version"
        assert rows[2][1]["analytes"][0]["calculation_config_state"] == "active"
        assert rows[1][1]["analytes"][0]["calculation_config_state"] == "draft"
    finally:
        cleanup()


# ---- downgrade and upgrade ----------------------------------------------------


def test_0126_downgrade_removes_the_tables_and_upgrade_restores_them(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        command.downgrade(cfg, PREVIOUS)
        with migrated_engine.connect() as conn:
            tables = set(
                conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
                        "AND table_name LIKE 'calculation\\_%'"
                    )
                ).scalars()
            )
            functions = set(
                conn.execute(
                    text(
                        "SELECT proname FROM pg_proc WHERE proname IN "
                        "('guard_calculation_activation', 'guard_calculation_confirm_token')"
                    )
                ).scalars()
            )
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == PREVIOUS
        assert tables == {"calculation_formulas"}
        assert functions == set()

        command.upgrade(cfg, HEAD)
        with migrated_engine.connect() as conn:
            tables = set(
                conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
                        "AND table_name LIKE 'calculation\\_%'"
                    )
                ).scalars()
            )
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == HEAD
        assert tables == {
            "calculation_formulas",
            "calculation_activations",
            "calculation_confirm_tokens",
            "calculation_test_cases",
            "calculation_test_case_results",
            "calculation_dry_runs",
        }


def test_the_json_columns_are_json_objects_or_arrays(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _ids(conn)
            _refused(
                conn,
                INSERT_ACTIVATION.replace("CAST('{}' AS jsonb)", "CAST('[]' AS jsonb)"),
                _activation(ids),
                "ck_calculation_activations_json",
            )
            _refused(
                conn,
                INSERT_CASE.replace("CAST('{}' AS jsonb), CAST('{}' AS jsonb)", "CAST('[]' AS jsonb), CAST('{}' AS jsonb)"),
                {"a": ids["analysis"], "b": ids["analyte"], "n": "x", "src": "independent", "by": ids["admin"]},
                "ck_calculation_test_cases_json",
            )
        finally:
            tx.rollback()


# ---- the service as the application role, against the real triggers ------------


def test_the_activation_service_runs_as_the_app_role_against_the_real_guards(migrated_engine):
    from sqlalchemy.orm import Session

    from app.services import calculation_activation as activation
    from app.services.calculation_review import build_review
    from app.services.calculation_config import parse_config  # noqa: F401  (import check)
    from models.user import User
    from tests.test_calculation_config_s7 import config, stage_copy

    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        configuration = config(stage_copy(), name="Draft")
        with migrated_engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            conn.execute(
                text(SET_CONFIG),
                {**_params(ids, order=1, name="Draft"), "c": json.dumps(configuration)},
            )
        version_before, _ = _versions(migrated_engine, ids["analysis"])

        with migrated_engine.connect() as conn:
            outer = conn.begin()
            try:
                with _as_app(conn, {**ids, "client": uuid.uuid4()}):
                    session = Session(bind=conn, join_transaction_mode="create_savepoint")
                    admin = session.get(User, ids["admin"])
                    document, digest = build_review(session, ids["analysis"], ids["analyte"])
                    assert document["configuration"]["name"] == "Draft"

                    issued = activation.issue_token(
                        session, admin, "jti-real", ids["analysis"], ids["analyte"], {"review_hash": digest}
                    )
                    record = activation.activate(
                        session,
                        admin,
                        "jti-real",
                        ids["analysis"],
                        ids["analyte"],
                        {"confirm_token": issued["confirm_token"]},
                    )
                    assert record["created_by"] == ids["admin"]
                    assert record["review_hash"] == digest

                    state = conn.execute(
                        text(
                            "SELECT calculation_config_state FROM analysis_analytes "
                            "WHERE analysis_id = :a AND analyte_id = :b"
                        ),
                        {"a": ids["analysis"], "b": ids["analyte"]},
                    ).scalar()
                    assert state == "active"
                    consumed = conn.execute(text("SELECT consumed_at FROM calculation_confirm_tokens")).scalar()
                    assert consumed is not None
                    flag = conn.execute(text("SELECT current_setting('lims.calculation_activate', true)")).scalar()
                    assert flag == "off", "the activation flag is turned off again"

                    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
                    assert (
                        conn.execute(text("SELECT version FROM analyses WHERE id = :a"), {"a": ids["analysis"]}).scalar()
                        == version_before + 1
                    )
                    session.close()
            finally:
                outer.rollback()
        version_after, _ = _versions(migrated_engine, ids["analysis"])
        assert version_after == version_before, "the test's transaction was rolled back"
    finally:
        cleanup()
