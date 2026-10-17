"""Debit returns the remainder, and a held row lock is a 503 rather than a hang."""
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import _engine_kwargs
from app.services.contents_amount import debit_contents_amount
from models.client import Client
from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project
from models.sample import Sample
from models.user import Role, User
from tests.test_aliquots import _tracked_parent


def test_debit_remainder_is_a_decimal(db_session, test_admin_user):
    lab = _tracked_parent(db_session, test_admin_user, label="debit-dec", amount="10")
    source = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
    remaining = debit_contents_amount(db_session, source, Decimal("6"))
    assert type(remaining) is Decimal
    assert remaining == Decimal("4")
    db_session.expire_all()
    stored = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
    assert Decimal(stored.amount) == Decimal("4")


def test_debit_reports_source_busy_when_the_row_is_locked(db_engine):
    """The draw waits on the row lock and returns source_busy instead of hanging."""
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, **_engine_kwargs(url))
    session_factory = sessionmaker(bind=engine, autoflush=False)
    tag = uuid4().hex[:8]
    with session_factory() as session:
        org = Client(name=f"Debit lock {tag}", description="lock", billing_info={})
        role = Role(name=f"debit-lock-{tag}", description="lock")
        session.add_all([org, role])
        session.flush()
        user = User(
            name=f"Debit lock {tag}",
            username=f"debitlock{tag}",
            email=f"debitlock{tag}@example.com",
            password_hash="x",
            role_id=role.id,
            client_id=org.id,
            must_change_password=False,
        )
        session.add(user)
        session.flush()
        # Unique names only. A committed "Available for Testing" collides with
        # later tests: list entry names are unique across every list.
        status_list = List(name=f"debit-status-{tag}", description="status")
        type_list = List(name=f"debit-type-{tag}", description="type")
        session.add_all([status_list, type_list])
        session.flush()
        sample_type = ListEntry(
            name=f"Blood {tag}",
            description="Blood",
            list_id=type_list.id,
        )
        sample_status = ListEntry(
            name=f"Ready {tag}",
            description="Ready",
            list_id=status_list.id,
        )
        matrix = ListEntry(
            name=f"Matrix {tag}",
            description="matrix",
            list_id=type_list.id,
        )
        project_status = ListEntry(
            name=f"Active {tag}",
            description="active",
            list_id=status_list.id,
        )
        session.add_all([sample_type, sample_status, matrix, project_status])
        session.flush()
        project = Project(
            name=f"Debit project {tag}",
            description="lock",
            start_date="2024-01-01",
            client_id=org.id,
            status=project_status.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(project)
        session.flush()
        parent = Sample(
            name=f"Debit sample {tag}",
            description="lock",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=matrix.id,
            project_id=project.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(parent)
        session.flush()
        container_type = ContainerType(
            name=f"Debit tube {tag}",
            description="tube",
            rows=1,
            columns=1,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(container_type)
        session.flush()
        source_container = Container(
            name=f"Debit src {tag}",
            description="source",
            type_id=container_type.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(source_container)
        session.flush()
        session.add(
            Contents(
                container_id=source_container.id,
                sample_id=parent.id,
                amount=Decimal("10"),
            )
        )
        session.commit()
        container_id = source_container.id
        sample_id = parent.id
        cleanup = {
            "sample": sample_id,
            "ctype": container_type.id,
            "project": project.id,
            "org": org.id,
            "user": user.id,
            "role": role.id,
            "lists": [status_list.id, type_list.id],
            "entries": [sample_type.id, sample_status.id, matrix.id, project_status.id],
        }
    holder = engine.connect()
    transaction = holder.begin()
    try:
        holder.execute(
            text(
                "SELECT amount FROM contents "
                "WHERE container_id = :c AND sample_id = :s FOR UPDATE"
            ),
            {"c": container_id, "s": sample_id},
        )
        with session_factory() as session:
            session.execute(text("SET lock_timeout = '300ms'"))
            source = (
                session.query(Contents)
                .filter(
                    Contents.container_id == container_id,
                    Contents.sample_id == sample_id,
                )
                .one()
            )
            with pytest.raises(HTTPException) as caught:
                debit_contents_amount(session, source, Decimal("1"))
        assert caught.value.status_code == 503
        assert caught.value.detail["code"] == "source_busy"
    finally:
        transaction.rollback()
        holder.close()
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM contents WHERE sample_id = :i"),
                {"i": cleanup["sample"]},
            )
            connection.execute(text("DELETE FROM samples WHERE id = :i"), {"i": cleanup["sample"]})
            connection.execute(
                text("DELETE FROM containers WHERE type_id = :i"),
                {"i": cleanup["ctype"]},
            )
            connection.execute(
                text("DELETE FROM container_types WHERE id = :i"),
                {"i": cleanup["ctype"]},
            )
            connection.execute(text("DELETE FROM projects WHERE id = :i"), {"i": cleanup["project"]})
            for entry_id in cleanup["entries"]:
                connection.execute(
                    text("DELETE FROM list_entries WHERE id = :i"),
                    {"i": entry_id},
                )
            for list_id in cleanup["lists"]:
                connection.execute(text("DELETE FROM lists WHERE id = :i"), {"i": list_id})
            connection.execute(text("DELETE FROM users WHERE id = :i"), {"i": cleanup["user"]})
            connection.execute(text("DELETE FROM clients WHERE id = :i"), {"i": cleanup["org"]})
            connection.execute(text("DELETE FROM roles WHERE id = :i"), {"i": cleanup["role"]})
        engine.dispose()
