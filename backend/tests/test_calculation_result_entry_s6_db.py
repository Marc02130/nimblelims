"""Calculations S6: migration 0123 on the real Alembic chain.

Guards run for the app role (``lims_app``). The migrator and superusers skip
them (``skip_app_row_guard``), so each guard test does ``SET ROLE lims_app``.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Dict, Iterator

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.test_shared_reason_rules_0121 import _alembic_cfg

HEAD = "0123_result_entry_data_model"
PREVIOUS = "0122_calculation_units_seed"


def _entry(conn, list_id: str, name: str):
    return conn.execute(
        text("SELECT id FROM list_entries WHERE list_id = :l AND name = :n"),
        {"l": list_id, "n": name},
    ).scalar_one()


def _admin_id(conn):
    return conn.execute(
        text(
            "SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id "
            "WHERE r.name = 'Administrator' ORDER BY u.created_at LIMIT 1"
        )
    ).scalar_one()


def _world(conn, *, with_run_on_test: bool = True) -> Dict[str, uuid.UUID]:
    """Client, project, sample, analysis with one analyte, a run, and a Test."""
    tag = uuid.uuid4().hex[:6]
    ids = {k: uuid.uuid4() for k in ("client", "project", "sample", "analysis", "analyte", "run", "test")}
    ids["admin"] = _admin_id(conn)
    sample_type = _entry(conn, "55555555-5555-5555-5555-555555555555", "Blood")
    sample_status = _entry(conn, "11111111-1111-1111-1111-111111111111", "Received")
    project_status = _entry(conn, "33333333-3333-3333-3333-333333333333", "Active")
    ids["status"] = sample_status
    # Reuse a seeded client: the migration tests commit, and a new client
    # would have no Schema catalog rows for the catalog seed tests to find.
    existing_client = conn.execute(
        text("SELECT id FROM clients ORDER BY created_at, id LIMIT 1")
    ).scalar()
    if existing_client is not None:
        ids["client"] = existing_client
    else:
        conn.execute(
            text("INSERT INTO clients (id, name, active, billing_info) VALUES (:id, :n, true, '{}')"),
            {"id": ids["client"], "n": f"S6C-{tag}"},
        )
    conn.execute(
        text(
            "INSERT INTO projects (id, name, client_id, status, start_date, active, created_by, modified_by) "
            "VALUES (:id, :n, :c, :s, CURRENT_DATE, true, :u, :u)"
        ),
        {"id": ids["project"], "n": f"S6P-{tag}", "c": ids["client"], "s": project_status, "u": ids["admin"]},
    )
    conn.execute(
        text(
            "INSERT INTO samples (id, name, sample_type, status, project_id, active, created_by, modified_by) "
            "VALUES (:id, :n, :t, :s, :p, true, :u, :u)"
        ),
        {
            "id": ids["sample"], "n": f"S6S-{tag}", "t": sample_type, "s": sample_status,
            "p": ids["project"], "u": ids["admin"],
        },
    )
    conn.execute(
        text("INSERT INTO analyses (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
        {"id": ids["analysis"], "n": f"S6A-{tag}", "u": ids["admin"]},
    )
    conn.execute(
        text("INSERT INTO analytes (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
        {"id": ids["analyte"], "n": f"S6An-{tag}", "u": ids["admin"]},
    )
    conn.execute(
        text("INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required) VALUES (:a, :b, false)"),
        {"a": ids["analysis"], "b": ids["analyte"]},
    )
    conn.execute(
        text(
            "INSERT INTO lims_runs (id, name, status, analysis_id, created_by) "
            "VALUES (:id, :n, 'running', :a, :u)"
        ),
        {"id": ids["run"], "n": f"S6R-{tag}", "a": ids["analysis"], "u": ids["admin"]},
    )
    _insert_test(conn, ids, ids["test"], ids["run"] if with_run_on_test else None, f"S6T-{tag}")
    return ids


def _insert_test(conn, ids, test_id, run_id, name):
    columns = "id, name, sample_id, analysis_id, status, active, created_by, modified_by"
    values = ":id, :n, :s, :a, :st, true, :u, :u"
    params = {
        "id": test_id, "n": name, "s": ids["sample"], "a": ids["analysis"],
        "st": ids["status"], "u": ids["admin"],
    }
    if run_id is not None:
        columns += ", lims_run_id"
        values += ", :r"
        params["r"] = run_id
    conn.execute(text(f"INSERT INTO tests ({columns}) VALUES ({values})"), params)


def _run_entry(conn, ids) -> uuid.UUID:
    entry_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO entries (id, lims_run_id, entry_type, name, created_by) "
            "VALUES (:id, :r, 'experiment_sample_data', 'Results', :u)"
        ),
        {"id": entry_id, "r": ids["run"], "u": ids["admin"]},
    )
    return entry_id


def _result_entry(conn, ids, entry_id, replicate=1) -> uuid.UUID:
    row_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO result_entries (id, entry_id, test_id, analyte_id, replicate) "
            "VALUES (:id, :e, :t, :a, :rep)"
        ),
        {"id": row_id, "e": entry_id, "t": ids["test"], "a": ids["analyte"], "rep": replicate},
    )
    return row_id


@contextmanager
def _as_app(conn, ids) -> Iterator[None]:
    """lims_app with the grants ensure_lims_app_role.py gives it (rolled back)."""
    from db.append_only_tables import APPEND_ONLY_REVOKES

    conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lims_app"))
    for table, privileges in APPEND_ONLY_REVOKES.items():
        if conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar():
            conn.execute(text(f"REVOKE {', '.join(sorted(privileges))} ON TABLE {table} FROM lims_app"))
    conn.execute(text("SET ROLE lims_app"))
    conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
    conn.execute(text("SELECT set_config('app.client_id', :c, true)"), {"c": str(ids["client"])})
    try:
        yield
    finally:
        conn.execute(text("RESET ROLE"))


def _refused(conn, sql: str, params: dict, code: str) -> None:
    savepoint = conn.begin_nested()
    with pytest.raises(DBAPIError) as refused:
        conn.execute(text(sql), params)
    savepoint.rollback()
    assert code in str(refused.value), str(refused.value)


def _allowed(conn, sql: str, params: dict) -> None:
    savepoint = conn.begin_nested()
    conn.execute(text(sql), params)
    savepoint.commit()


# ---- schema shape ----------------------------------------------------------


def test_0123_schema_shape(migrated_engine):
    with migrated_engine.connect() as conn:
        cols = {
            (t, c): n
            for t, c, n in conn.execute(
                text(
                    "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('tests', 'results', 'entries', 'analysis_analytes', 'result_entries', "
                    "'lims_run_data_exclusions')"
                )
            )
        }
        assert cols[("tests", "lims_run_id")] == "YES"
        assert ("results", "lims_run_id") not in cols
        for col in ("official_set_id", "superseded_by", "superseded_at"):
            assert ("results", col) not in cols, col
        for col in ("display_order", "raw_units", "final_units_id", "knocked_out", "knocked_out_by", "knocked_out_at"):
            assert ("results", col) in cols, col
        assert cols[("results", "knocked_out")] == "NO"
        assert cols[("entries", "experiment_id")] == "YES"
        assert cols[("entries", "lims_run_id")] == "YES"
        assert cols[("analysis_analytes", "pairing_unit_id")] == "YES"
        assert ("analysis_analytes", "replicates") not in cols
        for col in (
            "entry_id", "test_id", "analyte_id", "replicate", "raw_result", "raw_units", "raw_origin",
            "final_units_id", "calculated_result", "reported_result", "qualifiers", "knocked_out",
            "knocked_out_by", "knocked_out_at", "display_order",
        ):
            assert ("result_entries", col) in cols, col
        assert ("result_entries", "count") not in cols
        assert cols[("lims_run_data_exclusions", "cleared_by")] == "YES"
        assert cols[("lims_run_data_exclusions", "cleared_at")] == "YES"

        rls = conn.execute(
            text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'result_entries'")
        ).one()
        assert tuple(rls) == (True, True)
        checks = set(
            conn.execute(
                text("SELECT conname FROM pg_constraint WHERE contype IN ('c', 'u')")
            ).scalars()
        )
        for name in (
            "ck_entries_experiment_xor_lims_run",
            "ck_results_knockout_fields",
            "ck_results_knockout_time",
            "uq_result_entries_test_analyte_replicate",
            "ck_lims_run_data_exclusions_cleared",
        ):
            assert name in checks, name
        assert "uq_experiment_data_exclusions_data_id" not in checks
        index = conn.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_lims_run_data_exclusions_active'")
        ).scalar_one()
        assert "UNIQUE" in index and "cleared_at IS NULL" in index
        grants = conn.execute(
            text("SELECT has_table_privilege('lims_app', 'public.result_entries', 'INSERT')")
        ).scalar()
        assert grants is True


# ---- entries: experiment XOR LIMS run --------------------------------------


def test_entries_belong_to_exactly_one_parent(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            experiment = conn.execute(text("SELECT id FROM experiments LIMIT 1")).scalar()
            base = (
                "INSERT INTO entries (id, experiment_id, lims_run_id, entry_type, name) "
                "VALUES (gen_random_uuid(), :e, :r, :t, 'x')"
            )
            _refused(conn, base, {"e": None, "r": None, "t": "experiment_data"}, "ck_entries_experiment_xor_lims_run")
            _refused(conn, base, {"e": None, "r": ids["run"], "t": "instructions"}, "ck_entries_experiment_xor_lims_run")
            _allowed(conn, base, {"e": None, "r": ids["run"], "t": "experiment_data"})
            _allowed(conn, base, {"e": None, "r": ids["run"], "t": "experiment_sample_data"})
            if experiment is not None:
                _refused(
                    conn, base, {"e": experiment, "r": ids["run"], "t": "experiment_data"},
                    "ck_entries_experiment_xor_lims_run",
                )
        finally:
            tx.rollback()


# ---- guards as lims_app ----------------------------------------------------


def test_result_guards_for_the_app_role(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            runless = uuid.uuid4()
            _insert_test(conn, ids, runless, None, f"S6NoRun-{uuid.uuid4().hex[:6]}")
            legacy = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO results (id, test_id, analyte_id, raw_result, entry_date, entered_by, active) "
                    "VALUES (:id, :t, :a, '1', CURRENT_DATE, :u, true)"
                ),
                {"id": legacy, "t": runless, "a": ids["analyte"], "u": ids["admin"]},
            )
            insert = (
                "INSERT INTO results (id, test_id, analyte_id, replicate, raw_result, calculated_result, "
                "entry_date, entered_by, active) "
                "VALUES (gen_random_uuid(), :t, :a, :rep, '1', :c, CURRENT_DATE, :u, true)"
            )
            with _as_app(conn, ids):
                _refused(
                    conn, insert, {"t": runless, "a": ids["analyte"], "rep": 2, "c": None, "u": ids["admin"]},
                    "result_test_has_no_run",
                )
                _refused(
                    conn, "UPDATE results SET raw_result = '2' WHERE id = :id", {"id": legacy},
                    "result_test_has_no_run",
                )
                # Retiring a legacy run-less result stays possible.
                _allowed(conn, "UPDATE results SET active = false WHERE id = :id", {"id": legacy})
                _refused(
                    conn, insert, {"t": ids["test"], "a": ids["analyte"], "rep": 1, "c": "5", "u": ids["admin"]},
                    "calculated_locked",
                )
                _allowed(conn, insert, {"t": ids["test"], "a": ids["analyte"], "rep": 1, "c": None, "u": ids["admin"]})
                # CALC-REQ-55: a second official row for the same key on a Test fails.
                _refused(
                    conn, insert, {"t": ids["test"], "a": ids["analyte"], "rep": 1, "c": None, "u": ids["admin"]},
                    "uq_results_test_analyte_replicate",
                )
                _refused(
                    conn, "UPDATE results SET lims_run_id = NULL WHERE test_id = :t", {"t": ids["test"]},
                    "lims_run_id",
                )
                _refused(
                    conn,
                    "UPDATE results SET calculated_result = '5' WHERE test_id = :t",
                    {"t": ids["test"]},
                    "calculated_locked",
                )
                _allowed(conn, "UPDATE results SET raw_result = '1.5' WHERE test_id = :t", {"t": ids["test"]})
                conn.execute(text("SELECT set_config('lims.calculation_write', 'on', true)"))
                _allowed(conn, "UPDATE results SET calculated_result = '5' WHERE test_id = :t", {"t": ids["test"]})
                conn.execute(text("SELECT set_config('lims.calculation_write', 'off', true)"))

                other_run = uuid.uuid4()
                conn.execute(text("RESET ROLE"))
                conn.execute(
                    text("INSERT INTO lims_runs (id, name, status, created_by) VALUES (:id, :n, 'draft', :u)"),
                    {"id": other_run, "n": f"S6R2-{uuid.uuid4().hex[:6]}", "u": ids["admin"]},
                )
                conn.execute(text("SET ROLE lims_app"))
                _refused(
                    conn, "UPDATE tests SET lims_run_id = :r WHERE id = :t",
                    {"r": other_run, "t": ids["test"]}, "test_run_immutable",
                )
                _refused(
                    conn, "UPDATE tests SET lims_run_id = NULL WHERE id = :t",
                    {"t": ids["test"]}, "test_run_immutable",
                )
                _allowed(conn, "UPDATE tests SET lims_run_id = :r WHERE id = :t", {"r": other_run, "t": runless})
        finally:
            tx.rollback()


def test_result_entry_guards_for_the_app_role(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            entry_id = _run_entry(conn, ids)
            data_entry = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO entries (id, lims_run_id, entry_type, name, created_by) "
                    "VALUES (:id, :r, 'experiment_data', 'Run data', :u)"
                ),
                {"id": data_entry, "r": ids["run"], "u": ids["admin"]},
            )
            row_id = _result_entry(conn, ids, entry_id)
            with _as_app(conn, ids):
                insert = (
                    "INSERT INTO result_entries (id, entry_id, test_id, analyte_id, replicate, "
                    "calculated_result, reported_result, created_by) "
                    "VALUES (gen_random_uuid(), :e, :t, :a, :rep, :c, :r, :u)"
                )
                common = {"t": ids["test"], "a": ids["analyte"], "u": ids["admin"]}
                _refused(conn, insert, {**common, "e": data_entry, "rep": 2, "c": None, "r": None}, "result_entry_scope")
                _refused(conn, insert, {**common, "e": entry_id, "rep": 2, "c": "1", "r": None}, "calculated_locked")
                _refused(conn, insert, {**common, "e": entry_id, "rep": 2, "c": None, "r": "1"}, "reported_before_calculation")
                _allowed(conn, insert, {**common, "e": entry_id, "rep": 2, "c": None, "r": None})

                upd = "UPDATE result_entries SET {} WHERE id = :id"
                _allowed(conn, upd.format("raw_result = '3', raw_origin = 'typed'"), {"id": row_id})
                _refused(conn, upd.format("calculated_result = '3'"), {"id": row_id}, "calculated_locked")
                _refused(conn, upd.format("reported_result = '3'"), {"id": row_id}, "reported_before_calculation")

                conn.execute(text("SELECT set_config('lims.calculation_write', 'on', true)"))
                _allowed(conn, upd.format("calculated_result = '3', reported_result = '3'"), {"id": row_id})
                _refused(conn, upd.format("raw_result = '4'"), {"id": row_id}, "calculation_changes_raw")
                conn.execute(text("SELECT set_config('lims.calculation_write', 'off', true)"))

                _allowed(conn, upd.format("reported_result = '3.0'"), {"id": row_id})
                _refused(conn, upd.format("calculated_result = NULL"), {"id": row_id}, "calculated_locked")
                _refused(conn, upd.format("entry_id = :e"), {"id": row_id, "e": data_entry}, "result_entry_scope")
            # The scope check runs for the migrator too.
            _refused(
                conn,
                "UPDATE result_entries SET entry_id = :e WHERE id = :id",
                {"id": row_id, "e": data_entry},
                "result_entry_scope",
            )
            _refused(
                conn,
                "INSERT INTO result_entries (id, entry_id, test_id, analyte_id) "
                "VALUES (gen_random_uuid(), :e, :t, :a)",
                {"e": entry_id, "t": ids["test"], "a": ids["analyte"]},
                "uq_result_entries_test_analyte_replicate",
            )
            _refused(
                conn,
                "UPDATE result_entries SET raw_result = 'x', raw_origin = NULL WHERE id = :id",
                {"id": row_id},
                "ck_result_entries_raw_has_origin",
            )
            _refused(
                conn,
                "UPDATE result_entries SET knocked_out_by = :u WHERE id = :id",
                {"id": row_id, "u": ids["admin"]},
                "ck_result_entries_knockout_fields",
            )
        finally:
            tx.rollback()


def test_pairing_unit_defaults_from_the_analyte(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            unit = conn.execute(text("SELECT id FROM units WHERE active LIMIT 1")).scalar_one()
            analyte = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO analytes (id, name, active, units_default) VALUES (:id, :n, true, :u)"
                ),
                {"id": analyte, "n": f"S6U-{uuid.uuid4().hex[:6]}", "u": unit},
            )
            conn.execute(
                text("INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required) VALUES (:a, :b, false)"),
                {"a": ids["analysis"], "b": analyte},
            )
            row = conn.execute(
                text(
                    "SELECT pairing_unit_id FROM analysis_analytes "
                    "WHERE analysis_id = :a AND analyte_id = :b"
                ),
                {"a": ids["analysis"], "b": analyte},
            ).one()
            assert tuple(row) == (unit,)
        finally:
            tx.rollback()


def test_knockout_record_is_kept_for_the_app_role(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            data_id, exclusion = uuid.uuid4(), uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO lims_run_data (id, lims_run_id, sample_id, row_data, created_by) "
                    "VALUES (:id, :r, :s, '{}', :u)"
                ),
                {"id": data_id, "r": ids["run"], "s": ids["sample"], "u": ids["admin"]},
            )
            conn.execute(
                text(
                    "INSERT INTO lims_run_data_exclusions (id, lims_run_data_id, excluded_by, client_id, reason) "
                    "VALUES (:id, :d, :u, :c, 'outlier')"
                ),
                {"id": exclusion, "d": data_id, "u": ids["admin"], "c": ids["client"]},
            )
            with _as_app(conn, ids):
                _refused(conn, "DELETE FROM lims_run_data_exclusions WHERE id = :id", {"id": exclusion}, "permission denied")
                conn.execute(text("RESET ROLE"))
                conn.execute(text("GRANT DELETE ON lims_run_data_exclusions TO lims_app"))
                conn.execute(text("SET ROLE lims_app"))
                _refused(conn, "DELETE FROM lims_run_data_exclusions WHERE id = :id", {"id": exclusion}, "exclusion_record_kept")
                _refused(
                    conn, "UPDATE lims_run_data_exclusions SET reason = 'other' WHERE id = :id",
                    {"id": exclusion}, "exclusion_record_kept",
                )
                _refused(
                    conn, "UPDATE lims_run_data_exclusions SET cleared_at = now() WHERE id = :id",
                    {"id": exclusion}, "",
                )
                _allowed(
                    conn,
                    "UPDATE lims_run_data_exclusions SET cleared_by = :u, cleared_at = now() WHERE id = :id",
                    {"id": exclusion, "u": ids["admin"]},
                )
                _refused(
                    conn,
                    "UPDATE lims_run_data_exclusions SET cleared_by = :u, cleared_at = now() WHERE id = :id",
                    {"id": exclusion, "u": ids["admin"]},
                    "exclusion_record_kept",
                )
                _allowed(
                    conn,
                    "INSERT INTO lims_run_data_exclusions (id, lims_run_data_id, excluded_by, client_id) "
                    "VALUES (gen_random_uuid(), :d, :u, :c)",
                    {"d": data_id, "u": ids["admin"], "c": ids["client"]},
                )
                _refused(
                    conn,
                    "INSERT INTO lims_run_data_exclusions (id, lims_run_data_id, excluded_by, client_id) "
                    "VALUES (gen_random_uuid(), :d, :u, :c)",
                    {"d": data_id, "u": ids["admin"], "c": ids["client"]},
                    "uq_lims_run_data_exclusions_active",
                )
            count = conn.execute(
                text("SELECT count(*) FROM lims_run_data_exclusions WHERE lims_run_data_id = :d"),
                {"d": data_id},
            ).scalar()
            assert count == 2
        finally:
            tx.rollback()


# ---- backfill, split, downgrade --------------------------------------------


@contextmanager
def _migrate_env(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = _alembic_cfg(url)
    previous = {k: os.environ.get(k) for k in ("DATABASE_URL", "MIGRATE_DATABASE_URL")}
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        yield cfg
    finally:
        command.upgrade(cfg, "head")
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_0123_backfills_and_splits_tests_by_run_then_downgrades(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        command.downgrade(cfg, PREVIOUS)
        with migrated_engine.begin() as conn:
            ids = _world(conn, with_run_on_test=False)
            run_b = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO lims_runs (id, name, status, created_by) "
                    "VALUES (:id, :n, 'published', :u)"
                ),
                {"id": run_b, "n": f"S6RB-{uuid.uuid4().hex[:6]}", "u": ids["admin"]},
            )
            mixed, single, empty, runless_and_run = (uuid.uuid4() for _ in range(4))
            for test_id, name in (
                (mixed, "mixed"), (single, "single"), (empty, "empty"), (runless_and_run, "both"),
            ):
                _insert_test(conn, ids, test_id, None, f"S6-{name}-{uuid.uuid4().hex[:6]}")
            add = (
                "INSERT INTO results (id, test_id, analyte_id, replicate, raw_result, lims_run_id, "
                "entry_date, entered_by, active) "
                "VALUES (gen_random_uuid(), :t, :a, :rep, :raw, :r, CURRENT_DATE, :u, true)"
            )
            for test_id, rep, raw, run in (
                (mixed, 1, "A1", ids["run"]),
                (mixed, 2, "B2", run_b),
                (single, 1, "S1", ids["run"]),
                (runless_and_run, 1, "manual", None),
                (runless_and_run, 2, "RB", run_b),
            ):
                conn.execute(
                    text(add),
                    {"t": test_id, "a": ids["analyte"], "rep": rep, "raw": raw, "r": run, "u": ids["admin"]},
                )

        command.upgrade(cfg, HEAD)
        with migrated_engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT t.id, t.name, t.lims_run_id, r.raw_result FROM tests t "
                    "LEFT JOIN results r ON r.test_id = t.id WHERE t.sample_id = :s"
                ),
                {"s": ids["sample"]},
            ).all()
        by_raw = {raw: (test_id, run) for test_id, _name, run, raw in rows if raw is not None}
        runs = {test_id: run for test_id, _name, run, _raw in rows}
        names = {test_id: name for test_id, name, _run, _raw in rows}

        with migrated_engine.connect() as conn:
            # The audit trigger stamps created_at; ties fall back to id.
            first, second = conn.execute(
                text("SELECT id FROM lims_runs WHERE id IN (:a, :b) ORDER BY created_at, id"),
                {"a": ids["run"], "b": run_b},
            ).scalars().all()
        raw_of = {ids["run"]: "A1", run_b: "B2"}

        assert runs[single] == ids["run"]
        assert runs[empty] is None and runs[ids["test"]] is None
        # The oldest run keeps the original Test; the later run gets a copy.
        assert by_raw[raw_of[first]] == (mixed, first)
        copy_test, copy_run = by_raw[raw_of[second]]
        assert copy_run == second and copy_test != mixed
        assert names[copy_test].startswith(names[mixed]) and "_run_" in names[copy_test]
        # Run-less results stay on the original Test, which stays run-less.
        assert by_raw["manual"] == (runless_and_run, None)
        rb_test, rb_run = by_raw["RB"]
        assert rb_run == run_b and rb_test != runless_and_run
        assert len(runs) == 7

        command.downgrade(cfg, PREVIOUS)
        with migrated_engine.connect() as conn:
            restored = dict(
                conn.execute(
                    text(
                        "SELECT r.raw_result, r.lims_run_id FROM results r "
                        "JOIN tests t ON t.id = r.test_id WHERE t.sample_id = :s"
                    ),
                    {"s": ids["sample"]},
                ).all()
            )
            test_cols = set(
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'tests' AND table_schema = 'public'"
                    )
                ).scalars()
            )
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == PREVIOUS
        assert "lims_run_id" not in test_cols
        assert restored == {"A1": ids["run"], "B2": run_b, "S1": ids["run"], "manual": None, "RB": run_b}

        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == HEAD


def test_0123_downgrade_drops_cleared_knockouts_and_run_entries(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        with migrated_engine.begin() as conn:
            ids = _world(conn)
            entry_id = _run_entry(conn, ids)
            _result_entry(conn, ids, entry_id)
            data_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO lims_run_data (id, lims_run_id, sample_id, row_data, created_by) "
                    "VALUES (:id, :r, :s, '{}', :u)"
                ),
                {"id": data_id, "r": ids["run"], "s": ids["sample"], "u": ids["admin"]},
            )
            conn.execute(
                text(
                    "INSERT INTO lims_run_data_exclusions "
                    "(id, lims_run_data_id, excluded_by, client_id, cleared_by, cleared_at) "
                    "VALUES (gen_random_uuid(), :d, :u, :c, :u, now())"
                ),
                {"d": data_id, "u": ids["admin"], "c": ids["client"]},
            )
            conn.execute(
                text(
                    "INSERT INTO lims_run_data_exclusions (id, lims_run_data_id, excluded_by, client_id) "
                    "VALUES (gen_random_uuid(), :d, :u, :c)"
                ),
                {"d": data_id, "u": ids["admin"], "c": ids["client"]},
            )
        command.downgrade(cfg, PREVIOUS)
        with migrated_engine.connect() as conn:
            kept = conn.execute(
                text("SELECT count(*) FROM lims_run_data_exclusions WHERE lims_run_data_id = :d"),
                {"d": data_id},
            ).scalar()
            entry = conn.execute(text("SELECT count(*) FROM entries WHERE id = :e"), {"e": entry_id}).scalar()
            unique = conn.execute(
                text("SELECT 1 FROM pg_constraint WHERE conname = 'uq_experiment_data_exclusions_data_id'")
            ).scalar()
        assert kept == 1
        assert entry == 0
        assert unique == 1
