"""Schema invariants for P0 atomic-receive datasets.

Uses migrated_engine so Alembic 0058/0060 seed is present.
Does not call POST /api/samples/receive (this pack does not implement receive).
"""
import inspect

import pytest
from sqlalchemy.orm import sessionmaker

from models.result import Result
from tests.fixtures.atomic_receive import (
    ALICE,
    BOB,
    CAROL,
    MAB_PROJECT,
    CART_PROJECT,
    IGG,
    CELL_COUNT,
    AVAILABLE,
    ASSIGNED_PENDING,
    LOD,
    ND,
    NBIO_BARCODES,
    load_payloads,
    project_by_name,
    project_ids_for,
    analyte_by_name,
    user_by_username,
    list_entry,
    result_has_no_unit_id,
)
import tests.test_atomic_receive_p0_invariants as this_mod


def _scenarios(data: dict) -> dict:
    return data["scenarios"] if "scenarios" in data else data


def _hv_bodies(hv: dict) -> list:
    if "requests" in hv:
        return [row["body"] for row in hv["requests"] if "body" in row]
    return [row["body"] for row in hv["receives"]]


def _res01_body(res: dict) -> dict:
    if "requests" in res:
        return res["requests"][0]["body"]
    return res["body"]


@pytest.fixture
def migrated_session(migrated_engine):
    Session = sessionmaker(bind=migrated_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_alice_and_bob_do_not_share_projects(migrated_session):
    alice = project_ids_for(migrated_session, ALICE)
    bob = project_ids_for(migrated_session, BOB)
    assert alice, "alice-tech must have project access from 0058"
    assert bob, "bob-tech must have project access from 0058"
    assert alice.isdisjoint(bob)

    mab = project_by_name(migrated_session, MAB_PROJECT).id
    cart = project_by_name(migrated_session, CART_PROJECT).id
    assert mab in alice and mab not in bob
    assert cart in bob and cart not in alice


def test_reviewer_is_not_enterer(migrated_session):
    assert user_by_username(migrated_session, ALICE).id != user_by_username(
        migrated_session, CAROL
    ).id


def test_igg_has_units_default_cell_count_does_not(migrated_session):
    igg = analyte_by_name(migrated_session, IGG)
    cell = analyte_by_name(migrated_session, CELL_COUNT)
    assert igg.units_default is not None
    assert cell.units_default is None


def test_available_for_testing_status_exists(migrated_session):
    list_entry(migrated_session, "Sample Status", AVAILABLE)


def test_assigned_pending_and_qualifiers_exist(migrated_session):
    list_entry(migrated_session, "Test Status", ASSIGNED_PENDING)
    list_entry(migrated_session, "Result Qualifiers", LOD)
    list_entry(migrated_session, "Result Qualifiers", ND)


def test_result_persist_lock_has_no_unit_id():
    assert result_has_no_unit_id()
    assert hasattr(Result, "reported_result")
    assert hasattr(Result, "raw_result")
    assert hasattr(Result, "qualifiers")


def test_hv_payloads_have_unique_barcodes_and_no_sample_name():
    hv = _scenarios(load_payloads())["AR-HV-01"]
    bodies = _hv_bodies(hv)
    barcodes = [b["container_barcode"] for b in bodies]
    assert barcodes == NBIO_BARCODES
    assert len(barcodes) == 24
    assert len(set(barcodes)) == 24
    forbidden = {"name", "sample_name", "lab_id", "status", "container_type_id", "unit_id"}
    for body in bodies:
        assert forbidden.isdisjoint(body.keys())
        assert "parent_sample_id" not in body


def test_res01_payload_copies_raw_to_reported_without_unit_id():
    body = _res01_body(_scenarios(load_payloads())["AR-RES-01"])
    assert body["reported_result"] == body["raw_result"] == "<0.05"
    assert body["qualifiers"] == LOD
    assert "unit_id" not in body


def test_canonical_p0_ids_include_keyboard_validation_and_rbac():
    data = _scenarios(load_payloads())
    for sid in ("AR-HV-05", "AR-VAL-01", "AR-RBAC-01"):
        assert sid in data
    kb = data["AR-HV-05"]["requests"][0]["body"]
    assert kb["container_barcode"] == "NBIO-AR-KB-0001"
    assert kb["container_barcode"] not in NBIO_BARCODES
    missing = data["AR-VAL-01"]["requests"][0]["body"]
    assert "container_barcode" not in missing
    assert data["AR-VAL-01"]["expected_status_code"] == 422
    assert data["AR-RBAC-01"]["actor"] == "david-cro"
    assert data["AR-RBAC-01"]["expected_status_code"] == 403
    assert data["AR-MU-02"].get("p0_must_pass") is False


def test_no_receive_api_assertion_in_this_module():
    source = inspect.getsource(this_mod)
    assert "TestClient" not in source
    assert "from fastapi.testclient" not in source
    assert "migrated_engine" in source
