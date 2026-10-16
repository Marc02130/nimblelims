"""0091: type-changing 'aliquot' transitions become 'derivative'.

Terminology (Marc): an aliquot keeps the sample and its type in a new
container; a derivative changes the type and creates a child sample.
"""

import importlib.util
import os
import types
from uuid import uuid4

from sqlalchemy import text

from models.list import ListEntry
from models.sample import SampleTypeTransition
from tests._fk_helpers import scratch_list_id

MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "db", "migrations", "versions",
    "0091_derivative_transitions.py",
)


def _module():
    spec = importlib.util.spec_from_file_location("m0091", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _types(db, n):
    rows = [ListEntry(list_id=scratch_list_id(db), name=f"t_{uuid4().hex[:6]}") for _ in range(n)]
    db.add_all(rows)
    db.flush()
    return rows


def _row(db, client_id, source, op, dest, active=True):
    row = SampleTypeTransition(
        client_id=client_id, source_sample_type=source.id, operation=op,
        allowed_dest_sample_type=dest.id, active=active,
    )
    db.add(row)
    db.flush()
    return row


def test_head_has_no_type_changing_aliquot_rows(db_session):
    count = db_session.execute(text(
        "SELECT COUNT(*) FROM sample_type_transitions "
        "WHERE operation = 'aliquot' AND source_sample_type <> allowed_dest_sample_type AND active"
    )).scalar()
    assert count == 0
    ck = db_session.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_sample_type_transitions_operation'"
    )).scalar()
    assert "derivative" in ck


def test_upgrade_converts_legacy_rows_and_retires_twins(db_session, test_org):
    blood, dna, plasma, serum = _types(db_session, 4)
    legacy = _row(db_session, test_org.id, blood, "aliquot", dna)
    same = _row(db_session, test_org.id, serum, "aliquot", serum)
    twin_old = _row(db_session, test_org.id, blood, "aliquot", plasma)
    twin_new = _row(db_session, test_org.id, blood, "derivative", plasma)
    pool = _row(db_session, test_org.id, dna, "pool", plasma)

    module = _module()
    conn = db_session.connection()
    module.op = types.SimpleNamespace(
        get_bind=lambda: conn,
        drop_constraint=lambda *a, **k: None,
        create_check_constraint=lambda *a, **k: None,
    )
    module.upgrade()
    db_session.expire_all()

    assert db_session.get(SampleTypeTransition, legacy.id).operation == "derivative"
    assert db_session.get(SampleTypeTransition, legacy.id).active is True
    assert db_session.get(SampleTypeTransition, same.id).operation == "aliquot"
    old = db_session.get(SampleTypeTransition, twin_old.id)
    assert (old.operation, old.active) == ("aliquot", False)  # retired, not deleted
    assert db_session.get(SampleTypeTransition, twin_new.id).active is True
    assert db_session.get(SampleTypeTransition, pool.id).operation == "pool"
