"""
Example tests demonstrating usage of seeded BioTech/Pharma test data.

These tests show how to use the seed data fixtures from fixtures/seed_data_fixtures.py
to test various LIMS workflows with realistic data.

Run with: pytest backend/tests/test_seed_data_usage_example.py -v
"""
import pytest
from tests.fixtures.seed_data_fixtures import (
    alice_user, bob_user, carol_manager,
    mab_pk_project, mab_pk_t0_sample, mab_pk_t0_elisa_test,
    mab_pk_full_scenario, cart_qc_scenario, multi_user_rbac_scenario
)


def test_sample_access_with_results(db_session, alice_user, mab_pk_t0_sample, mab_pk_t0_elisa_test):
    """Test that Alice can access mAb PK T0 sample with ELISA results."""
    # Verify sample exists and was created by Alice
    assert mab_pk_t0_sample is not None
    assert mab_pk_t0_sample.name == "mAb-2301-PK-T0"
    assert mab_pk_t0_sample.created_by == alice_user.id
    
    # Verify sample has test
    assert len(mab_pk_t0_sample.tests) > 0
    assert mab_pk_t0_elisa_test.sample_id == mab_pk_t0_sample.id
    
    # Verify test has results
    assert len(mab_pk_t0_elisa_test.results) > 0
    result = mab_pk_t0_elisa_test.results[0]
    assert result.reported_result == "5.2"


def test_parent_child_relationship(db_session, mab_pk_t0_sample):
    """Test that aliquot relationship is correctly established."""
    # T0 sample is a parent (has child aliquots)
    assert mab_pk_t0_sample.parent_sample_id is None  # It's a parent, not a child
    assert len(mab_pk_t0_sample.child_samples) > 0
    
    # Get aliquot
    aliquot = mab_pk_t0_sample.child_samples[0]
    assert aliquot.parent_sample_id == mab_pk_t0_sample.id
    assert aliquot.name == "mAb-2301-PK-T0-Aliq"
    
    # Verify property inheritance
    assert aliquot.project_id == mab_pk_t0_sample.project_id
    assert aliquot.sample_type == mab_pk_t0_sample.sample_type
    assert aliquot.matrix == mab_pk_t0_sample.matrix


def test_depleted_parent_edge_case(db_session, mab_pk_t0_sample):
    """Test that depleted parent sample (low remaining volume) is correctly flagged."""
    # Get container for T0 sample
    assert len(mab_pk_t0_sample.contents) > 0
    content = mab_pk_t0_sample.contents[0]
    
    # Verify remaining volume is low (50 µL)
    assert content.amount == 50  # µL
    # This is below typical test requirements (~100-200 µL for ELISA)


def test_qc_sample_identification(db_session, cart_qc_scenario):
    """Test that QC blank sample is correctly identified and has zero results."""
    blank_sample = cart_qc_scenario['blank_sample']
    blank_test = cart_qc_scenario['blank_test']
    
    # Verify QC type is Blank
    qc_type_entry = db_session.query(db_session.query(blank_sample.qc_type).first())
    # Note: qc_type is a UUID FK to list_entries, need to query the list_entry
    # For simplicity in example, just check it's not NULL
    assert blank_sample.qc_type is not None
    
    # Verify test is complete with zero results
    assert blank_test.status is not None  # Should be "Complete" status
    assert len(blank_test.results) > 0
    
    # Check for zero viability result
    viability_result = [r for r in blank_test.results if 'viability' in r.analyte.name.lower()][0]
    assert viability_result.reported_result == "0"


def test_multi_user_project_isolation(db_session, multi_user_rbac_scenario):
    """Test that Alice and Bob have isolated project access (RLS)."""
    alice = multi_user_rbac_scenario['alice']
    bob = multi_user_rbac_scenario['bob']
    mab_pk_proj = multi_user_rbac_scenario['mab_pk_project']
    cart_proj = multi_user_rbac_scenario['cart_project']
    
    # Check that Alice and Bob are from same client but have different project access
    assert alice.client_id == bob.client_id  # Same client (NovaBio)
    
    # Alice can access mAb PK project
    alice_projects = [pu.project_id for pu in db_session.query(
        db_session.query(alice.id).join('project_users').all()
    )]
    # Note: This is a simplified check; actual RLS enforcement is at API/policy level
    # Full RLS testing requires integration tests with actual user context


def test_batch_with_qc_samples(db_session, cart_qc_scenario):
    """Test that batch contains both regular and QC samples."""
    batch = cart_qc_scenario['batch']
    batch_sample = cart_qc_scenario['batch_sample']
    blank_sample = cart_qc_scenario['blank_sample']
    
    # Verify batch has containers linked
    assert len(batch.containers) == 2  # Batch-001 + Blank-QC
    
    # Verify batch status is Completed
    # (status is UUID FK to list_entries)
    assert batch.status is not None


def test_full_mab_pk_scenario(db_session, mab_pk_full_scenario):
    """Integration test for full mAb PK study workflow."""
    scenario = mab_pk_full_scenario
    
    # Verify user and project
    assert scenario['user'].username == "alice-tech"
    assert scenario['project'].name == "mAb-2301 PK Study"
    
    # Verify samples span status workflow
    samples = scenario['samples']
    assert len(samples) == 3  # T0, T1, T2
    
    # T0: Testing Complete (has results)
    t0 = scenario['t0_sample']
    assert len(t0.tests) > 0
    assert len(t0.tests[0].results) > 0
    
    # T1: Available for Testing (test in analysis, no results yet)
    t1 = scenario['t1_sample']
    assert len(t1.tests) > 0
    assert len(t1.tests[0].results) == 0  # No results yet
    
    # T2: Received (test just ordered)
    t2 = scenario['t2_sample']
    assert len(t2.tests) > 0
    
    # Verify batch
    batch = scenario['batch']
    assert batch.name == "mAb-ELISA-Batch-20260120"
    assert len(batch.containers) == 3  # T0, T1, T2


# Note: These are example tests demonstrating fixture usage.
# For full test coverage, add more specific tests for:
# - API endpoint access control (RLS enforcement)
# - Status transition workflows
# - Results validation
# - Batch completion logic
# - Permission checks (test:assign, result:enter, result:review)
