"""Migration 0125: the analysis version does not rise when a save changes nothing.

Marc, 2026-11-22. The version counter is a deferred trigger, so these tests
commit for real and clean up after themselves (as the S7 version tests do).
"""
from __future__ import annotations

import uuid

from alembic import command
from sqlalchemy import text

from tests.test_calculation_config_s7_db import (
    SET_CONFIG,
    _commit_analysis,
    _params,
    _versions,
)
from tests.test_calculation_result_entry_s6_db import _as_app, _migrate_env

HEAD = "0125_analysis_version_no_change"
PREVIOUS = "0124_calculation_configuration"

SAME_AS_IT_IS = "UPDATE analyses SET description = description WHERE id = :a"
SAME_ANALYTE_ROW = (
    "UPDATE analysis_analytes SET is_required = is_required WHERE analysis_id = :a AND analyte_id = :b"
)


def _second_analyte(migrated_engine, ids):
    """A second analyte row on the analysis. Returns its id."""
    analyte = uuid.uuid4()
    with migrated_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO analytes (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
            {"id": analyte, "n": f"S8Ver2-{uuid.uuid4().hex[:6]}", "u": ids["admin"]},
        )
        conn.execute(
            text(
                "INSERT INTO analysis_analytes (analysis_id, analyte_id, is_required, display_order) "
                "VALUES (:a, :b, false, 2)"
            ),
            {"a": ids["analysis"], "b": analyte},
        )
    return analyte


def _drop_second_analyte(migrated_engine, ids, analyte) -> None:
    with migrated_engine.begin() as conn:
        conn.execute(
            text("DELETE FROM analysis_analytes WHERE analysis_id = :a AND analyte_id = :b"),
            {"a": ids["analysis"], "b": analyte},
        )
        conn.execute(text("DELETE FROM analytes WHERE id = :b"), {"b": analyte})


