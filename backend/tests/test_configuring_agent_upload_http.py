"""Configuring-agent document upload end to end: real HTTP route, real DB.

Regression for #168: add_document referenced an undefined `kind` and every
upload returned 500. No test had called the route or add_document.
"""
import io
from uuid import UUID, uuid4

import pytest

from models.configuring_agent import ConfigurationChunk, ConfigurationDocument
from tests.test_sop_parse_uploads import BINARY, _blank_pdf, _text_pdf

PDF_LINE = "Automated DNA Extraction from Whole Blood"
TXT = "Qubit assay\n\nRead each sample in duplicate and report ng/uL."


@pytest.fixture
def auth_headers(client, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def configuration_id(client, auth_headers):
    r = client.post("/v1/configuring-agent/configurations",
                    json={"name": f"Upload {uuid4().hex[:8]}"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _upload(client, headers, cid, name, data, ctype="application/octet-stream"):
    return client.post(f"/v1/configuring-agent/configurations/{cid}/documents",
                       files={"file": (name, io.BytesIO(data), ctype)}, headers=headers)


@pytest.mark.parametrize("name,data,kind,needle", [
    ("sop.pdf", _text_pdf(PDF_LINE), "pdf", PDF_LINE),
    ("notes.txt", TXT.encode(), "txt", "report ng/uL"),
])
def test_upload_stores_file_type_and_text(client, auth_headers, configuration_id, db_session, name, data, kind, needle):
    r = _upload(client, auth_headers, configuration_id, name, data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["file_type"] == kind
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1
    doc = db_session.get(ConfigurationDocument, UUID(body["id"]))
    db_session.refresh(doc)
    assert doc.file_type == kind
    assert needle in doc.content
    assert "%PDF" not in doc.content
    chunks = db_session.query(ConfigurationChunk).filter(ConfigurationChunk.document_id == doc.id).all()
    assert len(chunks) == body["chunk_count"]
    assert any(needle in c.content for c in chunks)


def test_binary_upload_gets_415_and_stores_nothing(client, auth_headers, configuration_id, db_session):
    r = _upload(client, auth_headers, configuration_id, "data.bin", BINARY)
    assert r.status_code == 415
    assert "Unsupported file type" in r.json()["detail"]
    n = db_session.query(ConfigurationDocument).filter(
        ConfigurationDocument.configuration_id == UUID(configuration_id)).count()
    assert n == 0


def test_pdf_without_text_gets_400(client, auth_headers, configuration_id):
    r = _upload(client, auth_headers, configuration_id, "scan.pdf", _blank_pdf())
    assert r.status_code == 400
    assert "no text" in r.json()["detail"]
