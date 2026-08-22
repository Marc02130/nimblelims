"""P2 Med/Low: S7 sample access helper + S15 login lockout."""
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.services.sample_access import require_accessible_sample
from app.services.login_throttle import LoginThrottleService
from models.sample import Sample


class TestS7SampleAccess:
    def test_missing_sample_404(self, db_session):
        with pytest.raises(HTTPException) as ei:
            require_accessible_sample(db_session, uuid4())
        assert ei.value.status_code == 404

    def test_has_project_access_false_404(self, db_session, test_org, test_admin_user):
        from models.list import List, ListEntry
        from models.project import Project
        from datetime import timedelta

        avail = (
            db_session.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        if not avail:
            lst = List(name=f"s7_{uuid4().hex[:6]}")
            db_session.add(lst)
            db_session.flush()
            avail = ListEntry(list_id=lst.id, name="Available for Testing")
            st = ListEntry(list_id=lst.id, name=f"t_{uuid4().hex[:4]}")
            mx = ListEntry(list_id=lst.id, name=f"m_{uuid4().hex[:4]}")
            db_session.add_all([avail, st, mx])
            db_session.flush()
        else:
            st = avail
            mx = avail

        project = Project(
            name=f"S7 {uuid4().hex[:6]}",
            client_id=test_org.id,
            status=avail.id,
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(project)
        db_session.flush()
        sample = Sample(
            name=f"S7S {uuid4().hex[:6]}",
            sample_type=st.id,
            status=avail.id,
            matrix=mx.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(sample)
        db_session.commit()

        # Force has_project_access path to return False via nested execute mock
        real_execute = db_session.execute

        def fake_execute(stmt, params=None, **kwargs):
            sql = str(stmt)
            if "has_project_access" in sql:
                m = MagicMock()
                m.scalar.return_value = False
                return m
            return real_execute(stmt, params, **kwargs)

        db_session.execute = fake_execute  # type: ignore
        try:
            with pytest.raises(HTTPException) as ei:
                require_accessible_sample(db_session, sample.id)
            assert ei.value.status_code == 404
        finally:
            db_session.execute = real_execute  # type: ignore


class TestS15LoginThrottle:
    def test_lockout_after_failures(self, client: TestClient, test_user, monkeypatch):
        monkeypatch.setattr("app.services.login_throttle.LOGIN_MAX_FAILURES", 3)
        monkeypatch.setattr("app.core.config.LOGIN_MAX_FAILURES", 3)
        monkeypatch.setattr("app.services.login_throttle._max_failures", lambda: 3)

        statuses = []
        for _ in range(4):
            r = client.post(
                "/auth/login",
                json={"username": "testuser", "password": "wrong-password"},
            )
            statuses.append(r.status_code)
        assert 429 in statuses, statuses
        assert statuses[-1] == 429
        # Last response should carry lock detail when 429
        locked = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrong-password"},
        )
        assert locked.status_code == 429, locked.text
        assert locked.json()["detail"]["code"] == "login_locked"

        # Even correct password while locked
        still = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )
        assert still.status_code == 429

    def test_success_clears_failures(self, client: TestClient, test_user, monkeypatch):
        monkeypatch.setattr("app.services.login_throttle._max_failures", lambda: 5)

        client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrong"},
        )
        ok = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )
        assert ok.status_code == 200

        # Failures cleared — can fail again without immediate lock
        again = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrong"},
        )
        assert again.status_code == 401
