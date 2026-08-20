"""
Pytest fixtures for accessing seeded BioTech/Pharma test data.

These fixtures provide easy access to the comprehensive test dataset
seeded by migrations 0058 and 0059. The seed data includes clients,
users, projects, samples, tests, results, and batches for realistic
BioTech/Pharma scenarios.

Usage:
    from tests.fixtures.seed_data_fixtures import alice_user, mab_pk_sample

    def test_sample_access(db_session, alice_user, mab_pk_sample):
        # alice_user is a Lab Technician with access to mAb PK project
        # mab_pk_sample is a plasma PK sample with ELISA results
        assert mab_pk_sample.name == "mAb-2301-PK-T0"
        assert mab_pk_sample.created_by == alice_user.id

Note: These fixtures assume migrations 0058 and 0059 have been applied.
If using testcontainers with Base.metadata.create_all() (not Alembic),
you'll need to manually seed the data or use the migrated_engine fixture
from conftest.py.
"""
import pytest
from sqlalchemy.orm import Session
from models.user import User
from models.client import Client
from models.project import Project
from models.sample import Sample
from models.container import Container, ContainerType
from models.test import Test
from models.analysis import Analysis, Analyte
from models.batch import Batch
from models.result import Result


# ============================================================================
# Client Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def novabio_client(db_session: Session) -> Client:
    """NovaBio Therapeutics client (internal biotech company)."""
    return db_session.query(Client).filter(
        Client.id == "client-biotech-001"
    ).first()


@pytest.fixture(scope="function")
def pharmatest_cro_client(db_session: Session) -> Client:
    """PharmaTest CRO client (contract research organization)."""
    return db_session.query(Client).filter(
        Client.id == "client-cro-002"
    ).first()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def alice_user(db_session: Session) -> User:
    """Alice Chen - Lab Technician at NovaBio (mAb PK project access)."""
    return db_session.query(User).filter(User.username == "alice-tech").first()


@pytest.fixture(scope="function")
def bob_user(db_session: Session) -> User:
    """Bob Martinez - Lab Technician at NovaBio (CAR-T project access)."""
    return db_session.query(User).filter(User.username == "bob-tech").first()


@pytest.fixture(scope="function")
def carol_manager(db_session: Session) -> User:
    """Carol Davidson - Lab Manager at NovaBio (all projects access)."""
    return db_session.query(User).filter(User.username == "carol-manager").first()


@pytest.fixture(scope="function")
def david_cro_client(db_session: Session) -> User:
    """David Lee - Client user at PharmaTest CRO (read-only CRO project access)."""
    return db_session.query(User).filter(User.username == "david-cro").first()


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_pk_project(db_session: Session) -> Project:
    """mAb-2301 PK Study project (NovaBio)."""
    return db_session.query(Project).filter(
        Project.id == "proj-mab-pk-001"
    ).first()


@pytest.fixture(scope="function")
def cart_project(db_session: Session) -> Project:
    """CAR-T In-Process Testing project (NovaBio)."""
    return db_session.query(Project).filter(
        Project.id == "proj-cell-therapy-002"
    ).first()


@pytest.fixture(scope="function")
def plasmid_project(db_session: Session) -> Project:
    """Plasmid Lot Release Testing project (NovaBio)."""
    return db_session.query(Project).filter(
        Project.id == "proj-plasmid-003"
    ).first()


@pytest.fixture(scope="function")
def cro_sponsor_project(db_session: Session) -> Project:
    """Sponsor XYZ - Bioanalytical Services project (PharmaTest CRO)."""
    return db_session.query(Project).filter(
        Project.id == "proj-cro-sponsor-004"
    ).first()


@pytest.fixture(scope="function")
def project_alpha_legacy(db_session: Session) -> Project:
    """Project Alpha (legacy backward-compat alias for mAb PK)."""
    return db_session.query(Project).filter(
        Project.id == "proj-alpha-legacy"
    ).first()


@pytest.fixture(scope="function")
def project_beta_legacy(db_session: Session) -> Project:
    """Project Beta (legacy backward-compat alias for CAR-T, used for RLS tests)."""
    return db_session.query(Project).filter(
        Project.id == "proj-beta-legacy"
    ).first()


# ============================================================================
# Sample Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_pk_t0_sample(db_session: Session) -> Sample:
    """mAb PK T0 sample (Testing Complete status, has ELISA results, depleted parent)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-mab-pk-t0"
    ).first()


@pytest.fixture(scope="function")
def mab_pk_t1_sample(db_session: Session) -> Sample:
    """mAb PK T1 sample (Available for Testing status, test in analysis)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-mab-pk-t1"
    ).first()


