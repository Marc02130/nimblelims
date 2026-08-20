# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Status:** **Lab Ops Accept with conditions (L1–L4). Implement gate OPEN for Heidi / Hans / CEO reviews. No product code until those pass.**  
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

- **Atomic receive endpoint**: one POST creates sample + container + contents + tests in a **single DB transaction** (locked)
- **System-set status**: system writes status **`Received` then `Available for Testing`** (locked). Drop status from request payload. Techs do not pick status.
- **Barcode unique**: scan writes unique container `name` as-is (locked). No timestamp suffix. Duplicate → HTTP 409.
- **Sample.name = barcode** (L1, locked): `Sample.name` set to scanned barcode (same string as `Container.name`). One identity string. Drop `generate_name_for_sample`.
- **Keyboard fallback**: type container name if scan fails
- **Few fields**: barcode (becomes sample name + container name), optional external id, sample type, matrix, **project (required, sticky)** (L2, locked), optional analysis/tests to attach
- **Optional temperature**: remove any `nullable=False` or validation requiring temperature
- **Container type default** (L3, locked): default tube, **off the form**. Do not ask the tech.
- **Tests at receive**: optional (locked). Add/remove later from sample with no wizard.
- **Test status** (L4, locked): tests created at receive use **assigned/pending** status (not "In Process"). **Refuse DELETE** if test already has results.
- **Results entry**: POST result on a test with raw value, unit (defaults from `analytes.units_default`), optional qualifier (`<LOD`, `ND`) (locked)
- **High-volume scan UX** (locked): after successful receive, **stay on receive screen**. Toast success, **clear barcode**, **keep sticky** sample type/matrix/project, **focus barcode field**. Do not redirect to sample detail. Do not open aliquot dialog.

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
│ samples            │  existing (name = barcode [L1], sample_type, status, matrix,
│                    │           project_id REQUIRED [L2], temperature NULLABLE, etc.)
│                    │  ← system sets status = 'Received' then 'Available for Testing'
└──────────┬─────────┘
           │ 1:N
           ▼
┌────────────────────┐     ┌────────────────────┐
│ contents (M2M)     │────►│ containers         │  existing (name as barcode, same string)
│  sample_id         │     │  type_id = default tube [L3]
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

**Status list entries:** "Received" and "Available for Testing" must exist in `list_entries` (list "Sample Status"). If UAT statuses include these, reuse; else add via seed or migration.

## 5. Key contracts

### 5.1 Atomic receive endpoint

**POST /api/samples/receive** (new endpoint, distinct from `/api/samples/accession`)

**Request (Pydantic):**

```python
class SampleReceiveRequest(BaseModel):
    container_barcode: str  # scanned or typed; becomes Sample.name and Container.name (L1)
    client_sample_id: Optional[str] = None  # external ID
    sample_type: UUID  # list entry ID
    matrix: UUID  # list entry ID
    project_id: UUID  # REQUIRED, sticky (L2)
    analysis_ids: List[UUID] = Field(default_factory=list)  # optional tests to attach
    temperature: Optional[float] = None  # optional
    client_id: Optional[UUID] = None  # if multi-client
    client_project_id: Optional[UUID] = None  # if grouping
    # NO status field — system writes "Received" then "Available for Testing"
    # NO container_type_id field — default tube (L3)
    # Open question: other "few fields" (date_sampled, qc_type, etc.)
```

**Response (Pydantic):**

```python
class SampleReceiveResponse(BaseModel):
    sample: SampleResponse  # includes id, name, status="Available for Testing"
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
            # 1. Get status list entries
            received_status = await self._get_status_by_name(db, "Received")
            available_status = await self._get_status_by_name(db, "Available for Testing")
            assigned_pending_status = await self._get_test_status_by_name(db, "Assigned/Pending")  # L4
            default_tube_type_id = await self._get_default_tube_type(db)  # L3
            
            # 2. Create sample (L1: name = barcode)
            sample = Sample(
                name=receive_data.container_barcode,  # L1: Sample.name = scanned barcode
                sample_type=receive_data.sample_type,
                matrix=receive_data.matrix,
                status=received_status.id,  # initially "Received"
                project_id=receive_data.project_id,  # L2: required
                temperature=receive_data.temperature,  # nullable
                client_sample_id=receive_data.client_sample_id,
                created_by=user_id,
            )
            db.add(sample)
            await db.flush()  # get sample.id
            
            # 3. Create container (L1: name = barcode, same string; L3: default tube type)
            container = Container(
                name=receive_data.container_barcode,  # unique; duplicate → 409
                type_id=default_tube_type_id,  # L3: default tube, off the form
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
            
            # 5. Create tests (optional; no wizard; L4: assigned/pending status)
            tests = []
            for analysis_id in receive_data.analysis_ids:
                test = Test(
                    sample_id=sample.id,
                    analysis_id=analysis_id,
                    status=assigned_pending_status.id,  # L4: assigned/pending, not In Process
                    created_by=user_id,
                )
                db.add(test)
                tests.append(test)
            
            # 6. Update sample status to "Available for Testing"
            sample.status = available_status.id
            
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

**L4: Refuse DELETE if test already has results.** Service checks `results.test_id`; if any exist, HTTP 400 with message "Cannot delete test with results."

(Or equivalent PATCH/PUT if product prefers bulk add/remove)

### 5.3 Result entry

**POST /api/tests/{test_id}/results** (or `/api/results` with `test_id` in body)

```python
class ResultEntryRequest(BaseModel):
    test_id: UUID
    analyte_id: UUID  # from analysis.analytes
    raw_result: str  # typed number (or text if data_type='text')
    unit_id: Optional[UUID] = None  # from units table; defaults from analytes.units_default
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

