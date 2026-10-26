"""Follow-ups on #226: fail instead of cancel after import, and tighter scoping.

No plate math. Every check here is about status, linking, privileges, or
upload reads.
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.security import get_password_hash
from app.schemas.sample import MAX_RECEIPT_VOLUME_UL, SampleCreate
from tests.test_elisa_run_gaps import _analysis, _publish, _run, _sample, _template

NOT_ON_RUN = "Not on this run"
DIFFERENT = "Client sample ID and sample name match different samples"
ALSO_OFF_RUN = (
    "Linked to the sample on this run; another sample not on this run has the same identifier"
)
VERSIONS = Path(__file__).resolve().parents[1] / "db" / "migrations" / "versions"
REAGENT_TABLES = ("vendors", "reagents", "reagent_vendors", "reagent_lots", "reagent_uses")


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _import(client, auth_headers, run_id, rows):
    return client.post(
        f"/v1/lims-runs/{run_id}/import", json={"rows": rows}, headers=auth_headers
    )


def _plate(client, auth_headers, db_session, test_admin_user, test_org, prefix="RUN"):
    sample = _sample(db_session, test_admin_user, test_org, f"{prefix}-{uuid.uuid4().hex[:6]}")
    analysis, analyte = _analysis(db_session, test_admin_user)
    template_id = _template(client, auth_headers)
    run_id = _run(client, auth_headers, template_id, str(analysis.id), str(sample.id))
    return run_id, sample, analysis, analyte, template_id


# ---------- 7: cancel only before import; fail after ----------


def test_cancel_is_allowed_before_any_import_row(
    client, auth_headers, db_session, test_admin_user, test_org
):
    run_id, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    before = client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers)
    assert before.json()["has_imported_data"] is False
    canceled = client.patch(f"/v1/lims-runs/{run_id}/cancel", headers=auth_headers)
    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["status"] == "canceled"


def test_a_rejected_import_attempt_stores_nothing_and_cancel_still_works(
    client, auth_headers, db_session, test_admin_user, test_org
):
    run_id, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    refused = _import(client, auth_headers, run_id, [{"sample_key": "K" * 256, "row_data": {"corr": "1"}}])
    assert refused.status_code == 422, refused.text
    assert client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers).json()["has_imported_data"] is False
    assert client.patch(f"/v1/lims-runs/{run_id}/cancel", headers=auth_headers).status_code == 200


@pytest.mark.parametrize("linked", [True, False], ids=["linked-row", "unmatched-row-only"])
def test_cancel_after_import_is_422_and_points_to_fail(
    client, auth_headers, db_session, test_admin_user, test_org, linked
):
    run_id, sample, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    row = (
        {"sample_id": str(sample.id), "row_data": {"corr": "1.10"}}
        if linked
        else {"sample_key": "STD-S1", "well_position": "A1", "row_data": {"corr": "2.0"}}
    )
    imported = _import(client, auth_headers, run_id, [row])
    assert imported.status_code == 200, imported.text
    assert (imported.json()["rows"][0]["sample_id"] is not None) is linked

    detail = client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers).json()
    assert detail["has_imported_data"] is True

    refused = client.patch(f"/v1/lims-runs/{run_id}/cancel", headers=auth_headers)
    assert refused.status_code == 422, refused.text
    body = refused.json()["detail"]
    assert body["code"] == "run_has_imported_data"
    assert "cannot be canceled" in body["message"]
    assert "Fail the run" in body["message"]
    assert f"/v1/lims-runs/{run_id}/fail" in body["message"]
    assert client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers).json()["status"] == "running"

    failed = client.post(
        f"/v1/lims-runs/{run_id}/fail", json={"reason": "Wrong plate map"}, headers=auth_headers
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "failed"
    assert failed.json()["status_reason"] == "Wrong plate map"
    assert failed.json()["rejected_at"] is not None
    listed = client.get(f"/v1/lims-runs/{run_id}/data", headers=auth_headers)
    assert listed.json()["total"] == 1


def test_fail_requires_a_reason_and_reject_is_the_same_action(
    client, auth_headers, db_session, test_admin_user, test_org
):
    run_id, sample, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    for reason in ("", "   "):
        response = client.post(
            f"/v1/lims-runs/{run_id}/fail", json={"reason": reason}, headers=auth_headers
        )
        assert response.status_code == 422, response.text
    assert client.post(f"/v1/lims-runs/{run_id}/fail", json={}, headers=auth_headers).status_code == 422

    other_id, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    legacy = client.post(
        f"/v1/lims-runs/{other_id}/reject", json={"reason": "QC-H out of range"}, headers=auth_headers
    )
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["status"] == "failed"
    assert legacy.json()["status_reason"] == "QC-H out of range"


def test_run_canceled_after_import_counts_as_failed_for_acceptance(
    client, auth_headers, db_session, test_admin_user, test_org
):
    from models.flexible_experiment import LimsRun, LimsRunStatus
    from models.result_acceptance import ResultAcceptance

    run_id, sample, analysis, analyte, template_id = _plate(
        client, auth_headers, db_session, test_admin_user, test_org
    )
    first = _import(
        client, auth_headers, run_id,
        [{"sample_id": str(sample.id), "row_data": {"corr": "1.10", "replicate": 1}}],
    )
    assert first.status_code == 200, first.text

    # A row from before this rule: canceled after its data was imported.
    legacy = db_session.get(LimsRun, uuid.UUID(run_id))
    legacy.status = LimsRunStatus.canceled
    legacy.canceled_at = datetime.now(timezone.utc)
    db_session.commit()

    rerun = client.post(f"/v1/lims-runs/{run_id}/rerun", json={}, headers=auth_headers)
    assert rerun.status_code == 201, rerun.text
    rerun_id = rerun.json()["id"]
    started = client.patch(
        f"/v1/lims-runs/{rerun_id}/start", json={"sample_ids": [str(sample.id)]}, headers=auth_headers
    )
    assert started.status_code == 200, started.text
    second = _import(
        client, auth_headers, rerun_id,
        [{"sample_id": str(sample.id), "row_data": {"corr": "2.20", "replicate": 1}}],
    )
    assert second.status_code == 200, second.text
    assert _publish(client, auth_headers, rerun_id).status_code == 200

    choices = client.get(f"/v1/lims-runs/{rerun_id}/value-choices", headers=auth_headers)
    assert choices.status_code == 200, choices.text
    options = {opt["lims_run_id"]: opt for opt in choices.json()[0]["options"]}
    assert options[run_id]["run_status"] == "canceled"
    assert options[run_id]["counts_as_failed"] is True
    assert options[rerun_id]["counts_as_failed"] is False

    body = {
        "sample_id": str(sample.id),
        "analyte_id": str(analyte.id),
        "replicate": 1,
        "accepted_lims_run_id": run_id,
        "reason": "Report the legacy plate",
    }
    missing = client.post(f"/v1/lims-runs/{rerun_id}/value-choices", json=body, headers=auth_headers)
    assert missing.status_code == 422, missing.text
    assert "failed run" in missing.json()["detail"]
    blank = client.post(
        f"/v1/lims-runs/{rerun_id}/value-choices",
        json=dict(body, override_failed=True, reason=" "),
        headers=auth_headers,
    )
    assert blank.status_code == 422, blank.text
    accepted = client.post(
        f"/v1/lims-runs/{rerun_id}/value-choices",
        json=dict(body, override_failed=True),
        headers=auth_headers,
    )
    assert accepted.status_code == 200, accepted.text

    db_session.expire_all()
    assert db_session.get(LimsRun, uuid.UUID(run_id)).status == LimsRunStatus.canceled
    pick = (
        db_session.query(ResultAcceptance)
        .filter(ResultAcceptance.sample_id == sample.id, ResultAcceptance.active == True)  # noqa: E712
        .one()
    )
    assert pick.override_failed is True
    assert pick.reason == "Report the legacy plate"


def test_canceled_without_data_does_not_count_as_failed(
    client, auth_headers, db_session, test_admin_user, test_org
):
    from app.services.run_failure import counts_as_failed, has_imported_data
    from models.flexible_experiment import LimsRun

    run_id, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    assert client.patch(f"/v1/lims-runs/{run_id}/cancel", headers=auth_headers).status_code == 200
    db_session.expire_all()
    run = db_session.get(LimsRun, uuid.UUID(run_id))
    assert has_imported_data(db_session, run.id) is False
    assert counts_as_failed(db_session, run) is False


# ---------- 5, 6, 4: on-run linking and promotion ----------


def test_json_import_with_explicit_off_run_sample_id(
    client, auth_headers, db_session, test_admin_user, test_org
):
    run_id, on_run, *_ = _plate(client, auth_headers, db_session, test_admin_user, test_org)
    off = _sample(db_session, test_admin_user, test_org, f"OFF-{uuid.uuid4().hex[:6]}")
    imported = _import(
        client, auth_headers, run_id,
        [
            {"well_position": "A1", "sample_id": str(on_run.id), "row_data": {"corr": "1"}},
            {"well_position": "A2", "sample_id": str(off.id), "row_data": {"corr": "1"}},
            {
                "well_position": "A3",
                "sample_id": str(off.id),
                "sample_key": on_run.client_sample_id,
                "row_data": {"corr": "1"},
            },
        ],
    )
    assert imported.status_code == 200, imported.text
    by_well = {row["well_position"]: row for row in imported.json()["rows"]}
    assert by_well["A1"]["sample_id"] == str(on_run.id)
    assert by_well["A1"]["link_note"] is None
    assert by_well["A2"]["sample_id"] is None
    assert by_well["A2"]["link_note"] == NOT_ON_RUN
    assert by_well["A3"]["sample_id"] == str(on_run.id)
    assert client.get(f"/v1/lims-runs/{run_id}/data", headers=auth_headers).json()["total"] == 3


def test_matches_are_narrowed_to_the_run_before_the_duplicate_check(
    client, auth_headers, db_session, test_admin_user, test_org
):
    on_client = _sample(db_session, test_admin_user, test_org, f"NC-{uuid.uuid4().hex[:6]}")
    off_named = _sample(db_session, test_admin_user, test_org, f"NN-{uuid.uuid4().hex[:6]}")
    off_named.name = on_client.client_sample_id
    both_client = _sample(db_session, test_admin_user, test_org, f"BC-{uuid.uuid4().hex[:6]}")
    both_named = _sample(db_session, test_admin_user, test_org, f"BN-{uuid.uuid4().hex[:6]}")
    both_named.name = both_client.client_sample_id
    db_session.commit()

    analysis, _analyte = _analysis(db_session, test_admin_user)
    template_id = _template(client, auth_headers)
    created = client.post(
        "/v1/lims-runs",
        json={"name": f"Plate {uuid.uuid4().hex[:8]}", "experiment_template_id": template_id, "analysis_id": str(analysis.id)},
        headers=auth_headers,
    )
    run_id = created.json()["id"]
    cohort = [str(on_client.id), str(both_client.id), str(both_named.id)]
    started = client.patch(f"/v1/lims-runs/{run_id}/start", json={"sample_ids": cohort}, headers=auth_headers)
    assert started.status_code == 200, started.text

    imported = _import(
        client, auth_headers, run_id,
        [
            {"well_position": "B1", "sample_key": on_client.client_sample_id, "row_data": {"corr": "1"}},
            {"well_position": "B2", "sample_key": both_client.client_sample_id, "row_data": {"corr": "1"}},
        ],
    )
    assert imported.status_code == 200, imported.text
    by_well = {row["well_position"]: row for row in imported.json()["rows"]}
    assert by_well["B1"]["sample_id"] == str(on_client.id)
    assert by_well["B1"]["link_note"] == ALSO_OFF_RUN
    assert by_well["B2"]["sample_id"] is None
    assert by_well["B2"]["link_note"] == DIFFERENT


def test_promotion_skips_rows_for_samples_not_on_the_run(
    client, auth_headers, db_session, test_admin_user, test_org
):
    from models.flexible_experiment import LimsRunData
    from models.result import Result
    from models.test import Test

    run_id, on_run, analysis, analyte, _tpl = _plate(
        client, auth_headers, db_session, test_admin_user, test_org
    )
    off = _sample(db_session, test_admin_user, test_org, f"OFFP-{uuid.uuid4().hex[:6]}")
    assert _import(
        client, auth_headers, run_id,
        [{"sample_id": str(on_run.id), "row_data": {"corr": "1.10", "replicate": 1}}],
    ).status_code == 200
    # A stored row bound to a sample outside the cohort (written before on-run linking).
    stray = LimsRunData(
        lims_run_id=uuid.UUID(run_id),
        sample_id=off.id,
        well_position="H12",
        row_data={"corr": "9.99", "replicate": 1},
        created_by=test_admin_user.id,
    )
    db_session.add(stray)
    db_session.commit()

    preview = client.get(f"/v1/lims-runs/{run_id}/promotion/preview", headers=auth_headers)
    assert preview.status_code == 200, preview.text
    plan = preview.json()
    skipped = [item for item in plan["items"] if item["lims_run_data_id"] == str(stray.id)]
    assert len(skipped) == 1
    assert skipped[0]["action"] == "skip"
    assert skipped[0]["message"] == NOT_ON_RUN
    assert plan["create_count"] == 1
    assert plan["errors"] == []

    assert _publish(client, auth_headers, run_id).status_code == 200
    db_session.expire_all()
    assert db_session.query(Test).filter(Test.sample_id == off.id).count() == 0
    stored = db_session.query(Result).filter(Result.analyte_id == analyte.id).all()
    assert [row.raw_result for row in stored] == ["1.10"]


# ---------- 5: SampleCreate volume bounds ----------


def test_sample_create_volume_bounds():
    base = {"sample_type": str(uuid.uuid4()), "status": str(uuid.uuid4())}
    assert SampleCreate(**base, volume_ul=0).volume_ul == 0
    assert SampleCreate(**base, volume_ul=MAX_RECEIPT_VOLUME_UL).volume_ul == MAX_RECEIPT_VOLUME_UL
    assert SampleCreate(**base).volume_ul is None
    for bad in (-1, -0.001, MAX_RECEIPT_VOLUME_UL + 1, float("nan"), float("inf"), float("-inf"), "lots", True):
        with pytest.raises(ValidationError):
            SampleCreate(**base, volume_ul=bad)
    for bad in ("NaN", "Infinity", "1e400"):
        with pytest.raises(ValidationError):
            SampleCreate(**base, volume_ul=bad)


# ---------- 3: parser uploads use the capped reader ----------


def test_parser_uploads_read_through_the_cap(client, auth_headers, db_session, monkeypatch):
    import app.routers.data_parsers as router
    from models.analysis import Analysis

    calls = []
    original = router.read_upload_capped

    def spy(file, **kwargs):
        calls.append(kwargs.get("max_bytes"))
        return original(file, **kwargs)

    monkeypatch.setattr(router, "read_upload_capped", spy)
    monkeypatch.setattr(router, "MAX_SETUP_FILE_BYTES", 16)
    config = {
        "schema_version": "1",
        "delimiter": ",",
        "skip_rows": 0,
        "header_row": 0,
        "columns": [{"source_col": "Well", "field_name": "well_position", "data_type": "string"}],
        "well_col": "Well",
    }

    small = b"Well\nA1\n"
    ok = client.post(
        "/v1/data-parsers/test",
        headers=auth_headers,
        data={"parser_config": json.dumps(config)},
        files=[("files", ("ok.csv", io.BytesIO(small), "text/csv"))],
    )
    assert ok.status_code == 200, ok.text
    big = b"Well\n" + b"A1\n" * 20
    over = client.post(
        "/v1/data-parsers/test",
        headers=auth_headers,
        data={"parser_config": json.dumps(config)},
        files=[("files", ("big.csv", io.BytesIO(big), "text/csv"))],
    )
    assert over.status_code == 413, over.text
    assert over.json()["detail"]["code"] == "upload_too_large"

    kind = client.post("/v1/instrument-types", headers=auth_headers, json={"name": f"T-{uuid.uuid4().hex[:6]}"})
    instrument = client.post(
        "/v1/instruments",
        headers=auth_headers,
        json={"name": f"I-{uuid.uuid4().hex[:6]}", "instrument_type_id": kind.json()["id"]},
    )
    analysis = Analysis(name=f"A-{uuid.uuid4().hex[:6]}", method="EPA", active=True)
    db_session.add(analysis)
    db_session.commit()
    parser = client.post(
        "/v1/data-parsers",
        headers=auth_headers,
        json={
            "name": f"P-{uuid.uuid4().hex[:6]}",
            "instrument_id": instrument.json()["id"],
            "parser_config": config,
            "analyses": [{"analysis_id": str(analysis.id), "is_default": True}],
            "activate": True,
        },
    )
    assert parser.status_code == 201, parser.text
    parser_id = parser.json()["id"]
    stored = client.post(
        f"/v1/data-parsers/{parser_id}/setup-files",
        headers=auth_headers,
        data={"role": "example"},
        files={"file": ("ok.csv", io.BytesIO(small), "text/csv")},
    )
    assert stored.status_code == 201, stored.text
    too_big = client.post(
        f"/v1/data-parsers/{parser_id}/setup-files",
        headers=auth_headers,
        data={"role": "example"},
        files={"file": ("big.csv", io.BytesIO(big), "text/csv")},
    )
    assert too_big.status_code == 413, too_big.text
    assert too_big.json()["detail"]["code"] == "upload_too_large"
    assert calls == [16, 16, 16, 16]


# ---------- 2: 0108 volume pre-check ----------


def _migration(name: str):
    spec = importlib.util.spec_from_file_location(f"_t_{name}", VERSIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _CountConn:
    def __init__(self, count: int):
        self.count = count
        self.sql: list[str] = []

    def execute(self, statement, params=None):
        self.sql.append(str(statement))
        count = self.count

        class _Result:
            def scalar(self_inner):
                return count

        return _Result()


def test_0108_stops_with_a_count_when_volumes_exceed_the_cap():
    m = _migration("0108_elisa_followups")
    conn = _CountConn(3)
    with pytest.raises(RuntimeError) as raised:
        m._assert_volumes_within_cap(conn)
    message = str(raised.value)
    assert "3 sample row(s)" in message
    assert "volume_ul above 10000000" in message
    assert "No rows were changed or deleted" in message
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in conn.sql)
    m._assert_volumes_within_cap(_CountConn(0))
    source = (VERSIONS / "0108_elisa_followups.py").read_text()
    assert source.index("_assert_volumes_within_cap(op.get_bind())") < source.index(
        "op.create_check_constraint("
    )


def test_0108_pre_check_passes_on_the_migrated_database(migrated_engine):
    m = _migration("0108_elisa_followups")
    with migrated_engine.connect() as conn:
        m._assert_volumes_within_cap(conn)


# ---------- 8: no DELETE on the reagent tables ----------


def test_0109_revokes_delete_and_grants_nothing():
    source = (VERSIONS / "0109_revoke_reagent_delete.py").read_text()
    assert "GRANT" not in source
    assert "op.drop_" not in source
    assert not re.search(r"\bDROP\s+(TABLE|COLUMN|SCHEMA|INDEX|POLICY|CONSTRAINT)\b", source, re.I)
    m = _migration("0109_revoke_reagent_delete")
    assert m.down_revision == "0108_elisa_followups"
    assert set(m.REAGENT_TABLES) == set(REAGENT_TABLES)


def test_lims_app_has_no_delete_on_reagent_tables(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            for table in REAGENT_TABLES:
                assert conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, 'DELETE')"),
                    {"t": f"public.{table}"},
                ).scalar() is False, table
                for priv in ("SELECT", "INSERT", "UPDATE"):
                    assert conn.execute(
                        text("SELECT has_table_privilege('lims_app', :t, :p)"),
                        {"t": f"public.{table}", "p": priv},
                    ).scalar() is True, (table, priv)
            conn.execute(text("SET ROLE lims_app"))
            for table in REAGENT_TABLES:
                nested = conn.begin_nested()
                with pytest.raises(ProgrammingError):
                    conn.execute(text(f"DELETE FROM {table} WHERE false"))
                nested.rollback()
        finally:
            conn.execute(text("RESET ROLE"))
            tx.rollback()


def test_alembic_has_one_head_and_short_revision_ids():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(VERSIONS.parents[2] / "alembic.ini"))
    cfg.set_main_option("script_location", str(VERSIONS.parent))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0116_e2_review_fixes"]
    for rev in script.walk_revisions():
        assert len(rev.revision) <= 32, rev.revision


# ---------- 5: cross-client visibility as lims_app ----------


def _entry(conn, list_id: str, name: str):
    return conn.execute(
        text("SELECT id FROM list_entries WHERE list_id = :l AND name = :n"),
        {"l": list_id, "n": name},
    ).scalar_one()


def _client_world(conn, lab_role, sample_type, sample_status, project_status, pw):
    tag = uuid.uuid4().hex[:6]
    ids = {k: uuid.uuid4() for k in ("client", "user", "project", "sample", "analyte", "run", "data", "accept")}
    conn.execute(
        text("INSERT INTO clients (id, name, active, billing_info) VALUES (:id, :n, true, '{}')"),
        {"id": ids["client"], "n": f"C-{tag}"},
    )
    conn.execute(
        text(
            "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
            "VALUES (:id, :n, :u, :e, :pw, :r, :c, true)"
        ),
        {
            "id": ids["user"], "n": f"Tech {tag}", "u": f"tech-{tag}", "e": f"{tag}@x.org",
            "pw": pw, "r": lab_role, "c": ids["client"],
        },
    )
    conn.execute(
        text(
            "INSERT INTO projects (id, name, client_id, status, start_date, active, created_by, modified_by) "
            "VALUES (:id, :n, :c, :s, CURRENT_DATE, true, :u, :u)"
        ),
        {"id": ids["project"], "n": f"P-{tag}", "c": ids["client"], "s": project_status, "u": ids["user"]},
    )
    conn.execute(
        text("INSERT INTO project_users (project_id, user_id) VALUES (:p, :u)"),
        {"p": ids["project"], "u": ids["user"]},
    )
    conn.execute(
        text(
            "INSERT INTO samples (id, name, sample_type, status, project_id, volume_ul, active, created_by, modified_by) "
            "VALUES (:id, :n, :t, :s, :p, 250, true, :u, :u)"
        ),
        {
            "id": ids["sample"], "n": f"S-{tag}", "t": sample_type, "s": sample_status,
            "p": ids["project"], "u": ids["user"],
        },
    )
    conn.execute(
        text("INSERT INTO analytes (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
        {"id": ids["analyte"], "n": f"IL6-{tag}", "u": ids["user"]},
    )
    conn.execute(
        text("INSERT INTO lims_runs (id, name, status, created_by) VALUES (:id, :n, 'running', :u)"),
        {"id": ids["run"], "n": f"Run-{tag}", "u": ids["user"]},
    )
    conn.execute(
        text(
            "INSERT INTO lims_run_data (id, lims_run_id, sample_id, sample_key, row_data, created_by) "
            "VALUES (:id, :r, :s, :k, '{}', :u)"
        ),
        {"id": ids["data"], "r": ids["run"], "s": ids["sample"], "k": f"K-{tag}", "u": ids["user"]},
    )
    conn.execute(
        text(
            "INSERT INTO result_acceptances (id, sample_id, analyte_id, replicate, accepted_lims_run_id, "
            "accepted_value, reason, created_by) VALUES (:id, :s, :a, 1, :r, '1.0', 'kept', :u)"
        ),
        {"id": ids["accept"], "s": ids["sample"], "a": ids["analyte"], "r": ids["run"], "u": ids["user"]},
    )
    return ids


def test_cross_client_visibility_as_lims_app(migrated_engine):
    conn = migrated_engine.connect()
    tx = conn.begin()
    try:
        lab = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        sample_type = _entry(conn, "55555555-5555-5555-5555-555555555555", "Blood")
        sample_status = _entry(conn, "11111111-1111-1111-1111-111111111111", "Received")
        project_status = _entry(conn, "33333333-3333-3333-3333-333333333333", "Active")
        pw = get_password_hash("x")
        a = _client_world(conn, lab, sample_type, sample_status, project_status, pw)
        b = _client_world(conn, lab, sample_type, sample_status, project_status, pw)

        conn.execute(
            text("GRANT SELECT ON samples, users, lims_runs, lims_run_data, result_acceptances TO lims_app")
        )
        conn.execute(text("SET ROLE lims_app"))
        flags = conn.execute(
            text("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
        assert tuple(flags) == ("lims_app", False, False)

        checks = (
            ("lims_runs", "run"),
            ("lims_run_data", "data"),
            ("samples", "sample"),
            ("result_acceptances", "accept"),
        )

        def visible(user_id, table, ids):
            conn.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_id)}
            )
            return set(
                conn.execute(
                    text(f"SELECT id FROM {table} WHERE id = ANY(CAST(:ids AS uuid[]))"),
                    {"ids": [str(i) for i in ids]},
                ).scalars()
            )

        for table, key in checks:
            both = [a[key], b[key]]
            assert visible(a["user"], table, both) == {a[key]}, table
            assert visible(b["user"], table, both) == {b[key]}, table
            assert visible(uuid.UUID(int=0), table, both) == set(), table
    finally:
        tx.rollback()
        conn.execute(text("RESET ROLE"))
        conn.close()
