# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Status:** **Lab Ops L1–L4 Accept · CSO Accept (condition = L4 DELETE refuse) · Architecture Accept · Implement gate OPEN for CEO review. No product code until CEO passes and this sketch is tight.**  
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
- **System-set status** (Architecture lock): system writes **one** status on commit: **`Available for Testing`**. Do not write `Received` then overwrite it in the same transaction (it never lands in the DB). Techs do not pick status. Drop status from request payload. **Note:** Lab Ops wanted Received→Available; architecture lock is the durable end state only (Available for Testing). A Received hop would need an event log, which this packet does not add. No `status_history` table.
- **Identity** (L1 + Architecture lock): `Sample.name` and `Container.name` are **both** the scanned barcode (same string). Duplicate → HTTP 409. Drop `generate_name_for_sample`.
- **Keyboard fallback**: type barcode if scan fails
- **Receive body exact** (Architecture lock): required: `barcode`, `sample_type`, `matrix`, `project_id`; optional: `analysis_ids`, `temperature`, `client_sample_id`. Project required and sticky (L2). Container type = default tube, off the form (L3). Never auto-create project per tube.
- **Tests at receive**: optional (locked). Add/remove later from sample with no wizard. Status = assigned/pending, not In Process (L4). **Refuse DELETE** if test already has results (L4 + CSO data integrity).
- **Results entry** (Architecture lock): POST result on a test with raw value, optional qualifier (`<LOD`, `ND`). Unit from `analytes.units_default`; if missing, **422** the result. **Do not add `results.unit_id` column.** Do not add reported/review/curve fields.
- **High-volume scan UX** (locked): after successful receive, **stay on receive screen**. Toast success, **clear barcode**, **keep sticky** sample type/matrix/project, **focus barcode field**. Do not redirect to sample detail. Do not open aliquot dialog.

**Non-goals (parked features)**

- **ELN / method-matrix execute / aliquot execute** — sample and test models exist; execute/method-matrix stays parked
- **IC50 / dose-response / curve fitting** — not this cycle (CSO locked scientific bar: classic results only)
- **Method/QC/review ceremony** — no `reported_result` / review fields on this spine (CSO locked)
- **Parsers / instrument/CRO import** — see [data-parsers-lims-runs.md](data-parsers-lims-runs.md)
- **US-28 batch ceremony** — simple one-off result entry only
- **Manifests / materials / multi-tenant** — not in scope

### 2b. Aliquot lineage readiness (not implementation)

Aliquot lineage (`parent_sample_id`) **may exist** in schema. This sketch does **not** implement aliquot creation workflows. Future aliquot/execute work will add UI and service-level rules for lineage. The receive path will ignore `parent_sample_id` unless a future phase requires marking received samples as aliquots.

## 3. Component diagram

Reuse existing tables; no new receive-specific tables:

```
┌────────────────────┐
│ samples            │  existing (name = barcode [L1+Arch], sample_type, matrix,
│                    │           status, project_id REQUIRED [L2], temperature NULLABLE)
│                    │  ← system sets status = 'Available for Testing' [Arch]
│                    │     (no Received hop; would need event log)
└──────────┬─────────┘
           │ 1:N
           ▼
┌────────────────────┐     ┌────────────────────┐
│ contents (M2M)     │────►│ containers         │  existing (name = barcode, same string [L1+Arch])
│  sample_id         │     │  type_id = default tube [L3], off form
│  container_id      │     └────────────────────┘
└────────────────────┘
           │
           │ tests attached to sample (via tests.sample_id)
           ▼
┌────────────────────┐
│ tests              │  existing (sample_id, analysis_id, status = assigned/pending [L4])
└──────────┬─────────┘
           │ 1:N
           ▼
┌────────────────────┐
│ results            │  existing (test_id, analyte_id, raw_result, qualifiers)
│                    │  NO new unit_id column [Arch] — use analytes.units_default
│                    │  (created later via result entry, not at receive time)
└────────────────────┘
```

**Atomic boundary:** `ReceiveService.atomic_receive(...)` wraps sample, container, contents, tests creation in one transaction. Rollback if any insert fails.

**No new tables. No new columns. No wizard.** (Architecture lock)

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

**Reuse existing models (Architecture lock: no new columns):**

- `Sample` (backend/models/sample.py) — **no new fields**. `name` = barcode.
- `Container` (backend/models/container.py) — **no new fields**. `name` = barcode (same string).
- `Contents` (backend/models/container.py) — M2M join, no changes.
- `Test` (backend/models/test.py) — **no new fields**. Attach via `sample_id` + `analysis_id`.
- `Result` (backend/models/result.py) — **no new fields**. Do NOT add `unit_id` column (Architecture lock). Unit comes from `analytes.units_default`; if missing, service returns 422.

**Status list entry:** "Available for Testing" must exist in `list_entries` (list "Sample Status"). If UAT statuses include it, reuse; else add via seed or migration. Do NOT add "Received" status (Architecture lock: skip the hop; would need event log).

## 5. Key contracts

### 5.1 Atomic receive endpoint