Service validates `analyte_id` exists in `analysis.analytes` for `test.analysis_id`. If `unit_id` is null, defaults from `analytes.units_default` (locked). No US-28 batch ceremony; one-off result entry only.

## 6. Runtime flows

### 6.1 Atomic receive (barcode scan happy path / high-volume scan loop)

1. Tech opens receive UI
2. Scan barcode → populate `container_barcode`
3. Select sample type, matrix, project (sticky across scans)
4. Optionally select analyses (tests) from dropdown
5. Submit → **POST /api/samples/receive**
6. Backend: single transaction creates sample (status=`Received` then `Available for Testing`), container (name=barcode, unique), contents, optional tests
7. UI: **stay on receive screen**. Toast success (e.g., "Sample [name] received"). **Clear barcode field**. **Keep sticky** sample type, matrix, project. **Focus barcode field** for next scan.
8. Repeat: scan next tube (step 2)

**Do NOT redirect to sample detail.** Do NOT open aliquot dialog. High-volume scan: next tube is the next action.

**Keyboard fallback:** If barcode scanner unavailable, type container name manually (same field).

**Duplicate barcode:** Unique constraint on `Container.name` → HTTP 409. UI shows error toast; tech re-scans or corrects.

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
- **Status picker UI:** hide status field on receive form (system sets `Received` then `Available for Testing`); existing sample edit forms may keep status picker for other workflows (or remove based on RBAC)
- **Temperature validation:** if Pydantic validators currently require `temperature`, remove validation or make optional
- **Bulk accession (US-24):** may coexist or be deprecated in favor of atomic receive; product decides
- **Barcode uniqueness:** `Container.name` unique constraint enforced (locked). Duplicate barcode → HTTP 409.

## 8. Locked decisions (not open)

- **One DB transaction** for sample + container + contents + tests (locked)
- **System sets status** "Received" then "Available for Testing" (locked). Drop status from request payload.
- **Barcode unique** (locked): `Container.name` unique constraint enforced. Duplicate → HTTP 409. No timestamp suffix disambiguation.
- **Sample.name = barcode** (L1, locked): `Sample.name` set to scanned barcode (same string as `Container.name`). Drop `generate_name_for_sample`.
- **Project required** (L2, locked): `project_id` required and sticky. Never auto-create a project per tube.
- **Container type default** (L3, locked): default tube, off the form. Do not ask the tech.
- **Test status** (L4, locked): tests created at receive use "Assigned/Pending" status (not "In Process"). Refuse DELETE if test already has results.
- **Unit defaults** from `analytes.units_default` (locked). If analyte has no default, unit selection required (edge case).
- **Tests at receive** are optional (locked)
- **Existing tables only** (locked). No new tables for parked features.

## 9. Open technical risks

| Risk | Mitigation |
|------|-----------|
| **Required fields on `Sample` block "few fields" flow** | Audit `Sample` model: if `matrix`, `sample_type`, `project_id` are nullable=False, they are already "few fields". If other columns (e.g., `due_date`, `qc_type`) are not-null, either: (1) make nullable, or (2) add to "few fields" list. **Open question: which fields beyond barcode (→ sample name)/sample_type/matrix/project are required?** |
| **Transaction boundaries with async SQLAlchemy** | Use `async with db.begin()` context manager (SQLAlchemy 2.0 async). Existing codebase may use sync `Session`; audit and refactor service layer to async if needed. |

**Not inventing field list:** This sketch assumes "few fields" = barcode (→ sample name + container name, L1) + sample_type + matrix + project (required, L2) + optional analyses. If product requires additional fields (date_sampled, qc_type, client_id, client_project_id, description, etc.), add them to `SampleReceiveRequest` schema.

## 10. Phase mapping

**P0 (atomic loop):**

- Backend: `/api/samples/receive` endpoint (atomic transaction, system-set status, unique barcode, L1: Sample.name = barcode, L2: project required, L3: default tube, L4: test status assigned/pending)
- Backend: `/api/samples/{sample_id}/tests` POST/DELETE (add/remove tests; L4: refuse DELETE if test has results)
- Backend: `/api/tests/{test_id}/results` POST (result entry, unit defaults from analyte)
- Frontend: receive form (scan barcode → sample name + container name [L1], sticky project [L2], container type off form [L3], stay-on-receive loop, focus barcode after success)
- Frontend: sample detail "Add Test" / "Remove Test" buttons (L4: disable Remove if test has results)
- Frontend: result entry form (raw value, unit defaults from analyte, qualifier)
- Migration: make `temperature` nullable (if not already)
- Migration: ensure `Container.name` unique constraint exists
- Seed/migration: ensure "Assigned/Pending" test status exists (L4)

**Deferred (not P0):**

- Bulk receive (rack of 96 samples) — may reuse US-24 bulk accessioning or build atomic bulk endpoint later
- Aliquot creation workflows (lineage via `parent_sample_id`) — schema exists but UI/service rules parked
- Method-matrix execute / dose-response / IC50 — models exist but execution parked
- ELN / experiment execute — parked
- Parsers / instrument import — separate packet

**UAT pass gate:** Dogfood → UAT → merge to `main` (production). See [`.docs/development-process/README.md`](../development-process/README.md).

---

**Next step:** Lab Ops Accept with conditions L1–L4 (folded in). Implement gate OPEN for Heidi / Hans / CEO reviews. Remaining open question: required fields beyond barcode (→ sample name)/sample_type/matrix/project. No product code until Heidi/Hans/CEO reviews pass.