@pytest.fixture(scope="function")
def mab_pk_t2_sample(db_session: Session) -> Sample:
    """mAb PK T2 sample (Received status, test just ordered)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-mab-pk-t2"
    ).first()


@pytest.fixture(scope="function")
def mab_pk_t0_aliquot(db_session: Session) -> Sample:
    """Aliquot from mAb PK T0 (child sample, parent_sample_id set)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-mab-pk-t0-aliquot"
    ).first()


@pytest.fixture(scope="function")
def cart_batch_sample(db_session: Session) -> Sample:
    """CAR-T Batch 001 sample (Available for Testing, viability test in analysis)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-cart-batch1"
    ).first()


@pytest.fixture(scope="function")
def cart_blank_qc_sample(db_session: Session) -> Sample:
    """CAR-T Blank QC sample (QC type: Blank, viability test complete with zero results)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-cart-blank"
    ).first()


@pytest.fixture(scope="function")
def plasmid_lot_sample(db_session: Session) -> Sample:
    """Plasmid Lot 2025-001 sample (Reviewed status, qPCR test complete and reviewed)."""
    return db_session.query(Sample).filter(
        Sample.id == "sample-plasmid-lot1"
    ).first()


# ============================================================================
# Container Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def cryovial_container_type(db_session: Session) -> ContainerType:
    """Cryovial (2mL) container type."""
    return db_session.query(ContainerType).filter(
        ContainerType.id == "ctype-001-cryovial"
    ).first()


@pytest.fixture(scope="function")
def plate96_container_type(db_session: Session) -> ContainerType:
    """96-Well Plate container type."""
    return db_session.query(ContainerType).filter(
        ContainerType.id == "ctype-004-plate96"
    ).first()


@pytest.fixture(scope="function")
def mab_pk_t0_container(db_session: Session) -> Container:
    """Container for mAb PK T0 sample (cryovial with depleted volume: 50 µL)."""
    return db_session.query(Container).filter(
        Container.id == "cont-mab-pk-t0"
    ).first()


# ============================================================================
# Analysis Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def elisa_analysis(db_session: Session) -> Analysis:
    """ELISA (Human IgG) analysis."""
    return db_session.query(Analysis).filter(
        Analysis.id == "analysis-elisa-001"
    ).first()


@pytest.fixture(scope="function")
def qpcr_analysis(db_session: Session) -> Analysis:
    """qPCR (Plasmid Copy Number) analysis."""
    return db_session.query(Analysis).filter(
        Analysis.id == "analysis-qpcr-001"
    ).first()


@pytest.fixture(scope="function")
def viability_analysis(db_session: Session) -> Analysis:
    """Cell Viability (Trypan Blue) analysis."""
    return db_session.query(Analysis).filter(
        Analysis.id == "analysis-viability-001"
    ).first()


# ============================================================================
# Analyte Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def igg_concentration_analyte(db_session: Session) -> Analyte:
    """IgG Concentration analyte (for ELISA)."""
    return db_session.query(Analyte).filter(
        Analyte.id == "analyte-igg-conc"
    ).first()


@pytest.fixture(scope="function")
def viability_percent_analyte(db_session: Session) -> Analyte:
    """Viability (%) analyte (for cell viability assay)."""
    return db_session.query(Analyte).filter(
        Analyte.id == "analyte-viability"
    ).first()


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_pk_t0_elisa_test(db_session: Session) -> Test:
    """ELISA test for mAb PK T0 sample (Complete status, has results)."""
    return db_session.query(Test).filter(
        Test.id == "test-mab-pk-t0-elisa"
    ).first()


@pytest.fixture(scope="function")
def mab_pk_t1_elisa_test(db_session: Session) -> Test:
    """ELISA test for mAb PK T1 sample (In Analysis status, no results yet)."""
    return db_session.query(Test).filter(
        Test.id == "test-mab-pk-t1-elisa"
    ).first()


@pytest.fixture(scope="function")
def cart_viability_test(db_session: Session) -> Test:
    """Viability test for CAR-T Batch 001 (In Analysis status)."""
    return db_session.query(Test).filter(
        Test.id == "test-cart-viability"
    ).first()


