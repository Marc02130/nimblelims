# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Status:** **Draft — waiting Lab Ops re-walk. Implement gate CLOSED.**  
**Requirements:** (not written; locked packet from CEO)  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

| Today | Gap |
|-------|-----|
| Existing accessioning creates sample + container + tests via `/api/samples/accession` and `/api/samples/bulk-accession` (US-1, US-24) | No **atomicity guarantee** across sample/container/contents/tests — mid-rack failure can orphan |
| Status picker exposed to tech | **System** must set `Received` on accession |
| Barcode scan happy path works; keyboard fallback works | Need **explicit scan-plus-few-fields** ceremony (no long form) |
| Temperature stored on sample | Temperature must become **optional/not required** for receive workflow |

**Why atomic:** A tech scanning a rack of 96 tubes cannot manually recover from partial writes (sample exists, container/tests missing). Single DB transaction guarantees sample, container, contents, and attached tests are created together or not at all.

## 2. Goals / non-goals (technical)

**Goals**

- **Atomic receive endpoint**: one POST creates sample + container + contents + tests in a **single DB transaction**
- **System-set status**: `Received` status applied automatically (tech does not pick status)
- **Barcode happy path**: scan barcode as container name (stored as-is; do not append timestamp suffix — Lab Ops L8 flag)
- **Keyboard fallback**: type container name if scan fails
- **Few fields**: barcode/lab id, optional external id, sample type, project (if required by schema), analysis/tests to attach
- **Optional temperature**: remove any `nullable=False` or validation requiring temperature
- **Tests at accession**: attach tests (analyses) immediately; no wizard
- **Add/remove tests later**: POST/DELETE (or equivalent) tests on an existing sample (no wizard)
- **Results entry**: POST result on a test with raw value, unit, optional qualifier (`<LOD`, `ND`)

**Non-goals (parked features)**

- **ELN / method-matrix execute / aliquot execute** — sample and test models exist; execute/method-matrix stays parked
- **IC50 / dose-response / curve fitting** — not this cycle
- **Parsers / instrument/CRO import** — see [data-parsers-lims-runs.md](data-parsers-lims-runs.md)
- **US-28 batch ceremony** — simple one-off result entry only
- **Manifests / materials / multi-tenant** — not in scope

### 2b. Aliquot lineage readiness (not implementation)

Aliquot lineage (`parent_sample_id`) **may exist** in schema. This sketch does **not** implement aliquot creation workflows. Future aliquot/execute work will add UI and service-level rules for lineage. The receive path will ignore `parent_sample_id` unless a future phase requires marking received samples as aliquots.

## 3. Component diagram

Reuse existing tables; no new receive-specific tables:

```
┌────────────────────┐
│ samples            │  existing (name, sample_type, status, matrix, project_id,
│                    │           temperature NULLABLE, parent_sample_id, etc.)
│                    │  ← system sets status = 'Received' (list entry)
└──────────┬─────────┘
           │ 1:N
           ▼
┌────────────────────┐     ┌────────────────────┐
│ contents (M2M)     │────►│ containers         │  existing (name as barcode)
│  sample_id         │     │                    │
│  container_id      │     └────────────────────┘
└────────────────────┘
           │
           │ tests attached to sample (via tests.sample_id)
           ▼
┌────────────────────┐
│ tests              │  existing (sample_id, analysis_id, status, ...)
└──────────┬─────────┘
           │ 1:N
           ▼
┌────────────────────┐
│ results            │  existing (test_id, analyte_id, raw_result, qualifiers, etc.)
│                    │  (created later via result entry, not at receive time)
└────────────────────┘
```

**Atomic boundary:** `ReceiveService.atomic_receive(...)` wraps sample, container, contents, tests creation in one transaction. Rollback if any insert fails.

## 4. Data model

**No schema changes required** if current `Sample.temperature` is already nullable. If not, migration:

```python
# migrations/versions/NNNN_make_temperature_optional.py
def upgrade():
    op.alter_column('samples', 'temperature',
                    existing_type=sa.Numeric(10, 2),
                    nullable=True)

def downgrade():
    # Optional: backfill nulls with 0 or raise if nulls exist
    op.alter_column('samples', 'temperature',
                    existing_type=sa.Numeric(10, 2),
                    nullable=False)
```

**Reuse existing models:**

- `Sample` (backend/models/sample.py) — no new fields
- `Container` (backend/models/container.py) — `name` stores barcode as-is
- `Contents` (backend/models/container.py) — M2M join
- `Test` (backend/models/test.py) — attach via `sample_id` + `analysis_id`
- `Result` (backend/models/result.py) — created later (not at receive time)

