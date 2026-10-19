"""Enter Results reads result_qualifiers. The old name qualifiers is not a list."""
from models.list import List, ListEntry


def _login(client):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_result_qualifiers_list_name(client, db_session, test_admin_user):
    row = List(
        name="result_qualifiers",
        description="Result qualifiers",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(row)
    db_session.flush()
    db_session.add(
        ListEntry(
            list_id=row.id,
            name="ND",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
    )
    db_session.commit()
    headers = _login(client)
    found = client.get("/lists/result_qualifiers/entries", headers=headers)
    assert found.status_code == 200, found.text
    names = [entry["name"] for entry in found.json()]
    assert "ND" in names
    missing = client.get("/lists/qualifiers/entries", headers=headers)
    assert missing.status_code == 404, missing.text
