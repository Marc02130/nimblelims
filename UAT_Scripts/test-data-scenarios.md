# NimbleLIMS Test Data Scenarios Catalog

## Overview

This document catalogs the comprehensive BioTech/Pharma test dataset and multi-user scenarios seeded by migrations `0058` and `0059`. The dataset covers the full sample lifecycle from accessioning through results review, with realistic edge cases and multi-user RBAC/RLS scenarios.

**Data Source**: Seeded by Alembic migrations (idempotent, safe to re-run)
- `0058_biotech_comprehensive_seed.py`: Clients, users, projects, analyses, container types, units
- `0059_biotech_sample_lifecycle_data.py`: Samples, containers, tests, results, batches

**Loading**: Automatically applied when database migrations run. To reload:
```bash
# In Docker environment
sudo docker exec lims-backend python run_migrations.py

# Or via alembic directly
cd backend && alembic upgrade head
```

---

## Table of Contents

1. [Clients and Organizations](#clients-and-organizations)
2. [Users and Roles](#users-and-roles)
3. [Projects](#projects)
4. [Sample Types and Matrices](#sample-types-and-matrices)
5. [Analyses and Test Batteries](#analyses-and-test-batteries)
6. [Sample Lifecycle Scenarios](#sample-lifecycle-scenarios)
7. [Multi-User RBAC Scenarios](#multi-user-rbac-scenarios)
8. [Edge Cases](#edge-cases)
9. [Backward Compatibility](#backward-compatibility)

---

## Clients and Organizations

### 1. NovaBio Therapeutics (`client-biotech-001`)
- **Type**: Internal biotech company
- **Focus**: Oncology monoclonal antibody development
- **Abbreviation**: NBIO
- **Location**: South San Francisco, CA

### 2. PharmaTest CRO (`client-cro-002`)
- **Type**: Contract Research Organization
- **Focus**: Outsourced analytical services
- **Abbreviation**: PTCRO
- **Location**: Cambridge, MA

**RLS Isolation**: These two clients are fully isolated. Users from one client cannot see projects, samples, or data from the other client (except Administrators with global access).

---

## Users and Roles

### Existing Users (from earlier migrations)
| Username | Password | Role | Client | Notes |
|----------|----------|------|--------|-------|
| `admin` | `admin123` | Administrator | System | Global access, no RLS restrictions |
| `lab-tech` | `labtech123` | Lab Technician | NovaBio | Access to Project Alpha and mAb PK |
| `lab-manager` | `labmanager123` | Lab Manager | NovaBio | Access to all NovaBio projects |
| `client` | `client123` | Client | UAT Test Client | Legacy test client (from earlier migrations) |

### New Users (from migration 0058)
| Username | Password | Role | Client | Projects | Notes |
|----------|----------|------|--------|----------|-------|
| `alice-tech` | `alice123` | Lab Technician | NovaBio | mAb PK, Project Alpha | Can accession, aliquot, order tests |
| `bob-tech` | `bob123` | Lab Technician | NovaBio | CAR-T, Project Beta | Cannot see Alice's projects (RLS) |
| `carol-manager` | `carol123` | Lab Manager | NovaBio | All NovaBio projects | Can review results across all projects |
| `david-cro` | `david123` | Client | PharmaTest CRO | CRO Sponsor project only | Read-only access to CRO samples |

**Key Permissions**:
- **Lab Technician**: `sample:create`, `sample:read`, `test:assign`, `test:update`, `result:enter`, `batch:read`
- **Lab Manager**: All tech permissions + `result:review`, `sample:update`, `batch:manage`, `project:manage`
- **Client**: `sample:read`, `result:read`, `project:read` (read-only, own client data only)
- **Administrator**: All permissions, global access

---

## Projects

### 1. mAb-2301 PK Study (`proj-mab-pk-001`)
- **Client**: NovaBio Therapeutics
- **Description**: Pharmacokinetic study for anti-PD-1 monoclonal antibody in mouse xenograft model
- **Samples**: Plasma PK samples at multiple timepoints (T0, T1, T2)
- **Analyses**: ELISA (Human IgG quantification)
- **Users**: alice-tech, carol-manager, lab-tech, lab-manager, admin
- **Status**: Active

### 2. CAR-T In-Process Testing (`proj-cell-therapy-002`)
- **Client**: NovaBio Therapeutics
- **Description**: In-process QC for CAR-T cell therapy manufacturing (Phase I clinical trial)
- **Samples**: CAR-T batches, QC blanks
- **Analyses**: Cell viability (trypan blue), identity (sequencing), sterility (endotoxin)
- **Users**: bob-tech, carol-manager, lab-manager, admin
- **Status**: Active

### 3. Plasmid Lot Release Testing (`proj-plasmid-003`)
- **Client**: NovaBio Therapeutics
- **Description**: GMP-grade plasmid DNA production lot release testing
- **Samples**: Plasmid DNA preps
- **Analyses**: qPCR (copy number), identity (Sanger sequencing), purity (A260/280), endotoxin
- **Users**: alice-tech, carol-manager, lab-manager, admin
- **Status**: Active

### 4. Sponsor XYZ - Bioanalytical Services (`proj-cro-sponsor-004`)
- **Client**: PharmaTest CRO
- **Description**: Outsourced bioanalytical testing for external sponsor
- **Analyses**: ELISA, qPCR, HPLC
- **Users**: david-cro, admin
- **Status**: Active

### 5. Project Alpha (`proj-alpha-legacy`) — **Backward Compat Alias**
- **Client**: NovaBio Therapeutics
- **Description**: Legacy project name (alias for mAb PK Study) for UAT script backward compatibility
- **Users**: alice-tech, carol-manager, lab-tech, lab-manager, admin

### 6. Project Beta (`proj-beta-legacy`) — **Backward Compat Alias**
- **Client**: NovaBio Therapeutics
- **Description**: Legacy project name (alias for CAR-T) for UAT RLS testing (inaccessible project scenario)
- **Users**: bob-tech, carol-manager, lab-manager, admin
- **Note**: alice-tech and lab-tech do NOT have access (for RLS negative test)

---

## Sample Types and Matrices

### BioTech/Pharma Sample Types
- Plasma, Serum, Whole Blood, PBMC
- Tissue, Cell Line, Primary Cells
- Plasmid DNA, Protein, Antibody
- Drug Product, API, Excipient
- Reference Standard, QC Sample
- **Legacy**: Blood, Urine, Tissue, Water (from earlier migrations)

### BioTech/Pharma Matrices
- Plasma (K2EDTA), Plasma (Heparin), Serum
- Whole Blood, PBMC, Tissue Homogenate
- Cell Supernatant, Cell Lysate, Purified Protein
- Antibody Solution, Plasmid DNA, Genomic DNA, Total RNA
- Lyophilized Powder, Formulation Buffer
- Urine, CSF
- **Legacy (backward compat)**: Soil (legacy), Sludge (legacy), Ground Water (legacy)

### Container Types
- **Cryovial (2mL)**: Standard cryogenic storage
- **15mL Conical Tube**: Cell culture, plasma storage
- **50mL Conical Tube**: Larger volume samples
- **96-Well Plate**: High-throughput assays
- **384-Well Plate**: Ultra-high-throughput screening
- **Microcentrifuge Tube (1.5mL)**: DNA, small volume aliquots
- **Serum Collection Tube (10mL)**: Blood collection with clot activator
- **K2EDTA Tube (5mL)**: Blood collection with anticoagulant

### Units
- **Concentration**: ng/µL, µg/mL, mg/mL, pg/mL
- **Molar**: nM, µM, mM
- **Volume**: µL, mL
- **Mass**: ng, µg, mg
- **Special**: EU/mL (endotoxin), copies/µL (DNA copy number)

---

## Analyses and Test Batteries

### BioTech/Pharma Analyses

#### 1. ELISA (Human IgG) (`analysis-elisa-001`)
- **Description**: Sandwich ELISA for human IgG quantification in plasma/serum
- **Method**: Plate-based immunoassay, TMB substrate, 450nm absorbance
- **Turnaround**: 2 days
- **Cost**: $75
- **Analytes**: IgG Concentration (µg/mL), range 0-10,000

#### 2. qPCR (Plasmid Copy Number) (`analysis-qpcr-001`)
- **Description**: Quantitative PCR for plasmid DNA copy number determination
- **Method**: TaqMan probe-based qPCR, CFX96 instrument
- **Turnaround**: 1 day
- **Cost**: $50
- **Analytes**: 
  - Plasmid Copy Number (copies/µL), range ≥0
  - A260/A280 Ratio, range 1.7-2.2 (purity check)

#### 3. HPLC (Purity/Identity) (`analysis-hplc-001`)
- **Description**: Reverse-phase HPLC for mAb/protein purity and identity
- **Method**: C18 column, UV 280nm, gradient elution
- **Turnaround**: 3 days
- **Cost**: $120
- **Analytes**: Purity (%), range 0-100

#### 4. Endotoxin (LAL) (`analysis-endotoxin-001`)
- **Description**: Limulus Amebocyte Lysate assay for endotoxin quantification
- **Method**: Kinetic chromogenic LAL, plate reader
- **Turnaround**: 1 day
- **Cost**: $45
- **Analytes**: Endotoxin Level (EU/mL), range 0-10

#### 5. Cell Viability (Trypan Blue) (`analysis-viability-001`)
- **Description**: Manual cell count with trypan blue exclusion
- **Method**: Hemocytometer or automated cell counter
- **Turnaround**: 1 day (must test immediately)
- **Cost**: $25
- **Analytes**: 
  - Viability (%), range 0-100
  - Total Cell Count (cells/mL), range ≥0

#### 6. Identity (Sanger Sequencing) (`analysis-identity-seq-001`)
- **Description**: Sanger sequencing for plasmid/gene identity confirmation
- **Method**: Bi-directional Sanger sequencing, BLAST alignment
- **Turnaround**: 5 days
- **Cost**: $150
- **Analytes**: Identity Result (text: Pass/Fail)

#### 7. EPA Method 8080 (`analysis-epa-8080-legacy`) — **Backward Compat**
- **Description**: Legacy environmental analysis for UAT script backward compatibility
- **Method**: GC/ECD for organochlorine pesticides
- **Turnaround**: 7 days
- **Cost**: $200

### Test Batteries

#### CAR-T In-Process QC Panel (`battery-cart-qc-001`)
- **Description**: Standard in-process QC panel for CAR-T manufacturing
- **Sequence**:
  1. Cell Viability (Trypan Blue) — required
  2. Identity (Sanger Sequencing) — required
  3. Endotoxin (LAL) — required
- **Use Case**: Assign entire battery during accessioning to automatically create 3 sequenced tests

#### ADME Panel (`battery-adme-001`) — from migration 0027
- **Description**: ADME profiling panel for drug discovery (from earlier migration)
- **Analyses**: Clearance, Permeability, Solubility, Plasma Protein Binding

---

## Sample Lifecycle Scenarios

### Scenario 1: mAb PK Study - Full Lifecycle

**Objective**: Exercise the complete sample workflow from accessioning through results review.

**Sample Set**: mAb-2301 PK timepoints (T0, T1, T2)

| Sample | Status | Container | Tests | Results | Notes |
|--------|--------|-----------|-------|---------|-------|
| `mAb-2301-PK-T0` | Testing Complete | Cryovial | ELISA (Complete) | IgG: 5.2 µg/mL | Results entered, awaiting review |
| `mAb-2301-PK-T1` | Available for Testing | Cryovial | ELISA (In Analysis) | None yet | Test in progress |
| `mAb-2301-PK-T2` | Received | Cryovial | ELISA (In Process) | None | Just accessioned, test ordered |

**User**: alice-tech (Lab Technician)

**Workflow**:
1. **Accessioning**: Alice accessioned T0, T1, T2 samples with ELISA analysis assigned
2. **Testing**: Alice ran ELISA for T0, entered results → status now "Testing Complete"
3. **In Progress**: T1 test is in analysis (awaiting results), T2 just ordered
4. **Review**: carol-manager can review T0 results and approve → status becomes "Reviewed"

**Test Coverage**:
- ✓ Accessioning with test assignment
- ✓ Status progression (Received → Available → Testing Complete)
- ✓ Results entry
- ✓ Results review workflow

---

### Scenario 2: Aliquot Creation with Depleted Parent

**Objective**: Test parent/child relationships and edge case for depleted parent sample.

**Sample**: `mAb-2301-PK-T0` (parent) → `mAb-2301-PK-T0-Aliq` (aliquot)

| Sample | Relationship | Remaining Volume | Status |
|--------|--------------|------------------|--------|
| `mAb-2301-PK-T0` | Parent | **50 µL** (depleted!) | Testing Complete |
| `mAb-2301-PK-T0-Aliq` | Aliquot | 100 µL | Available for Testing |

**Edge Case**: Parent sample has only 50 µL remaining (out of original 500 µL). This is below typical test volume requirements (~100-200 µL for ELISA). Demonstrates:
- Parent/child FK relationship (`parent_sample_id`)
- Low/zero remaining volume handling
- Aliquot inherits project, sample type, matrix from parent

**User**: alice-tech

**Workflow**:
1. Alice accessioned T0 parent sample (500 µL initial volume)
2. After ELISA test consumed ~450 µL, parent now has 50 µL remaining
3. Alice created aliquot (100 µL) from parent for repeat testing
4. Aliquot is available for testing, parent is depleted

**Test Coverage**:
- ✓ Parent/child relationship
- ✓ Aliquot creation workflow
- ✓ Depleted parent edge case
- ✓ Property inheritance (project, type, matrix)

---

### Scenario 3: CAR-T In-Process QC with Test Battery

**Objective**: Test battery assignment and QC sample handling.

**Samples**:
- `CAR-T-Batch-001` (regular sample, qc_type: Sample)
- `CAR-T-Blank-QC` (QC blank, qc_type: Blank)

**Battery**: CAR-T In-Process QC Panel (3 tests in sequence)

| Sample | QC Type | Tests | Results | Notes |
|--------|---------|-------|---------|-------|
| `CAR-T-Batch-001` | Sample | Viability (In Analysis) | None yet | Battery assigned → 3 tests created |
| `CAR-T-Blank-QC` | **Blank** | Viability (Complete) | Viability: 0%, Cells: 0 | QC blank, results entered |

**User**: bob-tech

**Workflow**:
1. Bob accessioned CAR-T batch + QC blank
2. Bob assigned CAR-T QC Panel battery → 3 tests auto-created in sequence
3. Bob ran viability assay for both samples
4. QC blank results: 0% viability (expected for blank)
5. Batch includes QC sample → flagged in batch view

**Test Coverage**:
- ✓ Test battery assignment
- ✓ Multiple tests created in sequence order
- ✓ QC sample flagging (qc_type field)
- ✓ QC sample display in batch view (warning indicators)

---

### Scenario 4: Plasmid Lot Release - Reviewed Sample

**Objective**: Test fully reviewed and released sample (end of lifecycle).

**Sample**: `Plasmid-Lot-2025-001`

| Sample | Status | Tests | Results | Review Date | Notes |
|--------|--------|-------|---------|-------------|-------|
| `Plasmid-Lot-2025-001` | **Reviewed** | qPCR (Complete) | 2.45e8 copies/µL | 1 week ago | GMP lot release, fully approved |

**User**: alice-tech (testing), carol-manager (review)

**Workflow**:
1. Alice accessioned plasmid sample, assigned qPCR + identity tests
2. Alice ran qPCR, entered results
3. Test marked complete, sample status → "Testing Complete"
4. carol-manager reviewed results, approved → sample status → "Reviewed"
5. Lot released for manufacturing

**Test Coverage**:
- ✓ Full lifecycle (Received → Testing Complete → Reviewed)
- ✓ Results review by manager
- ✓ GMP-critical testing scenario
- ✓ End state: sample fully released

---

### Scenario 5: Batches with QC Samples

**Objective**: Test batch creation with QC sample integration.

**Batches**:

#### Batch 1: mAb ELISA Batch (`batch-mab-elisa-001`)
- **Status**: In Process
- **Samples**: mAb-2301-PK-T0, T1, T2 (all regular samples)
- **Containers**: 3 cryovials
- **User**: alice-tech
- **Notes**: No QC samples in this batch

#### Batch 2: CAR-T QC Batch (`batch-cart-qc-001`)
- **Status**: Completed
- **Samples**: CAR-T-Batch-001 (Sample), CAR-T-Blank-QC (**Blank**)
- **Containers**: 2 (1 regular + 1 QC blank)
- **User**: bob-tech
- **Notes**: Contains QC blank → batch view shows QC indicator

**Test Coverage**:
- ✓ Batch creation and status management
- ✓ Multiple samples in batch
- ✓ QC sample flagging in batch view
- ✓ Batch status progression (Created → In Process → Completed)

---

## Multi-User RBAC Scenarios

### Scenario M1: Lab Tech Accessions and Aliquots (Alice)

**User**: alice-tech (Lab Technician, NovaBio)  
**Projects**: mAb PK, Project Alpha

**Steps**:
1. Alice logs in → sees only mAb PK and Project Alpha in project dropdown (RLS filtering)
2. Alice accessions `mAb-2301-PK-T0` sample → assigns ELISA test
3. After accessioning, Alice creates aliquot `mAb-2301-PK-T0-Aliq`
4. Alice enters ELISA results for T0 → test status becomes "Complete"

**Test Coverage**:
- ✓ Lab tech permissions (sample:create, test:assign, result:enter)
- ✓ RLS: Alice only sees her projects
- ✓ Aliquot creation workflow
- ✓ Results entry workflow

---

### Scenario M2: Lab Manager Reviews Results (Carol)

**User**: carol-manager (Lab Manager, NovaBio)  
**Projects**: All NovaBio projects (mAb PK, CAR-T, Plasmid, Alpha, Beta)

**Steps**:
1. Carol logs in → sees all NovaBio projects (broader RLS access than Alice/Bob)
2. Carol navigates to mAb-2301-PK-T0 sample (created by Alice)
3. Carol reviews ELISA results (5.2 µg/mL)
4. Carol approves results → test review_date set, sample status → "Reviewed"
5. Carol can also review Bob's CAR-T samples

**Test Coverage**:
- ✓ Lab manager permissions (result:review, sample:update)
- ✓ RLS: Manager sees all projects within their client
- ✓ Cross-user visibility (Carol sees Alice's and Bob's samples)
- ✓ Results review workflow

---

### Scenario M3: CRO Partner Read-Only Access (David)

**User**: david-cro (Client role, PharmaTest CRO)  
**Projects**: CRO Sponsor project only

**Steps**:
1. David logs in → sees only "Sponsor XYZ - Bioanalytical Services" project
2. David cannot see any NovaBio projects (RLS client isolation)
3. David views samples and results for CRO project (read-only)
4. David attempts to create/edit sample → **403 Forbidden** (no write permissions)

**Test Coverage**:
- ✓ Client role permissions (read-only: sample:read, result:read, project:read)
- ✓ RLS client isolation (david-cro cannot see NovaBio data)
- ✓ Permission denial for write operations

---

### Scenario M4: Two Techs, Two Projects Isolation (Alice vs Bob)

**Users**: alice-tech, bob-tech (both Lab Technicians, NovaBio)  
**Isolation**: Project-level RLS

| User | Projects | Can Access | Cannot Access |
|------|----------|------------|---------------|
| alice-tech | mAb PK, Project Alpha | mAb-2301 samples, Project Alpha samples | CAR-T samples, Project Beta samples |
| bob-tech | CAR-T, Project Beta | CAR-T samples, Project Beta samples | mAb-2301 samples, Project Alpha samples |

**Steps**:
1. Alice logs in → project dropdown shows only mAb PK and Project Alpha
2. Alice navigates to samples list → sees only mAb PK samples (T0, T1, T2)
3. Bob logs in → project dropdown shows only CAR-T and Project Beta
4. Bob navigates to samples list → sees only CAR-T samples (Batch-001, Blank-QC)
5. Alice attempts to access CAR-T project directly (via URL manipulation) → **403 Forbidden**
6. Bob attempts to access mAb PK sample → **403 Forbidden**

**Test Coverage**:
- ✓ Project-level RLS isolation between techs
- ✓ UI filtering (project dropdowns, sample lists)
- ✓ API enforcement (403 errors for unauthorized project access)
- ✓ project_users junction table wiring

---

### Scenario M5: Admin Global Access

**User**: admin (Administrator)  
**Projects**: All projects (no RLS restrictions)

**Steps**:
1. Admin logs in → sees all projects across all clients (NovaBio + PharmaTest CRO)
2. Admin can view/edit samples from any project
3. Admin can manage users, roles, permissions, configuration

**Test Coverage**:
- ✓ Administrator role bypasses RLS
- ✓ Global visibility across clients and projects
- ✓ Administrative permissions (user:manage, config:edit)

---

## Edge Cases

### Edge Case 1: Depleted Parent Sample

**Sample**: `mAb-2301-PK-T0`  
**Issue**: Only 50 µL remaining (out of original 500 µL)

**Implications**:
- Below typical test volume requirements (~100-200 µL for ELISA)
- Parent cannot be used for further testing without additional aliquots
- Demonstrates low-volume handling
- Aliquot created to preserve remaining parent material

**Test Coverage**:
- ✓ Low/zero remaining volume edge case
- ✓ Parent/child relationship with depleted parent
- ✓ Volume tracking via Contents junction table

---

### Edge Case 2: QC Blank with Zero Results

**Sample**: `CAR-T-Blank-QC`  
**QC Type**: Blank

**Results**:
- Viability: 0%
- Cell Count: 0 cells/mL

**Implications**:
- Expected results for a blank (no cells present)
- QC sample flagged in batch view with warning indicator
- Demonstrates QC integration and handling of zero/null values

**Test Coverage**:
- ✓ QC sample types (qc_type field)
- ✓ Zero/null result values
- ✓ QC flagging in UI (batch view, results table)

---

### Edge Case 3: Missing Optional Fields

**Samples**: Multiple samples have optional fields left NULL:
- `description`: NULL (allowed)
- `client_sample_id`: NULL (no external ID provided)
- `custom_attributes`: `{}` (empty JSON, no custom fields)

**Test Coverage**:
- ✓ Optional field handling
- ✓ NULL vs empty string vs empty JSON
- ✓ Schema flexibility

---

### Edge Case 4: Incomplete Test (No Results)

**Tests**: `test-mab-pk-t1-elisa`, `test-mab-pk-t2-elisa`

**Status**: In Analysis / In Process (no results entered yet)

**Implications**:
- Tests ordered but not complete
- Batch remains "In Process" until all tests complete
- Sample status cannot advance to "Testing Complete" until results entered

**Test Coverage**:
- ✓ Incomplete test handling
- ✓ Batch completion logic (waits for all tests)
- ✓ Status workflow gatekeeping

---

### Edge Case 5: Reviewed Sample with Historical Data

**Sample**: `Plasmid-Lot-2025-001`  
**Review Date**: 1 week ago

**Implications**:
- Sample is in final "Reviewed" status
- Historical data for time-series queries
- Demonstrates end state of lifecycle

**Test Coverage**:
- ✓ Reviewed status (end of lifecycle)
- ✓ Historical timestamps (received_date, test_date, review_date)
- ✓ Audit trail (created_by, modified_by)

---

## Backward Compatibility

### UAT Script Compatibility

The seed data maintains backward compatibility with existing UAT scripts by:

1. **Project Aliases**: `Project Alpha` and `Project Beta` exist as aliases for new BioTech projects
   - UAT scripts referencing "Project Alpha" still work
   - "Project Beta" used for RLS negative tests (inaccessible project)

2. **Legacy Analysis**: `EPA Method 8080` analysis preserved for environmental UAT scripts
   - Marked as "legacy" in description
   - Fully functional for backward compat

3. **Legacy Matrices**: Environmental matrices (Soil, Sludge, Ground Water) preserved
   - Marked with "(legacy)" suffix
   - Description notes to use BioTech matrices instead

4. **Existing Users**: Default users (`lab-tech`, `lab-manager`, `client`) still exist
   - Passwords unchanged: `labtech123`, `labmanager123`, `client123`
   - Project access wired to both legacy and new projects

### UAT Script Data Mapping

| UAT Script Element | Legacy Data (Pre-0058) | New Data (Post-0058/0059) | Notes |
|--------------------|------------------------|---------------------------|-------|
| Project Alpha | UAT Test Project | mAb-2301 PK Study | Alias exists, both names work |
| Project Beta | N/A | CAR-T In-Process Testing | Alias exists, used for RLS tests |
| EPA Method 8080 | Existing analysis | Preserved as legacy | Fully functional |
| Soil matrix | Existing | Preserved as "Soil (legacy)" | Both names work |
| Blood sample type | Existing | Preserved | Unchanged |
| Container "Tube (1x1)" | Legacy name | Now "Cryovial (2mL)" | Old UAT scripts may need update |

### Recommended UAT Script Updates

**Option 1**: Keep existing UAT scripts unchanged
- They will continue to work with Project Alpha/Beta aliases
- EPA Method 8080 analysis still exists
- Legacy matrices preserved

**Option 2**: Update UAT scripts to use new BioTech data (recommended)
- Replace "Project Alpha" with "mAb-2301 PK Study" or keep alias
- Replace "EPA Method 8080" with "ELISA (Human IgG)" for realistic scenarios
- Replace "Soil" matrix with "Plasma (K2EDTA)"
- Update container type references

**Files to review for updates**:
- `uat-sample-accessioning.md` (Appendix: Sample Test Data)
- `uat-aliquots-qc.md` (Appendix: Sample Test Data)
- `uat-test-ordering.md` (Appendix: Sample Test Data)
- `uat-results-entry-review.md` (Appendix: Sample Test Data)

---

## Loading Instructions

### Automatic Loading (Default)

The seed data is automatically loaded when running database migrations:

```bash
# Docker environment (recommended)
sudo docker exec lims-backend python run_migrations.py

# Or via Docker Compose (on startup)
sudo docker compose up -d --build
```

### Manual Loading

If you need to manually apply only the new seed migrations:

```bash
# In backend directory
cd backend

# Activate venv (if not using Docker)
source venv/bin/activate

# Run migrations up to 0059
alembic upgrade 0059
```

### Verification

To verify the seed data loaded correctly:

```sql
-- Check clients
SELECT id, name, abbreviation FROM clients WHERE id IN ('client-biotech-001', 'client-cro-002');

-- Check users
SELECT id, username, email FROM users WHERE username IN ('alice-tech', 'bob-tech', 'carol-manager', 'david-cro');

-- Check projects
SELECT id, name, client_id FROM projects WHERE name LIKE '%mAb%' OR name LIKE '%CAR-T%';

-- Check samples
SELECT id, name, status, qc_type FROM samples WHERE name LIKE '%mAb%' OR name LIKE '%CAR-T%';

-- Check tests
SELECT id, name, sample_id, status FROM tests WHERE name LIKE '%mAb%' OR name LIKE '%CAR-T%';

-- Check results
SELECT COUNT(*) as result_count FROM results;

-- Check batches
SELECT id, name, status FROM batches;
```

### Rollback

To rollback the seed data:

```bash
cd backend
alembic downgrade 0057  # Rolls back 0059 and 0058
```

**Warning**: Rollback will delete all seeded data including samples, tests, results, and user accounts. Only use in development/test environments.

---

## Using the Test Data

### For Automated Tests (pytest)

The seed data can be used in pytest fixtures:

```python
# backend/tests/conftest.py
@pytest.fixture(scope="function")
def alice_user(db_session):
    """Get Alice Chen (lab tech) user from seed data."""
    return db_session.query(User).filter(User.username == "alice-tech").first()

@pytest.fixture(scope="function")
def mab_pk_project(db_session):
    """Get mAb PK Study project from seed data."""
    return db_session.query(Project).filter(Project.name == "mAb-2301 PK Study").first()

@pytest.fixture(scope="function")
def mab_pk_t0_sample(db_session):
    """Get mAb PK T0 sample (with results) from seed data."""
    return db_session.query(Sample).filter(Sample.name == "mAb-2301-PK-T0").first()
```

### For Manual UAT

1. **Start services**: `sudo docker compose up -d`
2. **Login** as one of the test users (see table above)
3. **Navigate** to relevant sections based on scenario:
   - Samples: `/samples`
   - Accessioning: `/accessioning`
   - Results: `/results`
   - Batches: `/batches`
4. **Verify** expected data and behaviors per scenario

### For Development

The seed data provides a realistic, populated database for:
- UI development (forms pre-populated, dropdown options realistic)
- API testing (endpoints have data to query)
- Feature demos (realistic data for screenshots/videos)
- Regression testing (consistent baseline dataset)

---

## Summary

The comprehensive BioTech/Pharma test dataset provides:

- **2 clients** with full RLS isolation (NovaBio, PharmaTest CRO)
- **8 users** across 4 roles with varied project access (admin, 3 techs, 2 managers, 2 clients)
- **6 projects** (4 realistic BioTech + 2 legacy aliases for backward compat)
- **BioTech sample types** (Plasma, PBMC, Plasmid, etc.), **matrices**, **container types**, **units**
- **7 analyses** (ELISA, qPCR, HPLC, Endotoxin, Viability, Identity, EPA legacy)
- **2 test batteries** (CAR-T QC Panel, ADME Panel)
- **7 samples** spanning full status workflow (Received → Reviewed)
- **Parent/aliquot chains** with edge cases (depleted parent)
- **6 tests** (complete, in-analysis, in-process)
- **4 results** entered
- **2 batches** (with QC sample)
- **Edge cases**: depleted parent, QC blank, zero results, incomplete tests

All data is idempotent (safe to re-run migrations), realistic for BioTech/Pharma, and backward-compatible with existing UAT scripts.

---

**Last Updated**: 2026-01-20  
**Migrations**: 0058, 0059  
**Maintainer**: NimbleLIMS Development Team