**Status list entry:** "Received" must exist in `list_entries` (list "Sample Status"). If UAT statuses include "Received", reuse; else add via seed or migration.

## 5. Key contracts

### 5.1 Atomic receive endpoint

**POST /api/samples/receive** (new endpoint, distinct from `/api/samples/accession`)

**Request (Pydantic):**

```python
class SampleReceiveRequest(BaseModel):
    container_barcode: str  # scanned or typed
    client_sample_id: Optional[str] = None  # external ID
    sample_type: UUID  # list entry ID
    matrix: UUID  # list entry ID
    project_id: UUID  # required (or auto-create if product decides)
    analysis_ids: List[UUID] = Field(default_factory=list)  # tests to attach
    temperature: Optional[float] = None  # optional
    client_id: Optional[UUID] = None  # if multi-client
    client_project_id: Optional[UUID] = None  # if grouping
    # Open question: other "few fields" (date_sampled, qc_type, etc.)
```

**Response (Pydantic):**

```python
class SampleReceiveResponse(BaseModel):
    sample: SampleResponse  # includes id, name, status="Received"
    container: ContainerResponse
    tests: List[TestResponse]
```

**Service logic:**

```python
class ReceiveService:
    async def atomic_receive(
        self, 
        receive_data: SampleReceiveRequest, 
        user_id: UUID,
        db: AsyncSession
    ) -> SampleReceiveResponse:
        async with db.begin():  # single transaction
            # 1. Get "Received" status list entry
            received_status = await self._get_received_status(db)
            
            # 2. Create sample (system sets status = "Received")
            sample = Sample(
                name=generate_name_for_sample(...),  # or passed in
                sample_type=receive_data.sample_type,
                matrix=receive_data.matrix,
                status=received_status.id,
                project_id=receive_data.project_id,
                temperature=receive_data.temperature,  # nullable
                client_sample_id=receive_data.client_sample_id,
                created_by=user_id,
            )
            db.add(sample)
            await db.flush()  # get sample.id
            
            # 3. Create container (barcode as name, no timestamp suffix)
            container = Container(
                name=receive_data.container_barcode,
                type_id=...,  # default or from request
                created_by=user_id,
            )
            db.add(container)
            await db.flush()
            
            # 4. Create contents (M2M)
            contents = Contents(
                sample_id=sample.id,
                container_id=container.id,
            )
            db.add(contents)
            
            # 5. Create tests (no wizard)
            tests = []
            for analysis_id in receive_data.analysis_ids:
                test = Test(
                    sample_id=sample.id,
                    analysis_id=analysis_id,
                    status=...,  # default test status
                    created_by=user_id,
                )
                db.add(test)
                tests.append(test)
            
            await db.flush()
            # Commit happens at context exit; rollback if any failure
        
        return SampleReceiveResponse(sample=sample, container=container, tests=tests)
```

### 5.2 Add/remove tests later (no wizard)

**POST /api/samples/{sample_id}/tests** (add test)

```python
class TestAddRequest(BaseModel):
    analysis_id: UUID
```

**DELETE /api/samples/{sample_id}/tests/{test_id}** (remove test)

(Or equivalent PATCH/PUT if product prefers bulk add/remove)

### 5.3 Result entry

**POST /api/tests/{test_id}/results** (or `/api/results` with `test_id` in body)

```python
class ResultEntryRequest(BaseModel):
    test_id: UUID
    analyte_id: UUID  # from analysis.analytes
    raw_result: str  # typed number (or text if data_type='text')
    unit_id: Optional[UUID] = None  # from units table
    qualifier: Optional[UUID] = None  # list entry: '<LOD', 'ND', etc.
```

**Response:**

```python
class ResultResponse(BaseModel):
    id: UUID
    test_id: UUID
    analyte_id: UUID
    raw_result: str
    reported_result: Optional[str]
    qualifiers: Optional[UUID]
    entered_by: UUID
    entry_date: datetime
```

Service validates `analyte_id` exists in `analysis.analytes` for `test.analysis_id`. No US-28 batch ceremony; one-off result entry only.

## 6. Runtime flows

### 6.1 Atomic receive (barcode scan happy path)

1. Tech opens receive UI
2. Scan barcode → populate `container_barcode`
3. Select sample type, matrix, project (or auto-create project)
4. Optionally select analyses (tests) from dropdown
5. Submit → **POST /api/samples/receive**
6. Backend: single transaction creates sample (status=`Received`), container (name=barcode), contents, tests
7. UI: redirect to sample detail or show success toast