def test_a_save_that_writes_the_same_values_keeps_the_version_and_adds_no_snapshot(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        before_version, before_rows = _versions(migrated_engine, ids["analysis"])
        with migrated_engine.begin() as conn:
            conn.execute(text(SAME_AS_IT_IS), {"a": ids["analysis"]})
            conn.execute(text(SAME_ANALYTE_ROW), {"a": ids["analysis"], "b": ids["analyte"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == before_version == 1
        assert len(rows) == len(before_rows) == 1
        assert rows[0][1] == before_rows[0][1], "the snapshot is untouched"
    finally:
        cleanup()


def test_a_save_that_changes_only_audit_columns_keeps_the_version(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(
                text("UPDATE analyses SET modified_at = now() + interval '1 day', modified_by = :u WHERE id = :a"),
                {"a": ids["analysis"], "u": ids["admin"]},
            )
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 1 and [r[0] for r in rows] == [1]
    finally:
        cleanup()


def test_a_real_change_bumps_once_and_a_repeat_of_it_does_not_bump_again(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("UPDATE analyses SET description = 'one' WHERE id = :a"), {"a": ids["analysis"]})
            conn.execute(text("UPDATE analyses SET description = 'two' WHERE id = :a"), {"a": ids["analysis"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 2 and [r[0] for r in rows] == [1, 2], "two statements in one transaction are one version"
        assert rows[1][1]["analysis"]["description"] == "two"

        with migrated_engine.begin() as conn:
            conn.execute(text("UPDATE analyses SET description = 'two' WHERE id = :a"), {"a": ids["analysis"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 2 and [r[0] for r in rows] == [1, 2], "saving the same text again is not a change"
    finally:
        cleanup()


def test_a_change_that_is_undone_in_the_same_transaction_is_no_change(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("UPDATE analyses SET description = 'temporary' WHERE id = :a"), {"a": ids["analysis"]})
            conn.execute(text("UPDATE analyses SET description = NULL WHERE id = :a"), {"a": ids["analysis"]})
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 1 and [r[0] for r in rows] == [1]
    finally:
        cleanup()


def test_a_reorder_is_a_real_change_and_bumps_once_per_transaction(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    second = _second_analyte(migrated_engine, ids)
    try:
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 2, "adding an analyte row is a real change"
        assert [len(r[1]["analytes"]) for r in rows] == [1, 2]

        with migrated_engine.begin() as conn:
            conn.execute(
                text("UPDATE analysis_analytes SET display_order = 9 WHERE analysis_id = :a AND analyte_id = :b"),
                {"a": ids["analysis"], "b": ids["analyte"]},
            )
            conn.execute(
                text("UPDATE analysis_analytes SET display_order = 8 WHERE analysis_id = :a AND analyte_id = :b"),
                {"a": ids["analysis"], "b": second},
            )
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 3 and [r[0] for r in rows] == [1, 2, 3]
        by_analyte = {a["analyte_id"]: a["display_order"] for a in rows[2][1]["analytes"]}
        assert by_analyte == {str(ids["analyte"]): 9, str(second): 8}

        with migrated_engine.begin() as conn:
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Order"))
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 4

        with migrated_engine.begin() as conn:
            conn.execute(text(SET_CONFIG), _params(ids, order=3, name="Order"))
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 5, "a calculation order change is a real change"
        orders = {a["analyte_id"]: a["calculation_order"] for a in rows[4][1]["analytes"]}
        assert orders[str(ids["analyte"])] == 3
    finally:
        _drop_second_analyte(migrated_engine, ids, second)
        cleanup()


def test_removing_an_analyte_row_is_a_real_change(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    second = _second_analyte(migrated_engine, ids)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM analysis_analytes WHERE analysis_id = :a AND analyte_id = :b"),
                {"a": ids["analysis"], "b": second},
            )
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 3 and len(rows[2][1]["analytes"]) == 1
    finally:
        _drop_second_analyte(migrated_engine, ids, second)
        cleanup()


def test_a_calculation_configuration_edit_is_a_real_change_and_the_same_edit_again_is_not(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(ids["admin"])})
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Draft A"))
        version, _ = _versions(migrated_engine, ids["analysis"])
        assert version == 2

        with migrated_engine.begin() as conn:
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Draft A"))
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 2 and [r[0] for r in rows] == [1, 2], "writing the same configuration is not a change"

        with migrated_engine.begin() as conn:
            conn.execute(text(SET_CONFIG), _params(ids, order=2, name="Draft B"))
        version, rows = _versions(migrated_engine, ids["analysis"])
        assert version == 3 and rows[2][1]["analytes"][0]["calculation_config_name"] == "Draft B"
    finally:
        cleanup()


def test_a_no_change_save_as_the_app_role_keeps_the_version(migrated_engine):
    ids, cleanup = _commit_analysis(migrated_engine)
    try:
        with migrated_engine.connect() as conn:
            tx = conn.begin()
            with _as_app(conn, {**ids, "client": uuid.uuid4()}):
                conn.execute(text(SAME_AS_IT_IS), {"a": ids["analysis"]})
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
                version = conn.execute(
                    text("SELECT version FROM analyses WHERE id = :a"), {"a": ids["analysis"]}
                ).scalar()
                snapshots = conn.execute(
                    text("SELECT count(*) FROM analysis_versions WHERE analysis_id = :a"), {"a": ids["analysis"]}
                ).scalar()
            assert version == 1 and snapshots == 1
            tx.rollback()
    finally:
        cleanup()


def test_0125_downgrade_restores_the_0124_behaviour_and_upgrade_the_new_one(migrated_engine):
    with _migrate_env(migrated_engine) as cfg:
        ids, cleanup = _commit_analysis(migrated_engine)
        try:
            command.downgrade(cfg, PREVIOUS)
            with migrated_engine.connect() as conn:
                helpers = set(
                    conn.execute(
                        text(
                            "SELECT proname FROM pg_proc WHERE proname IN "
                            "('analysis_snapshot_of', 'analysis_snapshot_comparable')"
                        )
                    ).scalars()
                )
            assert helpers == set()
            with migrated_engine.begin() as conn:
                conn.execute(text(SAME_AS_IT_IS), {"a": ids["analysis"]})
            version, _ = _versions(migrated_engine, ids["analysis"])
            assert version == 2, "0124 bumped on a save that changed nothing"

            command.upgrade(cfg, HEAD)
            with migrated_engine.begin() as conn:
                conn.execute(text(SAME_AS_IT_IS), {"a": ids["analysis"]})
            version_after, rows = _versions(migrated_engine, ids["analysis"])
            assert version_after == 2 and [r[0] for r in rows] == [1, 2]
        finally:
            cleanup()
