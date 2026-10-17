"""Explicit JSON null clears a nullable column. A required column refuses it."""
from uuid import uuid4

from models.analysis import Analysis, Analyte, AnalysisAnalyte


def _login(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_explicit_null_clears_turnaround_and_significant_figures(client, db_session, test_admin_user):
    analysis = Analysis(
        name=f"Clear TAT {uuid4().hex[:8]}",
        method="EPA 150.1",
        turnaround_time=4,
        cost=12,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    analyte = Analyte(
        name=f"Clear sig {uuid4().hex[:8]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([analysis, analyte])
    db_session.flush()
    rule = AnalysisAnalyte(
        analysis_id=analysis.id,
        analyte_id=analyte.id,
        significant_figures=2,
        is_required=True,
        low_value=0,
        high_value=14,
    )
    db_session.add(rule)
    db_session.commit()
    headers = _login(client)

    zero = client.patch(
        f"/analyses/{analysis.id}",
        json={"turnaround_time": 0, "cost": 0},
        headers=headers,
    )
    assert zero.status_code == 200, zero.text
    assert zero.json()["turnaround_time"] == 0
    assert float(zero.json()["cost"]) == 0

    cleared = client.patch(
        f"/analyses/{analysis.id}",
        json={"turnaround_time": None},
        headers=headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["turnaround_time"] is None
    assert float(cleared.json()["cost"]) == 0

    omitted = client.patch(
        f"/analyses/{analysis.id}",
        json={"description": "still has cost"},
        headers=headers,
    )
    assert omitted.status_code == 200, omitted.text
    assert omitted.json()["turnaround_time"] is None
    assert float(omitted.json()["cost"]) == 0

    refused = client.patch(
        f"/analyses/{analysis.id}",
        json={"name": None},
        headers=headers,
    )
    assert refused.status_code == 422, refused.text
    assert "name" in refused.text

    figures = client.patch(
        f"/analyses/{analysis.id}/analyte-rules/{analyte.id}",
        json={"significant_figures": 0},
        headers=headers,
    )
    assert figures.status_code == 200, figures.text
    assert figures.json()["significant_figures"] == 0

    cleared_figures = client.patch(
        f"/analyses/{analysis.id}/analyte-rules/{analyte.id}",
        json={"significant_figures": None},
        headers=headers,
    )
    assert cleared_figures.status_code == 200, cleared_figures.text
    assert cleared_figures.json()["significant_figures"] is None
    assert cleared_figures.json()["is_required"] is True

    refused_required = client.patch(
        f"/analyses/{analysis.id}/analyte-rules/{analyte.id}",
        json={"is_required": None},
        headers=headers,
    )
    assert refused_required.status_code == 422, refused_required.text
    assert "is_required" in refused_required.text


def test_container_row_zero_is_rejected(client, db_session, test_admin_user):
    from models.container import Container, ContainerType

    container_type = ContainerType(
        name=f"Tube {uuid4().hex[:6]}",
        rows=1,
        columns=1,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(container_type)
    db_session.flush()
    container = Container(
        name=f"Well {uuid4().hex[:6]}",
        type_id=container_type.id,
        row=1,
        column=1,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(container)
    db_session.commit()
    headers = _login(client)

    refused = client.patch(
        f"/containers/{container.id}",
        json={"row": 0, "column": 0},
        headers=headers,
    )
    assert refused.status_code == 422, refused.text

    cleared = client.patch(
        f"/containers/{container.id}",
        json={"row": None},
        headers=headers,
    )
    assert cleared.status_code == 422, cleared.text
    assert "row" in cleared.text
