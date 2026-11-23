"""Calculations S7: migration 0124 on the real Alembic chain.

Guards run for the app role (``lims_app``); the migrator and superusers skip
them (``skip_app_row_guard``). The version counter is a deferred trigger, so
its tests commit for real and clean up after themselves.
"""
from __future__ import annotations

import json
import uuid
from typing import Dict

import pytest
from alembic import command
from sqlalchemy import text

from tests.test_calculation_result_entry_s6_db import (
    _admin_id,
    _allowed,
    _as_app,
    _migrate_env,
    _refused,
    _world,
)

HEAD = "0124_calculation_configuration"
PREVIOUS = "0123_result_entry_data_model"

CONFIG = json.dumps({"name": "n", "stages": [], "result": {"stage": "s", "output": "o"}})

SET_CONFIG = (
    "UPDATE analysis_analytes SET calculation_order = :o, calculation_config_name = :n, "
    "calculation_config_version = 1, calculation_config = CAST(:c AS jsonb), "
    "calculation_config_state = :s WHERE analysis_id = :a AND analyte_id = :b"
)


def _params(ids: Dict[str, uuid.UUID], *, order: int = 1, name: str = "cfg", state: str = "draft") -> dict:
    return {"o": order, "n": name, "c": CONFIG, "s": state, "a": ids["analysis"], "b": ids["analyte"]}


# ---- schema shape -------------------------------------------------------------


def test_0124_schema_shape(migrated_engine):
    with migrated_engine.connect() as conn:
        cols = {
            (t, c): (n, d)
            for t, c, n, d in conn.execute(
                text(
                    "SELECT table_name, column_name, is_nullable, column_default "
                    "FROM information_schema.columns WHERE table_schema = 'public' AND table_name IN "
                    "('analyses', 'analysis_analytes', 'analysis_versions', 'calculation_formulas')"
                )
            )
        }
        assert cols[("analyses", "version")][0] == "NO" and cols[("analyses", "version")][1] == "1"
        for col in (
            "calculation_order", "calculation_config_name", "calculation_config_version",
            "calculation_config", "calculation_config_state",
        ):
            assert cols[("analysis_analytes", col)][0] == "YES", col
        assert ("analysis_analytes", "display_order") in cols
        for col in ("analysis_id", "version", "snapshot", "created_at", "created_by"):
            assert ("analysis_versions", col) in cols, col
        for col in ("name", "version", "formula_text", "description", "created_at", "created_by"):
            assert ("calculation_formulas", col) in cols, col
        # The free-text column is untouched and not the configuration.
        assert ("analysis_analytes", "calculation") in cols

        constraints = set(conn.execute(text("SELECT conname FROM pg_constraint")).scalars())
        for name in (
            "ck_analyses_version",
            "ck_analysis_analytes_calc_config_complete",
            "ck_analysis_analytes_calc_config_values",
            "uq_analysis_versions_analysis_version",
            "ck_analysis_versions_version",
            "ck_calculation_formulas_version",
            "ck_calculation_formulas_text",
        ):
            assert name in constraints, name
        indexes = dict(conn.execute(text("SELECT indexname, indexdef FROM pg_indexes")).all())
        assert "UNIQUE" in indexes["uq_analysis_analytes_calculation_order"]
        assert "calculation_order IS NOT NULL" in indexes["uq_analysis_analytes_calculation_order"]
        assert "lower" in indexes["uq_analysis_analytes_calculation_config_name"]
        assert "UNIQUE" in indexes["uq_calculation_formulas_name_version"]

        triggers = {
            row[0]: row[1]
            for row in conn.execute(
                text(
                    "SELECT tgname, tgdeferrable FROM pg_trigger "
                    "WHERE tgname IN ('analyses_guard_version', 'analysis_analytes_guard_calculation', "
                    "'analyses_record_version', 'analysis_analytes_record_version')"
                )
            )
        }
        assert set(triggers) == {
            "analyses_guard_version", "analysis_analytes_guard_calculation",
            "analyses_record_version", "analysis_analytes_record_version",
        }
        assert triggers["analyses_record_version"] and triggers["analysis_analytes_record_version"]
        assert not triggers["analyses_guard_version"]

        for table, privilege, expected in (
            ("analysis_versions", "SELECT", True),
            ("analysis_versions", "INSERT", False),
            ("analysis_versions", "UPDATE", False),
            ("analysis_versions", "DELETE", False),
            ("calculation_formulas", "SELECT", True),
            ("calculation_formulas", "INSERT", True),
            ("calculation_formulas", "UPDATE", False),
            ("calculation_formulas", "DELETE", False),
        ):
            granted = conn.execute(
                text("SELECT has_table_privilege('lims_app', :t, :p)"), {"t": f"public.{table}", "p": privilege}
            ).scalar()
            assert granted is expected, (table, privilege)

        prefixed = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'analysis_analytes' AND column_name LIKE 'calculation_%'"
            )
        ).scalar()
        assert prefixed == 5


