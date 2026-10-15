"""SOP parse uploads share the configuring agent's text extraction (UAT 9d0108f)."""
import io
from unittest.mock import patch

import pytest

from app.services.configuring_agent_extract import NoTextInFile, UnsupportedFileType, file_text

SOP_LINE = "Automated DNA Extraction from Whole Blood"
CSV = b"Well,Sample,Concentration (ng/uL)\nA1,S1,12.5\n"


def _text_pdf(text: str = SOP_LINE) -> bytes:
    """A minimal one-page PDF with real text (Helvetica), built by hand."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


def _blank_pdf() -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.fixture
def auth_headers(client, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


BINARY = bytes(range(256)) * 8  # NULs and invalid UTF-8


# ── shared helper ────────────────────────────────────────────────────────────

def test_pdf_fixture_extracts_text():
    assert SOP_LINE in file_text(_text_pdf(), "sop.pdf")


def test_binary_is_unsupported():
    with pytest.raises(UnsupportedFileType):
        file_text(BINARY, "sop.bin")


def test_pdf_without_text_is_refused():
    with pytest.raises(NoTextInFile, match="no extractable text"):
        file_text(_blank_pdf(), "scan.pdf")


def test_corrupt_pdf_is_unsupported():
    with pytest.raises(UnsupportedFileType):
        file_text(b"%PDF-1.4\n garbage \x00\x01", "bad.pdf")


def test_configuring_agent_uses_the_shared_helper():
    from app.services import configuring_agent_service as svc
    assert svc.file_text is file_text


# ── POST /v1/sop-parse ───────────────────────────────────────────────────────

def _post(client, headers, sop: bytes, sop_name: str, inst: bytes = CSV, inst_name: str = "inst.csv"):
    return client.post(
        "/v1/sop-parse",
        files={"sop_file": (sop_name, io.BytesIO(sop), "application/octet-stream"),
               "instrument_file": (inst_name, io.BytesIO(inst), "text/csv")},
        headers=headers,
    )


def test_pdf_upload_sends_extracted_text_to_the_parse(client, auth_headers):
    with patch("app.services.sop_parse_service.SOPParseService.run_extraction_background") as task:
        r = _post(client, auth_headers, _text_pdf(), "sop.pdf")
    assert r.status_code == 202, r.text
    sent = task.call_args.kwargs["sop_text"]
    assert SOP_LINE in sent
    assert "%PDF" not in sent and "\ufffd" not in sent
    assert task.call_args.kwargs["instrument_text"] == CSV.decode()


def test_txt_upload_still_works(client, auth_headers):
    with patch("app.services.sop_parse_service.SOPParseService.run_extraction_background") as task:
        r = _post(client, auth_headers, SOP_LINE.encode(), "sop.txt")
    assert r.status_code == 202
    assert task.call_args.kwargs["sop_text"] == SOP_LINE


@pytest.mark.parametrize("field", ["sop", "instrument"])
def test_binary_upload_gets_415_and_no_job(client, auth_headers, field):
    with patch("app.services.sop_parse_service.SOPParseService.run_extraction_background") as task, \
         patch("app.services.sop_parse_service.SOPParseService.create_job") as create:
        if field == "sop":
            r = _post(client, auth_headers, BINARY, "sop.bin")
        else:
            r = _post(client, auth_headers, SOP_LINE.encode(), "sop.txt", BINARY, "inst.xlsx")
    assert r.status_code == 415
    assert ("SOP file" if field == "sop" else "Instrument file") in r.json()["detail"]
    task.assert_not_called()
    create.assert_not_called()


def test_pdf_without_text_gets_422_and_no_job(client, auth_headers):
    with patch("app.services.sop_parse_service.SOPParseService.run_extraction_background") as task, \
         patch("app.services.sop_parse_service.SOPParseService.create_job") as create:
        r = _post(client, auth_headers, _blank_pdf(), "scan.pdf")
    assert r.status_code == 422
    assert "no extractable text" in r.json()["detail"]
    task.assert_not_called()
    create.assert_not_called()


# ── DELETE /v1/configuring-agent/settings/key ────────────────────────────────

def test_key_delete_keeps_provider_and_model(client, auth_headers):
    r = client.put("/v1/configuring-agent/settings", json={"provider": "xai", "model": "grok-4.7"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    r = client.put("/v1/configuring-agent/settings/key", json={"api_key": "unit-test-key"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["key_set"] is True
    r = client.delete("/v1/configuring-agent/settings/key", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["key_set"] is False
    assert body["agent_provider"] == "xai"
    assert body["agent_model"] == "grok-4.7"
    again = client.get("/v1/configuring-agent/settings", headers=auth_headers).json()
    assert (again["agent_provider"], again["agent_model"], again["key_set"]) == ("xai", "grok-4.7", False)