**POST /api/samples/receive** (new endpoint, distinct from `/api/samples/accession`)

**Request (Pydantic) — Architecture exact contract:**

```python
class SampleReceiveRequest(BaseModel):
    # REQUIRED fields
    container_barcode: str  # scanned or typed; becomes Sample.name and Container.name (L1+Arch)
    sample_type: UUID  # list entry ID
    matrix: UUID  # list entry ID
    project_id: UUID  # REQUIRED, sticky (L2+Arch)
    
    # OPTIONAL fields
    analysis_ids: List[UUID] = Field(default_factory=list)  # optional tests to attach
    temperature: Optional[float] = None  # optional
    client_sample_id: Optional[str] = None  # external ID
    
    # DROPPED from request (Architecture lock):
    # - status (system writes "Available for Testing" only)
    # - container_type_id (default tube, off form [L3])
    # - client_id (not in exact contract)
    # - auto-create project flag (never auto-create per tube [L2])
```

**Response (Pydantic):**

```python
class SampleReceiveResponse(BaseModel):
    sample: SampleResponse  # includes id, name (= barcode), status="Available for Testing"
    container: ContainerResponse  # includes id, name (= barcode, same string)
    tests: List[TestResponse]  # optional, status = "Assigned/Pending"
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
            # 1. Get status list entries and defaults
            available_status = await self._get_status_by_name(db, "Available for Testing")  # Arch: only one status
            assigned_pending_status = await self._get_test_status_by_name(db, "Assigned/Pending")  # L4
            default_tube_type_id = await self._get_default_tube_type(db)  # L3
            
            # 2. Create sample (L1+Arch: name = barcode; Arch: status = Available for Testing directly)
            sample = Sample(
                name=receive_data.container_barcode,  # L1+Arch: Sample.name = scanned barcode
                sample_type=receive_data.sample_type,
                matrix=receive_data.matrix,
                status=available_status.id,  # Arch: persist one status only (Available for Testing)
                project_id=receive_data.project_id,  # L2+Arch: required, never auto-create
                temperature=receive_data.temperature,  # nullable
                client_sample_id=receive_data.client_sample_id,
                created_by=user_id,
            )
            db.add(sample)
            await db.flush()  # get sample.id
            
            # 3. Create container (L1+Arch: name = barcode, same string; L3+Arch: default tube, off form)
            container = Container(
                name=receive_data.container_barcode,  # Arch: unique; duplicate → 409
                type_id=default_tube_type_id,  # L3+Arch: default tube, off the form
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
            
            # 5. Create tests (optional; no wizard; L4+Arch: assigned/pending status)
            tests = []
            for analysis_id in receive_data.analysis_ids:
                test = Test(
                    sample_id=sample.id,
                    analysis_id=analysis_id,
                    status=assigned_pending_status.id,  # L4+Arch: assigned/pending, not In Process
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

**L4: Refuse DELETE if test already has results.** Service checks `results.test_id`; if any exist, HTTP 400 with message "Cannot delete test with results."

(Or equivalent PATCH/PUT if product prefers bulk add/remove)

### 5.3 Result entry

**POST /api/tests/{test_id}/results** (or `/api/results` with `test_id` in body)

```python
class ResultEntryRequest(BaseModel):
    test_id: UUID
    analyte_id: UUID  # from analysis.analytes
    raw_result: str  # typed number (or text if data_type='text')
    qualifier: Optional[UUID] = None  # list entry: '<LOD', 'ND', etc.
    # NO unit_id field (Architecture lock: do not add results.unit_id column)
```

**Response:**

```python
class ResultResponse(BaseModel):
    id: UUID
    test_id: UUID
    analyte_id: UUID
    raw_result: str
    reported_result: Optional[str]  # existing column only
    qualifiers: Optional[UUID]
    entered_by: UUID
    entry_date: datetime
    # NO unit field returned (Architecture lock: no new columns)