def test_0124_has_no_seed_rows_for_formulas(migrated_engine):
    with migrated_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM calculation_formulas")).scalar() == 0


# ---- the configuration columns ------------------------------------------------


def test_configuration_columns_are_all_or_nothing_and_unique(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            second = uuid.uuid4()
            conn.execute(
                text("INSERT INTO analytes (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
                {"id": second, "n": f"S7Second-{uuid.uuid4().hex[:6]}", "u": ids["admin"]},
            )
            conn.execute(
                text("INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required) VALUES (:a, :b, false)"),
                {"a": ids["analysis"], "b": second},
            )
            _refused(
                conn,
                "UPDATE analysis_analytes SET calculation_order = 1 WHERE analysis_id = :a AND analyte_id = :b",
                {"a": ids["analysis"], "b": ids["analyte"]},
                "ck_analysis_analytes_calc_config_complete",
            )
            _refused(
                conn,
                "UPDATE analysis_analytes SET calculation_config_name = 'x' WHERE analysis_id = :a AND analyte_id = :b",
                {"a": ids["analysis"], "b": ids["analyte"]},
                "ck_analysis_analytes_calc_config_complete",
            )
            _refused(conn, SET_CONFIG, _params(ids, order=0), "ck_analysis_analytes_calc_config_values")
            _refused(conn, SET_CONFIG, _params(ids, order=-3), "ck_analysis_analytes_calc_config_values")
            _refused(conn, SET_CONFIG, _params(ids, state="archived"), "ck_analysis_analytes_calc_config_values")
            _refused(conn, SET_CONFIG, _params(ids, name="  "), "ck_analysis_analytes_calc_config_values")
            _allowed(conn, SET_CONFIG, _params(ids, order=3, name="First"))

            other = dict(_params(ids, order=3, name="Other"), b=second)
            _refused(conn, SET_CONFIG, other, "uq_analysis_analytes_calculation_order")
            other = dict(_params(ids, order=4, name="first"), b=second)
            _refused(conn, SET_CONFIG, other, "uq_analysis_analytes_calculation_config_name")
            _allowed(conn, SET_CONFIG, dict(_params(ids, order=4, name="Second"), b=second))

            # display_order is its own column and may repeat.
            conn.execute(text("UPDATE analysis_analytes SET display_order = 1 WHERE analysis_id = :a"), {"a": ids["analysis"]})
        finally:
            tx.rollback()


def test_formula_rows_are_unique_by_name_and_version(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            admin = _admin_id(conn)
            insert = (
                "INSERT INTO calculation_formulas (name, version, formula_text, created_by) "
                "VALUES (:n, :v, :t, :u)"
            )
            base = {"n": "Blank Correct", "v": 1, "t": "od - blank", "u": admin}
            _allowed(conn, insert, base)
            _refused(conn, insert, dict(base, n="BLANK correct"), "uq_calculation_formulas_name_version")
            _allowed(conn, insert, dict(base, v=2, t="od + blank"))
            _refused(conn, insert, dict(base, n="x", v=0), "ck_calculation_formulas_version")
            _refused(conn, insert, dict(base, n="y", t="   "), "ck_calculation_formulas_text")
            _refused(conn, insert, dict(base, n="z", t="1" * 2001), "ck_calculation_formulas_text")
        finally:
            tx.rollback()


# ---- guards as lims_app -------------------------------------------------------


def test_the_app_role_cannot_write_the_analysis_version(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            with _as_app(conn, ids):
                new_id = uuid.uuid4()
                _refused(
                    conn,
                    "INSERT INTO analyses (id, name, version, active) VALUES (:i, :n, 5, true)",
                    {"i": new_id, "n": f"S7V-{uuid.uuid4().hex[:6]}"},
                    "analysis_version_locked",
                )
                _allowed(
                    conn,
                    "INSERT INTO analyses (id, name, active) VALUES (:i, :n, true)",
                    {"i": new_id, "n": f"S7V-{uuid.uuid4().hex[:6]}"},
                )
                assert conn.execute(text("SELECT version FROM analyses WHERE id = :i"), {"i": new_id}).scalar() == 1
                _refused(
                    conn, "UPDATE analyses SET version = 9 WHERE id = :i", {"i": ids["analysis"]},
                    "analysis_version_locked",
                )
                _refused(
                    conn, "UPDATE analyses SET version = version + 1 WHERE id = :i", {"i": ids["analysis"]},
                    "analysis_version_locked",
                )
                _allowed(
                    conn, "UPDATE analyses SET description = 'edited' WHERE id = :i", {"i": ids["analysis"]},
                )
        finally:
            tx.rollback()


def test_activation_is_a_flag_the_app_cannot_set_by_writing(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            with _as_app(conn, ids):
                _allowed(conn, SET_CONFIG, _params(ids))
                _refused(conn, SET_CONFIG, _params(ids, state="active"), "calculation_activation_required")
                _refused(
                    conn,
                    "INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required, calculation_order, "
                    "calculation_config_name, calculation_config_version, calculation_config, calculation_config_state) "
                    "SELECT :a, id, false, 9, 'x', 1, CAST(:c AS jsonb), 'active' FROM analytes WHERE id <> :b LIMIT 1",
                    {"a": ids["analysis"], "b": ids["analyte"], "c": CONFIG},
                    "calculation_activation_required",
                )
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'on', true)"))
                _allowed(conn, SET_CONFIG, _params(ids, state="active"))
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'off', true)"))
        finally:
            tx.rollback()


def test_an_active_configuration_is_immutable_for_the_app_role(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            with _as_app(conn, ids):
                _allowed(conn, SET_CONFIG, _params(ids))
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'on', true)"))
                _allowed(conn, SET_CONFIG, _params(ids, state="active"))
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'off', true)"))

                where = {"a": ids["analysis"], "b": ids["analyte"]}
                tail = " WHERE analysis_id = :a AND analyte_id = :b"
                for change in (
                    "calculation_config = CAST('{\"changed\": true}' AS jsonb)",
                    "calculation_config_name = 'renamed'",
                    "calculation_config_version = 2",
                    "calculation_order = 7",
                    "calculation_config = NULL, calculation_config_name = NULL, "
                    "calculation_config_version = NULL, calculation_order = NULL, calculation_config_state = NULL",
                    "calculation_config_state = 'draft'",
                ):
                    _refused(conn, f"UPDATE analysis_analytes SET {change}{tail}", where, "calculation_config_active")
                _refused(conn, f"DELETE FROM analysis_analytes{tail}", where, "calculation_config_active")

                # Columns that are not the calculation stay editable.
                _allowed(conn, f"UPDATE analysis_analytes SET is_required = true{tail}", where)
                _allowed(conn, f"UPDATE analysis_analytes SET calculation_order = calculation_order{tail}", where)
        finally:
            tx.rollback()


def test_new_version_flag_allows_only_active_to_draft_with_the_same_content(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            with _as_app(conn, ids):
                _allowed(conn, SET_CONFIG, _params(ids))
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'on', true)"))
                _allowed(conn, SET_CONFIG, _params(ids, state="active"))
                conn.execute(text("SELECT set_config('lims.calculation_activate', 'off', true)"))

                conn.execute(text("SELECT set_config('lims.calculation_new_version', 'on', true)"))
                where = {"a": ids["analysis"], "b": ids["analyte"]}
                tail = " WHERE analysis_id = :a AND analyte_id = :b"
                _refused(
                    conn,
                    "UPDATE analysis_analytes SET calculation_config_state = 'draft', "
                    "calculation_config = CAST('{\"changed\": true}' AS jsonb)" + tail,
                    where,
                    "calculation_config_active",
                )
                _refused(
                    conn,
                    "UPDATE analysis_analytes SET calculation_config_state = 'draft', calculation_order = 8" + tail,
                    where,
                    "calculation_config_active",
                )
                _allowed(conn, f"UPDATE analysis_analytes SET calculation_config_state = 'draft'{tail}", where)
                conn.execute(text("SELECT set_config('lims.calculation_new_version', 'off', true)"))

                state = conn.execute(
                    text("SELECT calculation_config_state, calculation_order FROM analysis_analytes" + tail),
                    where,
                ).one()
                assert tuple(state) == ("draft", 1)
                # Back to draft, the content may change again.
                _allowed(conn, SET_CONFIG, _params(ids, order=5, name="edited"))
        finally:
            tx.rollback()


def test_superusers_and_the_migrator_skip_the_guards(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            _allowed(conn, SET_CONFIG, _params(ids, state="active"))
            _allowed(conn, SET_CONFIG, _params(ids, order=2, state="active"))
            _allowed(conn, "UPDATE analyses SET version = 4 WHERE id = :a", {"a": ids["analysis"]})
        finally:
            tx.rollback()


def test_the_app_role_cannot_write_versions_or_change_a_saved_formula(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            ids = _world(conn)
            with _as_app(conn, ids):
                _allowed(
                    conn,
                    "INSERT INTO calculation_formulas (name, version, formula_text, created_by) "
                    "VALUES ('App Saved', 1, 'a + b', :u)",
                    {"u": ids["admin"]},
                )
                for sql in (
                    "UPDATE calculation_formulas SET formula_text = 'a - b' WHERE name = 'App Saved'",
                    "DELETE FROM calculation_formulas WHERE name = 'App Saved'",
                    "INSERT INTO analysis_versions (analysis_id, version, snapshot) VALUES (:a, 99, '{}')",
                    "UPDATE analysis_versions SET snapshot = '{}' WHERE analysis_id = :a",
                    "DELETE FROM analysis_versions WHERE analysis_id = :a",
                ):
                    _refused(conn, sql, {"a": ids["analysis"]}, "permission denied")
        finally:
            tx.rollback()


# ---- the version counter and the snapshots ------------------------------------


def _commit_analysis(migrated_engine):
    """An analysis with one analyte, committed. Returns ids and a cleanup."""
    ids: Dict[str, uuid.UUID] = {"analysis": uuid.uuid4(), "analyte": uuid.uuid4()}
    tag = uuid.uuid4().hex[:6]
    with migrated_engine.begin() as conn:
        ids["admin"] = _admin_id(conn)
        conn.execute(
            text("INSERT INTO analyses (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
            {"id": ids["analysis"], "n": f"S7Ver-{tag}", "u": ids["admin"]},
        )
        conn.execute(
            text("INSERT INTO analytes (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
            {"id": ids["analyte"], "n": f"S7VerAn-{tag}", "u": ids["admin"]},
        )
        conn.execute(
            text("INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required) VALUES (:a, :b, false)"),
            {"a": ids["analysis"], "b": ids["analyte"]},
        )

    def cleanup() -> None:
        with migrated_engine.begin() as conn:
            conn.execute(text("DELETE FROM analysis_analytes WHERE analysis_id = :a"), {"a": ids["analysis"]})
            conn.execute(text("DELETE FROM analyses WHERE id = :a"), {"a": ids["analysis"]})
            conn.execute(text("DELETE FROM analytes WHERE id = :b"), {"b": ids["analyte"]})

    return ids, cleanup


def _versions(migrated_engine, analysis_id):
    with migrated_engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM analyses WHERE id = :a"), {"a": analysis_id}).scalar()
        rows = conn.execute(
            text("SELECT version, snapshot, created_by FROM analysis_versions WHERE analysis_id = :a ORDER BY version"),
            {"a": analysis_id},
        ).all()
    return version, rows


def test_a_new_analysis_is_version_1_with_a_snapshot_of_what_committed(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 1
        assert [r[0] for r in rows] == [1]
        snapshot = rows[0][1]
        assert snapshot["analysis"]["id"] == str(ids["analysis"])
        assert [a["analyte_id"] for a in snapshot["analytes"]] == [str(ids["analyte"])]
    finally:
        cleanup()


def test_each_committed_change_bumps_the_version_once_and_keeps_the_old_snapshot(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Draft A"))
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Draft B"))
            conn.execute(text("UPDATE analyses SET description = 'edited' WHERE id = :a"), {"a": ids["analysis"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 2, "three statements in one transaction are one version"
        assert [r[0] for r in rows] == [1, 2]
        v1, v2 = rows[0][1], rows[1][1]
        assert v1["analytes"][0]["calculation_config"] is None
        assert v2["analytes"][0]["calculation_config_name"] == "Draft B"
        assert v2["analytes"][0]["calculation_order"] == 2
        assert v2["analysis"]["description"] == "edited" and v2["analysis"]["version"] == 2
        assert rows[1][2] == ids["admin"], "the author is the user of the transaction"

        with migrated_engine.begin() as conn:
            conn.execute(text("UPDATE analyses SET description = 'again' WHERE id = :a"), {"a": ids["analysis"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 3 and [r[0] for r in rows] == [1, 2, 3]
        assert rows[0][1] == v1 and rows[1][1] == v2, "an earlier version is never rewritten"
        assert rows[2][2] is None, "no user in the session leaves the author empty"

        with migrated_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM analysis_analytes WHERE analysis_id = :a AND analyte_id = :b"),
                {"a": ids["analysis"], "b": ids["analyte"]},
            )
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 4 and rows[3][1]["analytes"] == []
    finally:
        cleanup()


def test_a_rolled_back_change_does_not_bump_the_version(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.connect() as conn:
            tx = conn.begin()
            conn.execute(text(SET_CONFIG), _params(ids))
            tx.rollback()
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 1 and [r[0] for r in rows] == [1]
    finally:
        cleanup()


def test_a_change_made_as_the_app_role_bumps_the_version_the_app_cannot_write(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.connect() as conn:
            tx = conn.begin()
            with _as_app(conn, {**ids, "client": uuid.uuid4()}):
                conn.execute(text(SET_CONFIG), _params(ids, order=3, name="By app"))
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
                version = conn.execute(text("SELECT version FROM analyses WHERE id = :a"), {"a": ids["analysis"]}).scalar()
                assert version == 2
                snapshots = conn.execute(
                    text("SELECT count(*) FROM analysis_versions WHERE analysis_id = :a"), {"a": ids["analysis"]}
                ).scalar()
                assert snapshots == 2
            tx.rollback()
    finally:
        cleanup()


# ---- downgrade and upgrade ----------------------------------------------------


def test_0124_downgrade_removes_everything_and_upgrade_restores_it(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        ids, cleanup = _commit_analysis(migrated_engine)
        try:
            command.downgrade(cfg, PREVIOUS)
            with migrated_engine.connect() as conn:
                cols = set(
                    conn.execute(
                        text(
                            "SELECT table_name || '.' || column_name FROM information_schema.columns "
                            "WHERE table_schema = 'public' AND table_name IN ('analyses', 'analysis_analytes')"
                        )
                    ).scalars()
                )
                tables = set(
                    conn.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
                            "AND table_name IN ('analysis_versions', 'calculation_formulas')"
                        )
                    ).scalars()
                )
                functions = set(
                    conn.execute(
                        text(
                            "SELECT proname FROM pg_proc WHERE proname IN ('record_analysis_version', "
                            "'guard_analysis_version', 'guard_analysis_analyte_calculation', "
                            "'calculation_new_version_allowed', 'calculation_activate_allowed', "
                            "'analysis_version_bump_allowed')"
                        )
                    ).scalars()
                )
                version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == PREVIOUS
            assert "analyses.version" not in cols
            assert not {c for c in cols if "calculation_config" in c or c.endswith("calculation_order")}
            assert "analysis_analytes.calculation" in cols
            assert tables == set() and functions == set()

            command.upgrade(cfg, HEAD)
            version_after, rows = _versions(migrated_engine, ids["analysis"])
            assert version_after == 1, "the analysis comes back at version 1"
            assert [r[0] for r in rows] == [1], "and the upgrade writes its version 1 snapshot"
            assert rows[0][1]["analytes"][0]["analyte_id"] == str(ids["analyte"])
        finally:
            cleanup()