**Keyboard fallback:** If barcode scanner unavailable, type container name manually (same field).

### 6.2 Add/remove tests from sample (after receive)

1. Navigate to sample detail page
2. Click "Add Test" → select analysis → **POST /api/samples/{sample_id}/tests**
3. Click "Remove Test" (trash icon) → **DELETE /api/samples/{sample_id}/tests/{test_id}**

No wizard; immediate add/remove.

### 6.3 Type a number on a test (result entry)

1. Navigate to test detail page or results grid
2. Enter raw value, select unit, optionally select qualifier (`<LOD`, `ND`)
3. Submit → **POST /api/tests/{test_id}/results**
4. Backend: validate analyte belongs to test's analysis; insert result

## 7. Migration / compatibility

- **Existing UAT samples/tests:** remain unchanged
- **Status picker UI:** hide status field on receive form (system sets `Received`); existing sample edit forms may keep status picker for other workflows (or remove based on RBAC)
- **Temperature validation:** if Pydantic validators currently require `temperature`, remove validation or make optional
- **Bulk accession (US-24):** may coexist or be deprecated in favor of atomic receive; product decides
- **Barcode uniqueness:** existing `Container.name` unique constraint (if any) enforced; duplicate barcode → HTTP 409

## 8. Open technical risks

| Risk | Mitigation |
|------|-----------|
| **Required fields on `Sample` block "few fields" flow** | Audit `Sample` model: if `matrix`, `sample_type`, `project_id` are nullable=False, they are already "few fields". If other columns (e.g., `due_date`, `qc_type`) are not-null, either: (1) make nullable, or (2) add to "few fields" list. **Open question for Heidi/Deiter: which fields beyond barcode/sample_type/matrix/project are required?** |
| **Barcode uniqueness across containers** | If `Container.name` has unique constraint, duplicate scans fail (409). If no constraint, duplicate barcodes allowed but may confuse downstream. **Open question: enforce unique barcodes or allow duplicates with timestamp disambiguation?** |
| **Project auto-creation vs required project_id** | Current bulk accessioning auto-creates projects if `project_id=None`. Atomic receive may follow same pattern or require explicit project. **Open question: require project or auto-create?** |
| **Transaction boundaries with async SQLAlchemy** | Use `async with db.begin()` context manager (SQLAlchemy 2.0 async). Existing codebase may use sync `Session`; audit and refactor service layer to async if needed. |
| **Container type default** | If `container_type_id` is required on `Container`, either: (1) add `container_type_id` to request, or (2) use lab-wide default. **Open question: which container type for receive?** |
| **Test status default** | Tests created at receive must have valid status (list entry). Use existing test status "In Process" or create "Pending" status. **Open question: which test status at receive?** |
| **Result unit default** | If `unit_id` is null, use `analyte.units_default` or require explicit unit selection. **Open question: require unit or default from analyte?** |

**Not inventing field list:** This sketch assumes "few fields" = barcode + sample_type + matrix + project + analyses. If product requires additional fields (date_sampled, qc_type, client_id, client_project_id, description, etc.), add them to `SampleReceiveRequest` schema after Lab Ops re-walk.

## 9. Phase mapping

**P0 (atomic loop):**

- Backend: `/api/samples/receive` endpoint (atomic transaction)
- Backend: `/api/samples/{sample_id}/tests` POST/DELETE (add/remove tests)
- Backend: `/api/tests/{test_id}/results` POST (result entry)
- Frontend: receive form (scan barcode, select sample type/matrix/project/analyses)
- Frontend: sample detail "Add Test" / "Remove Test" buttons
- Frontend: result entry form (raw value, unit, qualifier)
- Migration: make `temperature` nullable (if not already)

**Deferred (not P0):**

- Bulk receive (rack of 96 samples) — may reuse US-24 bulk accessioning or build atomic bulk endpoint later
- Aliquot creation workflows (lineage via `parent_sample_id`) — schema exists but UI/service rules parked
- Method-matrix execute / dose-response / IC50 — models exist but execution parked
- ELN / experiment execute — parked
- Parsers / instrument import — separate packet

**UAT pass gate:** Dogfood → UAT → merge to `main` (production). See [`.docs/development-process/README.md`](../development-process/README.md).

---

**Next step:** Lab Ops re-walk to resolve open questions (required fields, barcode uniqueness, project auto-create, container/test/unit defaults).