```

**Service logic (Architecture lock):**

- Validate `analyte_id` exists in `analysis.analytes` for `test.analysis_id`.
- Check `analytes.units_default` for the analyte. If missing, **HTTP 422** with message "Analyte has no default unit."
- Do NOT add `results.unit_id` column. Do NOT add reported/review/curve fields (Architecture + CSO lock).
- No US-28 batch ceremony; one-off result entry only.

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
- **Status picker UI:** hide status field on receive form (system sets `Available for Testing` only); existing sample edit forms may keep status picker for other workflows (or remove based on RBAC)
- **Temperature validation:** if Pydantic validators currently require `temperature`, remove validation or make optional
- **Bulk accession (US-24):** may coexist or be deprecated in favor of atomic receive; product decides
- **Barcode uniqueness:** `Container.name` unique constraint enforced (L1+Arch). Duplicate barcode → HTTP 409.
- **Unit handling:** existing `analytes.units_default` column used; no schema change. Service validates default exists (422 if missing).

## 8. Locked decisions (not open)

**Lab Ops L1–L4:**
- **L1 Identity**: `Sample.name` and `Container.name` are **both** the scanned barcode (same string). Duplicate → HTTP 409. Drop `generate_name_for_sample`.
- **L2 Project**: `project_id` required and sticky. Never auto-create a project per tube.
- **L3 Container type**: default tube, off the form. Do not ask the tech.
- **L4 Test status**: tests created at receive use "Assigned/Pending" status (not "In Process"). Refuse DELETE if test already has results.

**Architecture (Heidi):**
- **One DB transaction** for sample + container + contents + tests.
- **System sets status**: persist **one** status on commit: **`Available for Testing`**. Do not write `Received` then overwrite it (it never lands in the DB). Lab Ops wanted Received→Available; architecture lock is the durable end state only. A Received hop would need an event log, which this packet does not add. **No `status_history` table.**
- **No new columns**: Do NOT add `results.unit_id`. Unit comes from `analytes.units_default`; if missing, HTTP 422. Do NOT add reported/review/curve fields.
- **No new tables. No wizard.** Existing tables only.
- **Receive body exact**: required: `barcode`, `sample_type`, `matrix`, `project_id`; optional: `analysis_ids`, `temperature`, `client_sample_id`. Drop `client_id` and `container_type_id` from request.

**CSO (Hans):**
- **Classic results only** (locked scientific bar): raw value, unit default from `analytes.units_default`, optional qualifier (`<LOD`, `ND`). Analyte must belong to test's analysis.
- **No IC50, no dose-response, no method/QC/review ceremony** on this spine (locked). No `reported_result` / review fields.
- **DELETE /tests must refuse when test already has results** (data integrity, CSO condition = L4). Not optional, not scope creep.
- **Sample.name = barcode** (L1) is the right identity (CSO concurs).

**All reviews:**
- **Tests at receive** are optional.
- **High-volume scan UX**: stay on receive screen; toast success; clear barcode; sticky type/matrix/project; focus barcode. No sample-detail redirect. No aliquot dialog.

## 9. Open technical risks

| Risk | Mitigation |
|------|-----------|
| **Required fields on `Sample` block "few fields" flow** | Audit `Sample` model: if `matrix`, `sample_type`, `project_id` are nullable=False, they are already "few fields". If other columns (e.g., `due_date`, `qc_type`) are not-null, either: (1) make nullable, or (2) add to "few fields" list. **Open question: which fields beyond barcode (→ sample name)/sample_type/matrix/project are required?** |
| **Transaction boundaries with async SQLAlchemy** | Use `async with db.begin()` context manager (SQLAlchemy 2.0 async). Existing codebase may use sync `Session`; audit and refactor service layer to async if needed. |

**Not inventing field list:** This sketch assumes "few fields" = barcode (→ sample name + container name, L1) + sample_type + matrix + project (required, L2) + optional analyses. If product requires additional fields (date_sampled, qc_type, client_id, client_project_id, description, etc.), add them to `SampleReceiveRequest` schema.

## 10. Phase mapping

**P0 (atomic loop):**

- Backend: `/api/samples/receive` endpoint (atomic transaction, system-set status = "Available for Testing" [Arch], unique barcode, L1+Arch: Sample.name = Container.name = barcode, L2+Arch: project required/no auto-create, L3+Arch: default tube off form, L4: test status assigned/pending)
- Backend: `/api/samples/{sample_id}/tests` POST/DELETE (add/remove tests; L4+CSO: refuse DELETE if test has results)
- Backend: `/api/tests/{test_id}/results` POST (result entry; Arch: unit from analytes.units_default, 422 if missing; no new columns)
- Frontend: receive form (scan barcode → sample name + container name [L1+Arch], sticky project [L2], container type off form [L3+Arch], stay-on-receive loop, focus barcode after success)
- Frontend: sample detail "Add Test" / "Remove Test" buttons (L4+CSO: disable Remove if test has results)
- Frontend: result entry form (raw value, qualifier; Arch: no unit selector, defaults from analyte)
- Migration: make `temperature` nullable (if not already)
- Migration: ensure `Container.name` unique constraint exists (L1+Arch)
- Seed/migration: ensure "Available for Testing" sample status exists (Arch)
- Seed/migration: ensure "Assigned/Pending" test status exists (L4)
- **Do NOT add:** `status_history` table, `results.unit_id` column, reported/review/curve fields (Arch lock)

**Deferred (not P0):**

- Bulk receive (rack of 96 samples) — may reuse US-24 bulk accessioning or build atomic bulk endpoint later
- Aliquot creation workflows (lineage via `parent_sample_id`) — schema exists but UI/service rules parked
- Method-matrix execute / dose-response / IC50 — models exist but execution parked
- ELN / experiment execute — parked
- Parsers / instrument import — separate packet

**UAT pass gate:** Dogfood → UAT → merge to `main` (production). See [`.docs/development-process/README.md`](../development-process/README.md).

---

**Next step:** Lab Ops L1–L4 Accept · CSO Accept · Architecture Accept (all folded in). Implement gate OPEN for CEO review. Remaining open question: required fields beyond barcode (→ sample name)/sample_type/matrix/project. No product code until CEO passes and this sketch is tight. Heidi bounces the sketch if it grows a table or a wizard.