@pytest.fixture(scope="function")
def cart_blank_viability_test(db_session: Session) -> Test:
    """Viability test for CAR-T Blank QC (Complete status, zero results)."""
    return db_session.query(Test).filter(
        Test.id == "test-cart-blank-viability"
    ).first()


# ============================================================================
# Result Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_pk_t0_igg_result(db_session: Session) -> Result:
    """IgG concentration result for mAb PK T0 ELISA test (5.2 µg/mL)."""
    return db_session.query(Result).filter(
        Result.test_id == "test-mab-pk-t0-elisa",
        Result.analyte_id == "analyte-igg-conc"
    ).first()


# ============================================================================
# Batch Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_elisa_batch(db_session: Session) -> Batch:
    """mAb ELISA Batch (In Process status, 3 samples: T0, T1, T2)."""
    return db_session.query(Batch).filter(
        Batch.id == "batch-mab-elisa-001"
    ).first()


@pytest.fixture(scope="function")
def cart_qc_batch(db_session: Session) -> Batch:
    """CAR-T QC Batch (Completed status, 2 samples: Batch-001 + Blank QC)."""
    return db_session.query(Batch).filter(
        Batch.id == "batch-cart-qc-001"
    ).first()


# ============================================================================
# Composite Scenario Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mab_pk_full_scenario(db_session: Session, alice_user, mab_pk_project, 
                         mab_pk_t0_sample, mab_pk_t1_sample, mab_pk_t2_sample,
                         mab_pk_t0_elisa_test, mab_elisa_batch):
    """
    Full mAb PK study scenario: project, samples, tests, batch.
    
    Returns dict with:
    - user: alice_user (Lab Technician)
    - project: mAb-2301 PK Study
    - samples: [T0, T1, T2]
    - t0_sample: Testing Complete (has results)
    - t1_sample: Available for Testing (test in analysis)
    - t2_sample: Received (test just ordered)
    - t0_test: ELISA test (Complete)
    - batch: mAb ELISA Batch (In Process)
    """
    return {
        'user': alice_user,
        'project': mab_pk_project,
        'samples': [mab_pk_t0_sample, mab_pk_t1_sample, mab_pk_t2_sample],
        't0_sample': mab_pk_t0_sample,
        't1_sample': mab_pk_t1_sample,
        't2_sample': mab_pk_t2_sample,
        't0_test': mab_pk_t0_elisa_test,
        'batch': mab_elisa_batch,
    }


@pytest.fixture(scope="function")
def cart_qc_scenario(db_session: Session, bob_user, cart_project,
                     cart_batch_sample, cart_blank_qc_sample,
                     cart_viability_test, cart_blank_viability_test,
                     cart_qc_batch):
    """
    CAR-T In-Process QC scenario: project, samples (regular + QC blank), tests, batch.
    
    Returns dict with:
    - user: bob_user (Lab Technician)
    - project: CAR-T In-Process Testing
    - batch_sample: CAR-T Batch 001 (regular sample)
    - blank_sample: CAR-T Blank QC (QC type: Blank)
    - batch_test: Viability test for batch (In Analysis)
    - blank_test: Viability test for blank (Complete, zero results)
    - batch: CAR-T QC Batch (Completed)
    """
    return {
        'user': bob_user,
        'project': cart_project,
        'batch_sample': cart_batch_sample,
        'blank_sample': cart_blank_qc_sample,
        'batch_test': cart_viability_test,
        'blank_test': cart_blank_viability_test,
        'batch': cart_qc_batch,
    }


@pytest.fixture(scope="function")
def multi_user_rbac_scenario(db_session: Session, alice_user, bob_user, 
                              carol_manager, david_cro_client,
                              mab_pk_project, cart_project, cro_sponsor_project):
    """
    Multi-user RBAC scenario: 4 users with different roles and project access.
    
    Returns dict with:
    - alice: Lab Tech (mAb PK project only)
    - bob: Lab Tech (CAR-T project only)
    - carol: Lab Manager (all NovaBio projects)
    - david: Client (CRO project only, read-only)
    - mab_pk_project: mAb-2301 PK Study
    - cart_project: CAR-T In-Process Testing
    - cro_project: Sponsor XYZ - Bioanalytical Services
    """
    return {
        'alice': alice_user,
        'bob': bob_user,
        'carol': carol_manager,
        'david': david_cro_client,
        'mab_pk_project': mab_pk_project,
        'cart_project': cart_project,
        'cro_project': cro_sponsor_project,
    }
