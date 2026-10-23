"""Follow-ups on the merged ELISA run gaps. No plate math."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.security import get_password_hash
from app.schemas.sample import MAX_RECEIPT_VOLUME_UL, SampleReceiveRequest
from tests.conftest import _get_or_create, _grant
from tests.test_elisa_run_gaps import _analysis, _publish, _run, _sample, _template

NOT_ON_RUN = "Not on this run"
DIFFERENT = "Client sample ID and sample name match different samples"
BOTH = "Matched by client sample ID and sample name"


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seat(db, org, perms):
    from models.user import Permission, Role, User

    role = Role(name=f"seat-{uuid.uuid4().hex[:8]}", description="follow-up seat")
    db.add(role)
    db.flush()
    _grant(db, role, [_get_or_create(db, Permission, name, name) for name in perms])
    user = User(
        name=f"Seat {uuid.uuid4().hex[:8]}",
        username=f"seat-{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("pass-word-1"),
        role_id=role.id,
        client_id=org.id,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    return user


def _login(client, username):
    response = client.post(
        "/auth/login", json={"username": username, "password": "pass-word-1"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _running(client, auth_headers, db_session, test_admin_user, test_org, sample_ids):
    sample = sample_ids[0]
    analysis, analyte = _analysis(db_session, test_admin_user)
    template_id = _template(client, auth_headers)
    created = client.post(
        "/v1/lims-runs",
        json={
            "name": f"Plate {uuid.uuid4().hex[:8]}",
            "experiment_template_id": template_id,
            "analysis_id": str(analysis.id),
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    started = client.patch(
        f"/v1/lims-runs/{run_id}/start",
        json={"sample_ids": [str(sid) for sid in sample_ids]},
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text
    return run_id, analysis, analyte, sample


def test_import_binds_only_samples_on_the_run(
    client, auth_headers, db_session, test_admin_user, test_org
):
    on_client = _sample(db_session, test_admin_user, test_org, f"ON-{uuid.uuid4().hex[:6]}")
    both = _sample(db_session, test_admin_user, test_org, f"BOTH-{uuid.uuid4().hex[:6]}")
    both.name = both.client_sample_id
    off = _sample(db_session, test_admin_user, test_org, f"OFF-{uuid.uuid4().hex[:6]}")
    clash_client = _sample(db_session, test_admin_user, test_org, f"CLASH-{uuid.uuid4().hex[:6]}")
    clash_name = _sample(db_session, test_admin_user, test_org, f"OTHER-{uuid.uuid4().hex[:6]}")
    clash_name.name = clash_client.client_sample_id
    db_session.commit()

    run_id, _analysis_row, _analyte, _sample_row = _running(
        client,
        auth_headers,
        db_session,
        test_admin_user,
        test_org,
        [on_client.id, both.id, clash_client.id],
    )
    imported = client.post(
        f"/v1/lims-runs/{run_id}/import",
        json={
            "rows": [
                {"sample_key": on_client.client_sample_id, "well_position": "D3", "row_data": {"corr": "1"}},
                {"sample_key": both.client_sample_id, "well_position": "D4", "row_data": {"corr": "1"}},
                {"sample_key": off.client_sample_id, "well_position": "E1", "row_data": {"corr": "1"}},
                {"sample_key": clash_client.client_sample_id, "well_position": "E2", "row_data": {"corr": "1"}},
            ]
        },
        headers=auth_headers,
    )
    assert imported.status_code == 200, imported.text
    by_well = {row["well_position"]: row for row in imported.json()["rows"]}
    assert by_well["D3"]["sample_id"] == str(on_client.id)
    assert by_well["D3"]["link_note"] is None
    assert by_well["D4"]["sample_id"] == str(both.id)
    assert by_well["D4"]["link_note"] == BOTH
    assert by_well["E1"]["sample_id"] is None
    assert by_well["E1"]["link_note"] == NOT_ON_RUN
    assert by_well["E2"]["sample_id"] is None
    assert by_well["E2"]["link_note"] == DIFFERENT

    listed = client.get(f"/v1/lims-runs/{run_id}/data", headers=auth_headers, params={"size": 20})
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 4


def test_sample_key_longer_than_255_is_422(
    client, auth_headers, db_session, test_admin_user, test_org
):
    sample = _sample(db_session, test_admin_user, test_org, f"KEY-{uuid.uuid4().hex[:6]}")
    run_id = _run(
        client,
        auth_headers,
        _template(client, auth_headers),
        str(_analysis(db_session, test_admin_user)[0].id),
        str(sample.id),
    )
    too_long = "K" * 256
    rejected = client.post(
        f"/v1/lims-runs/{run_id}/import",
        json={"rows": [{"sample_key": too_long, "row_data": {"corr": "1"}}]},
        headers=auth_headers,
    )
    assert rejected.status_code == 422, rejected.text

    instrument_type = client.post(
        "/v1/instrument-types",
        headers=auth_headers,
        json={"name": f"T-{uuid.uuid4().hex[:6]}"},
    )
    assert instrument_type.status_code == 201, instrument_type.text
    instrument = client.post(
        "/v1/instruments",
        headers=auth_headers,
        json={
            "name": f"I-{uuid.uuid4().hex[:6]}",
            "instrument_type_id": instrument_type.json()["id"],
        },
    )
    assert instrument.status_code == 201, instrument.text
    analysis_id = client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers).json()["analysis_id"]
    parser = client.post(
        "/v1/data-parsers",
        headers=auth_headers,
        json={
            "name": f"Long-{uuid.uuid4().hex[:6]}",
            "instrument_id": instrument.json()["id"],
            "parser_config": {
                "schema_version": "1",
                "skip_rows": 0,
                "sample_col": "Sample Name",
                "columns": [
                    {"source_col": "Sample Name", "field_name": "sample_name", "data_type": "string"}
                ],
            },
            "analyses": [{"analysis_id": analysis_id, "is_default": True}],
            "activate": True,
        },
    )
    assert parser.status_code == 201, parser.text
    body = f"Sample Name\n{too_long}\n".encode()
    uploaded = client.post(
        f"/v1/lims-runs/{run_id}/import-file",
        headers=auth_headers,
        data={"parser_id": parser.json()["id"], "instrument_id": instrument.json()["id"]},
        files={"file": ("long.csv", body, "text/csv")},
    )
    assert uploaded.status_code == 422, uploaded.text
    listed = client.get(f"/v1/lims-runs/{run_id}/data", headers=auth_headers)
    assert listed.json()["total"] == 0


def _receive_world(db, user):
    from models.container import ContainerType
    from models.list import List, ListEntry
    from models.project import Project, ProjectUser

    status_list = List(name=f"Sample Status {uuid.uuid4().hex[:6]}", description="t")
    type_list = List(name=f"Sample Type {uuid.uuid4().hex[:6]}", description="t")
    project_status_list = List(name=f"Project Status {uuid.uuid4().hex[:6]}", description="t")
    db.add_all([status_list, type_list, project_status_list])
    db.flush()
    # Receive looks up the list named Sample Status. Point that name at this list
    # only when it is missing; the per-test transaction rolls it back.
    named = db.query(List).filter(List.name == "Sample Status").one_or_none()
    if named is None:
        status_list.name = "Sample Status"
    available = ListEntry(list_id=(named or status_list).id, name=f"Available for Testing {uuid.uuid4().hex[:4]}")
    if db.query(ListEntry).filter(ListEntry.name == "Available for Testing").one_or_none() is None:
        available.name = "Available for Testing"
    sample_type = ListEntry(list_id=type_list.id, name=f"Serum-{uuid.uuid4().hex[:6]}")
    project_active = ListEntry(list_id=project_status_list.id, name=f"Active-{uuid.uuid4().hex[:6]}")
    db.add_all([available, sample_type, project_active])
    tube = ContainerType(
        name=f"Tube-{uuid.uuid4().hex[:6]}", capacity=5, material="plastic", rows=1, columns=1
    )
    db.add(tube)
    db.flush()
    project = Project(
        name=f"AR-{uuid.uuid4().hex[:8]}",
        start_date=datetime.utcnow(),
        client_id=user.client_id,
        status=project_active.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectUser(project_id=project.id, user_id=user.id))
    db.commit()
    return {
        "sample_type": str(sample_type.id),
        "project_id": str(project.id),
        "container_type_id": str(tube.id),
    }


def _receive_body(world, **overrides):
    body = {
        "container_barcode": f"NBIO-{uuid.uuid4().hex[:8]}",
        "sample_type": world["sample_type"],
        "project_id": world["project_id"],
        "container_type_id": world["container_type_id"],
        "client_sample_id": f"IL6-{uuid.uuid4().hex[:6]}",
        "date_sampled": "2026-10-20",
    }
    body.update(overrides)
    return body


def test_receipt_volume_and_thaw_count_are_bounded(client, auth_headers, db_session, test_admin_user):
    world = _receive_world(db_session, test_admin_user)
    base = _receive_body(world)
    with pytest.raises(ValidationError):
        SampleReceiveRequest(
            container_barcode=base["container_barcode"],
            sample_type=base["sample_type"],
            project_id=base["project_id"],
            container_type_id=base["container_type_id"],
            volume_ul=float("nan"),
        )
    with pytest.raises(ValidationError):
        SampleReceiveRequest(
            container_barcode=base["container_barcode"],
            sample_type=base["sample_type"],
            project_id=base["project_id"],
            container_type_id=base["container_type_id"],
            volume_ul=float("inf"),
        )
    ok = client.post(
        "/samples/receive",
        json=_receive_body(world, volume_ul=MAX_RECEIPT_VOLUME_UL, thaw_count=0),
        headers=auth_headers,
    )
    assert ok.status_code == 201, ok.text
    for bad in (
        {"volume_ul": -1},
        {"volume_ul": MAX_RECEIPT_VOLUME_UL + 1},
        {"thaw_count": -1},
    ):
        response = client.post(
            "/samples/receive", json=_receive_body(world, **bad), headers=auth_headers
        )
        assert response.status_code == 422, response.text


def test_value_choices_use_publish_permission(
    client, auth_headers, db_session, test_admin_user, test_org
):
    manager = _seat(db_session, test_org, ["experiment:manage"])
    publisher = _seat(db_session, test_org, ["experiment:publish"])
    sample = _sample(db_session, test_admin_user, test_org, f"PERM-{uuid.uuid4().hex[:6]}")
    run_id = _run(
        client,
        auth_headers,
        _template(client, auth_headers),
        str(_analysis(db_session, test_admin_user)[0].id),
        str(sample.id),
    )
    manage_headers = _login(client, manager.username)
    publish_headers = _login(client, publisher.username)
    listed = client.get(f"/v1/lims-runs/{run_id}/value-choices", headers=manage_headers)
    assert listed.status_code == 403, listed.text
    accepted = client.post(
        f"/v1/lims-runs/{run_id}/value-choices",
        json={
            "sample_id": str(sample.id),
            "analyte_id": str(uuid.uuid4()),
            "accepted_lims_run_id": run_id,
            "reason": "no",
        },
        headers=manage_headers,
    )
    assert accepted.status_code == 403, accepted.text
    seen = client.get(f"/v1/lims-runs/{run_id}/value-choices", headers=publish_headers)
    assert seen.status_code == 200, seen.text
    assert seen.json() == []


def test_accepting_a_failed_run_keeps_entered_by(
    client, auth_headers, db_session, test_admin_user, test_org, test_user
):
    from models.result import Result
    from models.result_acceptance import ResultAcceptance

    sample = _sample(db_session, test_admin_user, test_org, f"FAIL-{uuid.uuid4().hex[:6]}")
    analysis, analyte = _analysis(db_session, test_admin_user)
    template_id = _template(client, auth_headers)
    run_id = _run(client, auth_headers, template_id, str(analysis.id), str(sample.id))
    first = client.post(
        f"/v1/lims-runs/{run_id}/import",
        json={"rows": [{"sample_id": str(sample.id), "row_data": {"corr": "1.10", "replicate": 1}}]},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    rejected = client.post(
        f"/v1/lims-runs/{run_id}/reject",
        json={"reason": "QC-H out of range"},
        headers=auth_headers,
    )
    assert rejected.status_code == 200, rejected.text
    rerun = client.post(f"/v1/lims-runs/{run_id}/rerun", json={}, headers=auth_headers)
    assert rerun.status_code == 201, rerun.text
    rerun_id = rerun.json()["id"]
    started = client.patch(
        f"/v1/lims-runs/{rerun_id}/start",
        json={"sample_ids": [str(sample.id)]},
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text
    second = client.post(
        f"/v1/lims-runs/{rerun_id}/import",
        json={"rows": [{"sample_id": str(sample.id), "row_data": {"corr": "2.20", "replicate": 1}}]},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    published = _publish(client, auth_headers, rerun_id)
    assert published.status_code == 200, published.text

    db_session.expire_all()
    stored = (
        db_session.query(Result)
        .filter(Result.analyte_id == analyte.id, Result.active == True)  # noqa: E712
        .one()
    )
    stored.entered_by = test_user.id
    db_session.commit()

    body = {
        "sample_id": str(sample.id),
        "analyte_id": str(analyte.id),
        "replicate": 1,
        "accepted_lims_run_id": run_id,
        "reason": "Report the rejected plate",
    }
    missing = client.post(
        f"/v1/lims-runs/{rerun_id}/value-choices", json=body, headers=auth_headers
    )
    assert missing.status_code == 422, missing.text
    blank = dict(body, override_failed=True, reason="   ")
    assert client.post(
        f"/v1/lims-runs/{rerun_id}/value-choices", json=blank, headers=auth_headers
    ).status_code == 422

    accepted = client.post(
        f"/v1/lims-runs/{rerun_id}/value-choices",
        json=dict(body, override_failed=True),
        headers=auth_headers,
    )
    assert accepted.status_code == 200, accepted.text
    db_session.expire_all()
    stored = (
        db_session.query(Result)
        .filter(Result.analyte_id == analyte.id, Result.active == True)  # noqa: E712
        .one()
    )
    assert stored.raw_result == "1.10"
    assert stored.entered_by == test_user.id
    pick = (
        db_session.query(ResultAcceptance)
        .filter(ResultAcceptance.sample_id == sample.id, ResultAcceptance.active == True)  # noqa: E712
        .one()
    )
    assert pick.override_failed is True
    assert pick.reason == "Report the rejected plate"
    assert pick.created_by == test_admin_user.id


def test_upload_reads_at_most_cap_plus_one():
    import io

    from fastapi import HTTPException
    from starlette.datastructures import Headers, UploadFile

    from app.core.uploads import read_upload_capped

    class Limited:
        def __init__(self, payload: bytes):
            self.payload = payload
            self.pos = 0
            self.reads: list[int] = []

        def read(self, n=-1):
            self.reads.append(n)
            if n is None or n < 0:
                n = len(self.payload) - self.pos
            chunk = self.payload[self.pos : self.pos + n]
            self.pos += len(chunk)
            return chunk

    cap = 8
    reader = Limited(b"x" * 100)
    upload = UploadFile(filename="big.csv", file=reader, headers=Headers({}))
    with pytest.raises(HTTPException) as raised:
        read_upload_capped(upload, max_bytes=cap)
    assert raised.value.status_code == 413
    assert reader.reads
    assert max(reader.reads) <= cap + 1
    assert all(size is not None and size >= 0 for size in reader.reads)
    assert reader.pos <= cap + 1

    lied = Limited(b"y" * 100)
    small_header = UploadFile(
        filename="big.csv",
        file=lied,
        headers=Headers({"content-length": "4"}),
    )
    with pytest.raises(HTTPException) as raised:
        read_upload_capped(small_header, max_bytes=cap)
    assert raised.value.status_code == 413
    assert lied.pos <= cap + 1

    exact = UploadFile(
        filename="ok.csv",
        file=io.BytesIO(b"z" * cap),
        headers=Headers({}),
    )
    assert read_upload_capped(exact, max_bytes=cap) == b"z" * cap


def test_0108_revokes_delete_and_grants_nothing():
    source = Path(__file__).resolve().parents[1].joinpath(
        "db", "migrations", "versions", "0108_elisa_followups.py"
    ).read_text()
    assert "REVOKE DELETE ON TABLE result_acceptances FROM lims_app" in source
    assert "GRANT" not in source
    assert "DROP TABLE" not in source.upper()


def test_lims_app_cannot_delete_result_acceptances(migrated_engine):
    with migrated_engine.connect() as conn:
        tx = conn.begin()
        try:
            assert (
                conn.execute(
                    text(
                        "SELECT has_table_privilege('lims_app', 'public.result_acceptances', 'DELETE')"
                    )
                ).scalar()
                is False
            )
            for priv in ("SELECT", "INSERT", "UPDATE"):
                assert (
                    conn.execute(
                        text(
                            "SELECT has_table_privilege("
                            "'lims_app', 'public.result_acceptances', :priv)"
                        ),
                        {"priv": priv},
                    ).scalar()
                    is True
                )
            conn.execute(text("SET ROLE lims_app"))
            assert conn.execute(text("SELECT current_user")).scalar() == "lims_app"
            flags = conn.execute(
                text(
                    "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
            assert flags[0] is False
            assert flags[1] is False
            nested = conn.begin_nested()
            with pytest.raises(ProgrammingError):
                conn.execute(text("DELETE FROM result_acceptances"))
            nested.rollback()
        finally:
            conn.execute(text("RESET ROLE"))
            tx.rollback()


def test_result_acceptances_are_project_scoped_for_lims_app(migrated_engine):
    conn = migrated_engine.connect()
    tx = conn.begin()
    try:
        lab = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        sample_type = conn.execute(
            text(
                """
                SELECT id FROM list_entries
                WHERE list_id = '55555555-5555-5555-5555-555555555555' AND name = 'Blood'
                """
            )
        ).scalar_one()
        sample_status = conn.execute(
            text(
                """
                SELECT id FROM list_entries
                WHERE list_id = '11111111-1111-1111-1111-111111111111' AND name = 'Received'
                """
            )
        ).scalar_one()
        project_status = conn.execute(
            text(
                """
                SELECT id FROM list_entries
                WHERE list_id = '33333333-3333-3333-3333-333333333333' AND name = 'Active'
                """
            )
        ).scalar_one()
        client_a, client_b = uuid.uuid4(), uuid.uuid4()
        assigned, unassigned, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        project_id, sample_id = uuid.uuid4(), uuid.uuid4()
        analyte_id, run_id, data_id, accept_id = (uuid.uuid4() for _ in range(4))
        pw = get_password_hash("x")
        conn.execute(
            text(
                "INSERT INTO clients (id, name, active, billing_info) "
                "VALUES (:a, :an, true, '{}'), (:b, :bn, true, '{}')"
            ),
            {
                "a": client_a,
                "an": f"A-{uuid.uuid4().hex[:6]}",
                "b": client_b,
                "bn": f"B-{uuid.uuid4().hex[:6]}",
            },
        )
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, :name, :username, :email, :pw, :role, :client, true)"
            ),
            [
                {
                    "id": assigned,
                    "name": "Assigned",
                    "username": f"as-{uuid.uuid4().hex[:6]}",
                    "email": f"{uuid.uuid4().hex[:6]}@x.org",
                    "pw": pw,
                    "role": lab,
                    "client": client_a,
                },
                {
                    "id": unassigned,
                    "name": "Unassigned",
                    "username": f"un-{uuid.uuid4().hex[:6]}",
                    "email": f"{uuid.uuid4().hex[:6]}@x.org",
                    "pw": pw,
                    "role": lab,
                    "client": client_a,
                },
                {
                    "id": other,
                    "name": "Other",
                    "username": f"ot-{uuid.uuid4().hex[:6]}",
                    "email": f"{uuid.uuid4().hex[:6]}@x.org",
                    "pw": pw,
                    "role": lab,
                    "client": client_b,
                },
            ],
        )
        suffix = uuid.uuid4().hex[:6]
        conn.execute(
            text(
                "INSERT INTO projects (id, name, client_id, status, start_date, active, created_by, modified_by) "
                "VALUES (:id, :name, :client, :status, CURRENT_DATE, true, :user, :user)"
            ),
            {
                "id": project_id,
                "name": f"P-{suffix}",
                "client": client_a,
                "status": project_status,
                "user": assigned,
            },
        )
        conn.execute(
            text("INSERT INTO project_users (project_id, user_id) VALUES (:p, :u)"),
            {"p": project_id, "u": assigned},
        )
        conn.execute(
            text(
                "INSERT INTO samples (id, name, sample_type, status, project_id, volume_ul, active, created_by, modified_by) "
                "VALUES (:id, :name, :sample_type, :status, :project, 500, true, :user, :user)"
            ),
            {
                "id": sample_id,
                "name": f"S-{suffix}",
                "sample_type": sample_type,
                "status": sample_status,
                "project": project_id,
                "user": assigned,
            },
        )
        conn.execute(
            text(
                "INSERT INTO analytes (id, name, active, created_by, modified_by) "
                "VALUES (:id, :name, true, :user, :user)"
            ),
            {"id": analyte_id, "name": f"IL6-{suffix}", "user": assigned},
        )
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by) "
                "VALUES (:id, :name, 'draft', :user)"
            ),
            {"id": run_id, "name": f"Run-{suffix}", "user": assigned},
        )
        conn.execute(
            text(
                "INSERT INTO lims_run_data (id, lims_run_id, sample_id, sample_key, row_data, created_by) "
                "VALUES (:id, :run, :sample, 'IL6-SER-0001', '{}', :user)"
            ),
            {"id": data_id, "run": run_id, "sample": sample_id, "user": assigned},
        )
        conn.execute(
            text(
                "INSERT INTO result_acceptances ("
                "id, sample_id, analyte_id, replicate, accepted_lims_run_id, accepted_value, reason, created_by"
                ") VALUES (:id, :sample, :analyte, 1, :run, '1.10', 'kept', :user)"
            ),
            {
                "id": accept_id,
                "sample": sample_id,
                "analyte": analyte_id,
                "run": run_id,
                "user": assigned,
            },
        )

        conn.execute(
            text(
                "GRANT SELECT ON samples, users, lims_runs, lims_run_data, result_acceptances TO lims_app"
            )
        )
        conn.execute(text("SET ROLE lims_app"))
        assert conn.execute(text("SELECT current_user")).scalar() == "lims_app"
        flags = conn.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
        assert flags[0] is False and flags[1] is False

        def sees(user_id, sql, params):
            conn.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(user_id)},
            )
            return conn.execute(text(sql), params).scalar()

        assert sees(assigned, "SELECT count(*) FROM result_acceptances WHERE id = :i", {"i": accept_id}) == 1
        assert sees(unassigned, "SELECT count(*) FROM result_acceptances WHERE id = :i", {"i": accept_id}) == 0
        assert sees(other, "SELECT count(*) FROM result_acceptances WHERE id = :i", {"i": accept_id}) == 0
        assert float(sees(assigned, "SELECT volume_ul FROM samples WHERE id = :i", {"i": sample_id})) == 500
        assert sees(unassigned, "SELECT count(*) FROM samples WHERE id = :i", {"i": sample_id}) == 0
        assert sees(assigned, "SELECT sample_key FROM lims_run_data WHERE id = :i", {"i": data_id}) == "IL6-SER-0001"
        assert sees(other, "SELECT count(*) FROM lims_run_data WHERE id = :i", {"i": data_id}) == 0
        assert (
            sees(unassigned, "SELECT count(*) FROM lims_run_data WHERE id = :i", {"i": data_id}) == 1
        )
        none = uuid.UUID(int=0)
        assert sees(none, "SELECT count(*) FROM result_acceptances WHERE id = :i", {"i": accept_id}) == 0
    finally:
        tx.rollback()
        conn.execute(text("RESET ROLE"))
        conn.close()
