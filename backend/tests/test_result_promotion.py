"""P3: promote lims_run_data → results on publish."""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def analysis_and_analyte(db_session, test_admin_user):
    from models.analysis import Analysis, Analyte, AnalysisAnalyte, AnalyteAlias
    from models.list import List, ListEntry

    analysis = Analysis(
        name=f"Metals {uuid4().hex[:6]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    lead = Analyte(
        name=f"Lead_{uuid4().hex[:4]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    arsenic = Analyte(
        name=f"Arsenic_{uuid4().hex[:4]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([analysis, lead, arsenic])
    db_session.flush()
    db_session.add(AnalyteAlias(analyte_id=lead.id, alias="Pb_ug_L", created_by=test_admin_user.id))
    db_session.add_all(
        [
            AnalysisAnalyte(analysis_id=analysis.id, analyte_id=lead.id),
            AnalysisAnalyte(analysis_id=analysis.id, analyte_id=arsenic.id),
        ]
    )
    # test_status list
    lst = db_session.query(List).filter(List.name == "test_status").first()
    if not lst:
        lst = List(name="test_status", description="Test status")
        db_session.add(lst)
        db_session.flush()
        db_session.add(ListEntry(list_id=lst.id, name="In Process"))
    elif not db_session.query(ListEntry).filter(ListEntry.list_id == lst.id).first():
        db_session.add(ListEntry(list_id=lst.id, name="In Process"))
    db_session.commit()
    return {
        "analysis_id": str(analysis.id),
        "lead_id": str(lead.id),
        "lead_name": lead.name,
        "arsenic_id": str(arsenic.id),
        "arsenic_name": arsenic.name,
    }


@pytest.fixture
def sample_id(db_session, test_admin_user, test_org):
    from models.sample import Sample
    from models.project import Project
    from models.list import List, ListEntry

    lst = List(name=f"promo_list_{uuid4().hex[:6]}", description="t")
    db_session.add(lst)
    db_session.flush()
    st = ListEntry(list_id=lst.id, name="type")
    status = ListEntry(list_id=lst.id, name="status")
    matrix = ListEntry(list_id=lst.id, name="matrix")
    db_session.add_all([st, status, matrix])
    db_session.flush()
    project = Project(
        name=f"P {uuid4().hex[:6]}",
        client_id=test_org.id,
        status=status.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(project)
    db_session.flush()
    s = Sample(
        name=f"S {uuid4().hex[:6]}",
        sample_type=st.id,
        status=status.id,
        matrix=matrix.id,
        project_id=project.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(s)
    db_session.commit()
    return str(s.id)


@pytest.fixture
def template_id(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl {uuid4().hex[:8]}",
            "template_definition": {
                "experiment_name": "Promo",
                "protocol_steps": ["a"],
                "transfer_steps": [],
                "result_columns": [],
                "mandatory_review_count": 0,
            },
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestResultPromotion:
    def test_preview_and_publish_promotes(
        self,
        client: TestClient,
        auth_headers,
        analysis_and_analyte,
        sample_id,
        template_id,
        db_session,
        test_admin_user,
    ):
        from models.flexible_experiment import InstrumentParser

        # Parser with empty expected columns so arbitrary row_data is allowed
        db_session.add(
            InstrumentParser(
                name=f"parser-{uuid4().hex[:6]}",
                experiment_template_id=template_id,
                parser_config={"columns": [], "skip_rows": 0},
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        # Create run with analysis
        r = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "experiment_template_id": template_id,
                "analysis_id": analysis_and_analyte["analysis_id"],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        # Start (ack not needed — has analysis)
        r = client.patch(f"/v1/lims-runs/{run_id}/start", json={}, headers=auth_headers)
        assert r.status_code == 200, r.text

        # Import data
        r = client.post(
            f"/v1/lims-runs/{run_id}/import",
            json={
                "rows": [
                    {
                        "sample_id": sample_id,
                        "well_position": "A1",
                        "row_data": {
                            "Pb_ug_L": "12.3",
                            analysis_and_analyte["arsenic_name"]: "0.4",
                            "units": "ug/L",
                        },
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text

        # Preview (dry-run; known keys like units are silently ignored, not unresolved)
        r = client.get(f"/v1/lims-runs/{run_id}/promotion/preview", headers=auth_headers)
        assert r.status_code == 200, r.text
        preview = r.json()
        assert preview["will_promote"] is True
        assert preview["create_count"] >= 2
        assert preview["conflict_count"] == 0
        assert "units" not in preview.get("unresolved_columns", [])
        match_vias = {
            i.get("match_via")
            for i in preview.get("items", [])
            if i.get("action") == "create"
        }
        assert "alias" in match_vias  # Pb_ug_L
        assert "name" in match_vias  # arsenic name

        # Complete then publish
        r = client.patch(f"/v1/lims-runs/{run_id}/review", headers=auth_headers)
        assert r.status_code == 200, r.text
        r = client.patch(f"/v1/lims-runs/{run_id}/complete", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "published"

        # Results exist
        r = client.get("/results/", headers=auth_headers, params={"page": 1, "size": 50})
        assert r.status_code == 200, r.text
        results = r.json().get("results") or []
        raws = {x.get("raw_result") for x in results if str(x.get("lims_run_id")) == run_id}
        assert "12.3" in raws, f"expected 12.3 in results for run; got {raws} from {len(results)} rows"
        assert "0.4" in raws

    def test_publish_without_analysis_no_promote(
        self, client: TestClient, auth_headers, template_id
    ):
        r = client.post(
            "/v1/lims-runs",
            json={
                "name": f"RunNA {uuid4().hex[:8]}",
                "experiment_template_id": template_id,
            },
            headers=auth_headers,
        )
        run_id = r.json()["id"]
        r = client.patch(
            f"/v1/lims-runs/{run_id}/start",
            json={"acknowledge_no_analysis": True},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        r = client.patch(f"/v1/lims-runs/{run_id}/review", headers=auth_headers)
        assert r.status_code == 200
        r = client.patch(f"/v1/lims-runs/{run_id}/complete", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    def test_conflict_blocks_publish(
        self,
        client: TestClient,
        auth_headers,
        analysis_and_analyte,
        sample_id,
        template_id,
        db_session,
        test_admin_user,
    ):
        """Manual/other-run result for same (test, analyte, rep) → 409 on publish."""
        from models.flexible_experiment import InstrumentParser
        from models.test import Test
        from models.result import Result
        from models.list import List, ListEntry
        from models.sample import Sample
        from models.analysis import Analysis
        from uuid import UUID

        db_session.add(
            InstrumentParser(
                name=f"parser-{uuid4().hex[:6]}",
                experiment_template_id=template_id,
                parser_config={"columns": [], "skip_rows": 0},
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        # Pre-existing test + result (manual, lims_run_id null)
        lst = db_session.query(List).filter(List.name == "test_status").first()
        status_id = (
            db_session.query(ListEntry)
            .filter(ListEntry.list_id == lst.id)
            .first()
            .id
        )
        sample = db_session.query(Sample).filter(Sample.id == UUID(sample_id)).one()
        analysis = (
            db_session.query(Analysis)
            .filter(Analysis.id == UUID(analysis_and_analyte["analysis_id"]))
            .one()
        )
        test = Test(
            name=f"ManualT_{uuid4().hex[:8]}",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=status_id,
            test_date=datetime.utcnow(),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(test)
        db_session.flush()
        db_session.add(
            Result(
                test_id=test.id,
                analyte_id=UUID(analysis_and_analyte["lead_id"]),
                raw_result="99.0",
                replicate=1,
                lims_run_id=None,
                entry_date=datetime.now(),
                entered_by=test_admin_user.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        r = client.post(
            "/v1/lims-runs",
            json={
                "name": f"RunC {uuid4().hex[:8]}",
                "experiment_template_id": template_id,
                "analysis_id": analysis_and_analyte["analysis_id"],
            },
            headers=auth_headers,
        )
        run_id = r.json()["id"]
        assert client.patch(f"/v1/lims-runs/{run_id}/start", json={}, headers=auth_headers).status_code == 200
        r = client.post(
            f"/v1/lims-runs/{run_id}/import",
            json={
                "rows": [
                    {
                        "sample_id": sample_id,
                        "well_position": "A1",
                        "row_data": {"Pb_ug_L": "12.3"},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text

        preview = client.get(
            f"/v1/lims-runs/{run_id}/promotion/preview", headers=auth_headers
        ).json()
        assert preview["conflict_count"] >= 1

        assert client.patch(f"/v1/lims-runs/{run_id}/review", headers=auth_headers).status_code == 200
        r = client.patch(f"/v1/lims-runs/{run_id}/complete", headers=auth_headers)
        assert r.status_code == 409, r.text
        body = r.json()["detail"]
        assert body.get("code") == "promotion_conflict"
