"""P1 Med/Low: S8 upload caps, S9 validate auth, S13 catalog GET, S14 write-back allowlist."""
import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from models.entry import SAMPLE_WRITE_BACK_COLUMNS, SAMPLE_SYSTEM_FIELDS
from app.core.uploads import MAX_UPLOAD_FILE_BYTES


class TestS14WriteBackAllowlist:
    def test_biotype_and_temperature_not_in_write_back(self):
        assert "specimen_biotype_id" not in SAMPLE_WRITE_BACK_COLUMNS
        assert "temperature" not in SAMPLE_WRITE_BACK_COLUMNS
        assert "specimen_biotype_id" in SAMPLE_SYSTEM_FIELDS
        assert "temperature" in SAMPLE_SYSTEM_FIELDS
        assert "due_date" in SAMPLE_WRITE_BACK_COLUMNS


class TestS8UploadCap:
    def test_read_upload_capped_rejects_oversized(self):
        import asyncio
        from starlette.datastructures import Headers, UploadFile
        from app.core.uploads import read_upload_capped
        from fastapi import HTTPException

        big = b"x" * (MAX_UPLOAD_FILE_BYTES + 1)
        uf = UploadFile(
            filename="big.csv",
            file=io.BytesIO(big),
            headers=Headers({"content-length": str(len(big))}),
        )

        with pytest.raises(HTTPException) as ei:
            asyncio.run(read_upload_capped(uf))
        assert ei.value.status_code == 413
        assert ei.value.detail["code"] == "upload_too_large"


class TestS9ValidateAuth:
    def test_validate_requires_auth(self, client: TestClient):
        r = client.post(
            "/results/validate",
            json={
                "test_id": str(uuid4()),
                "analyte_id": str(uuid4()),
                "raw_result": "1.0",
            },
        )
        assert r.status_code in (401, 403)

    def test_validate_with_admin_ok_or_business_error(
        self, client: TestClient, test_admin_user
    ):
        login = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        r = client.post(
            "/results/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "test_id": str(uuid4()),
                "analyte_id": str(uuid4()),
                "raw_result": "1.0",
            },
        )
        # Auth passed; may be invalid config (200 with is_valid false) or 200
        assert r.status_code == 200, r.text


class TestS13CatalogGet:
    def test_roles_requires_manage_permission(
        self, client: TestClient, test_user
    ):
        login = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        r = client.get("/roles", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_permissions_requires_manage_permission(
        self, client: TestClient, test_user
    ):
        login = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        r = client.get(
            "/permissions", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 403

    def test_admin_can_list_roles(self, client: TestClient, test_admin_user):
        login = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        r = client.get("/roles", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
