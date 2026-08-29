# Developer Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Reviewer persona:** Skilled Developer  
**Packet:** tech sketch + schema-changes + Lab Ops L1–L5 + related reviews  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/post-receive-work-spine.md) (Accept with conditions; P1 gate OPEN)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)

This stamp licenses **P1 only**. P2–P5 are mapped so the spine is implementable later. Do not code P2–P5 in the P1 PR.

---

## 1. Executive summary

P1 is Cursor-ready once the conditions below land in the **same PR**. The sketch, schema delta, and Lab Ops L1 are enough to implement an asked-for lake without inventing a second execute stack.

The packet is **not** ready as a single mega-PR. Existing code already has the wrong gravity wells:

| Existing | Role in this packet | Trap |
|----------|---------------------|------|
| `atomic_receive_service` + `POST /samples/receive` | **Freeze.** Keep `analysis_ids` 422. | Do not reopen CORE. |
| `TestsManagement` / `POST /tests` / `TestForm` | Classic Test grid (WO-4 type-a-number still lives here). | **Do not reuse `TestForm`.** It is Test CRUD copy and `test:update`. |
| `ELNProcessService.instantiate_from_definition` | P2 start of first process. | Do not call from asked-for create. |
| `LimsRunService.start_run` + `ResultPromotionService.ensure_test` | P2 WO-7: mint Test at **start**; **stop** ensure-on-publish. | Today `ensure_test` still runs on publish (`plan_promotion` `dry_run=False`). |
| `DataParsersManagement` + `/v1/data-parsers` | P5 setup UX (engine shipped). | No new import engine. |

P1 is a **new domain** (`asked_for`), mounted like other post-wizard APIs (`/v1/...`), modeled like `Result`/`DataParser` (**not** `BaseModel` — unique `name` would explode). Multi-sample L1 is one transactional write, not N independent POSTs. Hidden samples return **403** like receive, not `require_accessible_sample` 404.

**P2 coding remains closed** until OQ-WO-1 / OQ-WO-3 are Decided and L2 names a real column for type eligibility (`eln_process_definition_steps.experiment_template_id` is still NOT NULL; no `analysis_id`; no accepted-type config). **P3 is closed** until OQ-RES-1: `results.qualifiers` is a UUID FK to `list_entries`, not JSON.

**Verdict: Accept with conditions** for P1. Later phases are file-mapped, not licensed.

---

## 2. Implementation readiness assessment

| Dimension | Notes |
|-----------|--------|
| **Sketch → code mapping** | P1 files are nameable. P2–P5 targets exist. Spec HTTP vs repo prefix (`/api/v1` nginx-stripped `/v1`) must be locked (**D3**). |
| **Convention adherence** | Follow `eln_processes` / `data_parsers` (service + Pydantic + `/v1` router + `main.py` include). Do **not** inherit `BaseModel` unique `name`. Do **not** copy `TestForm`. |
| **Migration & schema safety** | P1 = two tables only. Head is `0071`. `asked_for.routed_work_order_id` must not FK `work_orders` in P1 (**D1**). RLS FORCE + GRANT `lims_app` like `0068`. |
| **API contract completeness** | Spec POST is single `sample_id`; L1 is a sample **set**. Lock `sample_ids[]` + one txn (**D4**). 403 vs 404 and Client-role deny must be explicit (**D5**). Status is UUID on `samples`, not a string (**D6**). |
| **Incremental delivery** | One phase per PR. Receive freeze. P1 ships with zero Tests / zero WOs. |
| **Test scaffolding** | Pytest file + RLS 403 + unique 409 + params 422 + tests-count-0. Jest: new page, not `TestsManagement.test.tsx`. |
| **Cursor hand-off** | Enough for P1 if D1–D11 are treated as bounce. Docs + UAT + README are in-scope for the P1 PR. |
| **Tech-debt / complexity** | No second AuthZ permission. No routing in P1. No FieldDefinition reuse for param defs (own small catalog). Empty `params {}` is the OOB path. |

---

## 3. Suggested module / file impact

### 3.1 P1 (this PR) — existing / new

| Area | Existing / New | Notes |
|------|----------------|--------|
| Alembic | **New** `backend/db/migrations/versions/0072_asked_for_p1.py` (`down_revision = "0071"`) | Tables: `analysis_param_defs`, `asked_for`. Partial unique `uq_asked_for_open`. Check `asked_for_status_chk`. Indexes on `sample_id`, `status`. ENABLE + FORCE RLS. GRANT `lims_app`. **No** `routing_map` / `work_orders`. |
| Models | **New** `backend/models/asked_for.py` (or columns on `models/analysis.py` for param defs) | `AskedFor` and `AnalysisParamDef` extend **`Base`**, not `BaseModel`. Audit columns only (id, created_at/by, modified_at/by, active optional). Register in `backend/models/__init__.py`. |
| Schemas | **New** `backend/app/schemas/asked_for.py` | Create: `sample_ids: list[UUID]` (min 1), `analysis_id`, `tat_days: int ge=1`, `params: dict` default `{}`. List/read/cancel. Param-def CRUD shapes. |
| Service | **New** `backend/app/services/asked_for_service.py` | `create` / `list` / `get` / `cancel` / `validate_params`. Copy receive 403 project check. Resolve Available for Testing via `resolve_available_for_testing_status`. Catch `IntegrityError` → 409. **Do not** import Test/ELN/LimsRun create. |
| Router | **New** `backend/app/routers/asked_for.py` | `APIRouter(prefix="/asked-for")`. POST `""` 201, GET `""`, GET `/{id}`, POST `/{id}/cancel`. |
| Analyses param-defs | **Edit** `backend/app/routers/analyses.py` | `GET/PUT /analyses/{id}/param-defs`. PUT = `require_config_edit`. Do not add a second `/v1/analyses` router. |
| App mount | **Edit** `backend/app/main.py` | `app.include_router(asked_for.router, prefix="/v1")` next to `eln_processes`. Nginx `/api` strip → HTTP `/api/v1/asked-for`. |
| Receive freeze | **Do not edit** `backend/app/services/atomic_receive_service.py`, `app/schemas/sample.py` `reject_nonempty_analysis_ids` | Keep 422. `_create_tests_for_sample` in `app/routers/samples.py` stays unused by this packet. Function `_create_asked_for_tests` **does not exist** — do not invent it. |
| Classic Tests | **Do not edit** `backend/app/routers/tests.py` for P1 | `POST /tests` still mints Tests (WO-4). Leave it. |
| Frontend page | **New** `frontend/src/pages/AskedFor.tsx` | FillHeightPage + DataGrid. Multi-select Available-for-Testing samples, analysis Autocomplete from `apiService.getAnalyses` + `unwrapAnalysesList`, TAT, params if defs exist. Copy: “Asked-for” / “requested analysis”. **No Start / Execute.** |
| Frontend form | **New** `frontend/src/components/asked-for/AskedForForm.tsx` (name as convenient) | **Do not import** `components/tests/TestForm.tsx`. |
| Sample detail | **Edit** `frontend/src/pages/SamplesManagement.tsx` | Section under the existing “Process journey” block in the sample dialog: asked-for table + add (same form, pre-filled `sample_ids: [id]`). |
| Sidebar | **Edit** `frontend/src/components/Sidebar.tsx` | Sample Mgmt item **Asked-for** immediately after Receive. Expand accordion on `/asked-for`. Permission: show if `sample:read` or `test:assign`. |
| Routes | **Edit** `frontend/src/App.tsx` | `/asked-for` — view `sample:read`, create UI gated `test:assign`. |
| API client | **Edit** `frontend/src/services/apiService.ts` | `createAskedFor`, `getAskedFor`, `cancelAskedFor`, `getAnalysisParamDefs`. Paths `/v1/asked-for`, `/analyses/{id}/param-defs`. |
| Jest | **New** `frontend/src/__tests__/AskedFor.test.tsx`; **Edit** `frontend/src/__tests__/Sidebar.test.tsx` | Assert Asked-for label; never render TestForm. |
| Pytest | **New** `backend/tests/test_asked_for_p1.py` | See §6. Reuse atomic-receive fixtures / 0058 analyses (ELISA if present). **Do not** invent Qubit/blood IDs. |
| Docs / UAT | **New** `UAT_Scripts/uat-post-receive-work-spine.md`; **Edit** manuals + README as in §6 | Mandatory with implement. Point `uat-test-ordering.md` at Asked-for for *new* requests (do not delete classic Test cases). |

### 3.2 P2 (not this PR) — file map only

| Area | File | Work |
|------|------|------|
| Migration | new `007x_routing_work_orders.py` | `routing_map` keyed by analysis + TAT (`int4range` + `EXCLUDE USING gist`); retract admin-authored `sample_type_id`. `work_orders` keeps one process FK. |
| Type gate (L2 / OQ-WO-4) | `eln_process_definition_step_accepted_sample_types`; nullable template + `analysis_id` for `lims_run` | Route compares current type with the first ordered step only. Later steps gate at start. Empty/incompatible = `route_sample_type` 422. **Do not** read `sample_type_transitions`. |
| Route | `asked_for_service` + `routing_service` / `work_order_service` | Explicit Route per OQ-WO-1. Empty map → 200 `work_order: null`. Overlap 409 by analysis. Derive first-process / first-step type display; no sample-type picker. |
| Start | `ELNProcessService.instantiate_from_definition` (`backend/app/services/eln_process_service.py` ~L212) via `POST /v1/eln-process-definitions/{id}/instantiate` | Existing `experiment:manage`. One definition’s typed steps remain ordered and visible (L4). |
| WO-7 | `backend/app/services/lims_run_service.py` `start_run` (~L191) | Insert Test if missing; snapshot asked-for `params` onto Test (L3) and freeze. |
| Publish refuse | `backend/app/services/result_promotion_service.py` `ensure_test` (~L164) called from `plan_promotion` when `dry_run=False` (~L313) | Remove find-or-create on publish; 422 if Test missing. |
| UI | new Work Orders page **or** extend Processes; routing-map admin (`config:edit`) | Not `/asked-for` Start CTA. |

### 3.3 P3 — file map only (blocked on OQ-RES-1)

| Area | File | Work |
|------|------|------|
| Persist | **New** `persist_typed_result` in `backend/app/services/` (or fold into results router) | Called by `backend/app/routers/results.py` `POST /results` and LimsRun entry. Unit from `analytes.units_default`; 422 if null. **No** `results.unit_id`. |
| Qualifiers mismatch | `backend/models/result.py` L31 | `qualifiers` is **UUID FK to `list_entries`**, not JSON. Sketch/OQ-RES-1 JSON `{"entered_as"}` **cannot land without a schema change or a different column**. Hold P3. |
| UI | `frontend/src/components/results/ResultsEntryTable.tsx` | Align writers; two writers → 409 (`lims_run_id` ownership already on Result). |

### 3.4 P4 — file map only

| Area | File | Work |
|------|------|------|
| Apply | `backend/app/services/sop_parse_service.py` `apply_job` (~L148) | Today: ExperimentTemplate only. Change success path → `eln_process_definitions` + `_definition_steps`. LimsRun steps need **nullable** `experiment_template_id` + `analysis_id` (schema delta). |
| Job FK | `models/flexible_experiment.py` `SopParseJob`; migration ADD `process_definition_id` | Per schema-changes. |
| Router | `backend/app/routers/sop_parse.py` `POST /{job_id}/apply` | Response includes `process_definition_id`. Never silent activate (L5). |
| Copy | manuals / Apply success | Must not claim blood → DNA → Qubit is runnable. |

### 3.5 P5 — file map only (may parallel P1 staffing-wise; not in P1 PR)

| Area | File | Work |
|------|------|------|
| Engine | `backend/app/services/data_parser_service.py`, `backend/app/routers/data_parsers.py` | Already: CRUD, setup-files, `POST /v1/data-parsers/test`, `POST /{id}/activate`. |
| UX gap | `frontend/src/pages/admin/DataParsersManagement.tsx` | Has test-files + activate; **no labeled dry-run / example + expected-output gate**. Close R-8 here, not a new engine. `InstrumentCatalogManagement.tsx` already exists. AI draft stays setup-only / config-gated. |

---

## 4. Conditions (must land with implement)

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **D1** | **P1** | **P1 migration is two tables only.** `analysis_param_defs` + `asked_for`. Do **not** create `routing_map` or `work_orders`. Do **not** FK `asked_for.routed_work_order_id` → `work_orders` (omit the column in P1, or nullable UUID **without** FK). Alembic revision `0072` revises `0071`. Rollback: `DROP TABLE` both (no backfill). Fill revision id into schema-changes after implement. Unique `(analysis_id, key)` on param defs. Status **text + check** (`requested`/`routed`/`cancelled`) — do not use `list_entries` UUID (unlike `samples.status`). | Sketch lists `routed_work_order_id` on the P1 table; that FK cannot exist until P2. `BaseModel`/enum traps are worse than a nullable uuid with no FK — omitting the column is cleaner. |
| **D2** | **P1** | **Do not subclass `BaseModel` for `asked_for` or `analysis_param_defs`.** Follow `Result` / `DataParser` / `ELNProcessSample`: `Base` + explicit id/audit. No global unique `name`. | `BaseModel.name` is `unique=True, nullable=False`. A request lake cannot share Test’s naming scheme. |
| **D3** | **P1** | **Mount asked-for at `/v1/asked-for`** (`main.py` include like `eln_processes`). Trailing-slash-safe (`redirect_slashes=False` — use `""` not `"/"`). **Param-defs stay on the existing analyses router:** `GET/PUT /analyses/{id}/param-defs` (nginx `/api/analyses/...`). Do not create `/v1/analyses`. Frontend `apiService` must hit those exact paths. | Spec writes `/api/v1/asked-for` (correct after nginx strip) **and** `/api/v1/analyses/{id}/param-defs` (would fork analyses). Catalog CRUD in this repo is unversioned (`/analyses`); new ELN/LIMS domains use `/v1`. |
| **D4** | **P1** | **One operator action → one transaction.** POST body: `sample_ids: UUID[]` (min 1) + `analysis_id` + `tat_days` + `params`. Insert **one row per sample**. Partial unique violation on any pair → **409 + full rollback** (mirror receive barcode 409). Response: `201` `{ items: AskedForRead[], count }`. Accept alias `sample_id` as a 1-element convenience if cheap; do not document two public create APIs. Frontend loops of independent POSTs are **bounce**. | L1 rack order. Spec’s single `sample_id` would leave half a rack requested on 409. |
| **D5** | **P1** | **AuthZ + 403.** Write/cancel: `require_test_assign` **and** role name ≠ `Client` (0013 falls back to granting `test:assign` when `test:read` is missing — Client must not write). List/get: `sample:read` (Client may read own project rows via RLS). Hidden / other-project sample: **403** with receive wording, **not 404**. **Do not** call `sample_access.require_accessible_sample` (it 404s). Copy `atomic_receive_service.require_project_for_receive` / `has_project_access` savepoint. Inactive analysis → 422. | Packet error table + RQ-AF-7/8. 404 would leak existence unlike CORE receive. |
| **D6** | **P1** | **Status gate uses the list entry, not a string column.** `Sample.status` is UUID → `list_entries`. Reuse `resolve_available_for_testing_status`. If sample status ≠ that entry → **422** (discarded / etc.). **Do not** refuse a second analysis solely because the sample is already on an ELN process (Lab Ops watch: Decision #24 is process membership, not Sample.status). `tat_days` CHECK `> 0` matches schema; UI may default from `analyses.turnaround_time` but must still send an int. | Naive `sample.status != "Available for Testing"` will always 422. |
| **D7** | **P1** | **Zero downstream rows.** `AskedForService.create` must not create Test, Result, Process, Experiment, LimsRun, or work_order. Do not call `_create_tests_for_sample`. Do not import routing. P1 writes `requested` / `cancelled` only. Cancel after `routed` → 422 (P2). Receive code freeze except proven CORE bugs. Pytest must assert `COUNT(tests)` unchanged. | WO-7 / L1. Tests page still mints Tests — that is not this PR’s order path. |
| **D8** | **P1** | **UI is not TestForm and not `/receive`.** New `/asked-for` page + sample-detail section. Reuse **analysis dropdown data** (`getAnalyses` / `unwrapAnalysesList`), nothing else from TestForm. Copy: “Asked-for” / “requested analysis” — never assign/create test, start work, or order process. **No Start/Execute CTA** on `requested`. Sidebar Sample Mgmt: **Asked-for immediately after Receive**. Params UI: if defs empty, send `{}` and hide fields; unknown keys 422 from API. | Muscle memory on Tests will keep minting Tests; this page must not look like Test assignment. |
| **D9** | **P1** | **RLS + unique handling.** FORCE RLS on both tables. `asked_for`: USING **and** WITH CHECK via `samples.project_id` + `has_project_access` (mirror `tests_access`, add WITH CHECK like `0068`). `analysis_param_defs`: read authenticated lab roles; write `config:edit` / admin (API-enforced write is acceptable if policy is admin-or-authenticated-read like instrument catalogs — still FORCE RLS). GRANT `lims_app`. Catch unique `uq_asked_for_open` → 409. Cancelled row may be re-created (partial unique ignores cancelled). | Schema-changes §2.5. USING-only policies fail inserts under FORCE RLS. |
| **D10** | **P1** | **Docs + UAT in the same PR.** Create `UAT_Scripts/uat-post-receive-work-spine.md` with AC-P1-1..3 (receive → ELISA asked-for → zero Tests/WOs; dup 409; cross-project 403). Do **not** use retired `uat-sample-accessioning.md`. Update `.docs/review/manuals/navigation.md`, `api-endpoints.md`, `accessioning-workflow.md` (after receive → Asked-for, not TestForm), and `README.md` / `frontend/README.md` route list. Fill Alembic id in schema-changes. No Qubit/blood testdata. | Full-pipeline implement requirements. |
| **D11** | **P1** | **Pytest/Jest minimums** (see §6). Include: Client 403 on POST; lab-tech 201; IntegrityError 409; unknown param key 422; empty defs + `{}` 201; receive still 422 on `analysis_ids`; asked-for create leaves tests count 0; RLS-hidden sample 403. | Sketch §3.4 + QA will need these even before a QA review stamp. |
| **D12** | **P2 (not P1)** | **Marc/Rolf superseding lock:** remove map sample-type authoring. Match analysis + TAT. Derive allowed types from the selected first/only process and first ordered step. Route gates that step only; later steps gate current type at start. Keep `eln_process_definition_step_accepted_sample_types`, nullable `experiment_template_id` + `analysis_id`, `btree_gist`, and ensure-test off publish. | Map-create lock + Lab Ops integrity. |
| **D13** | **P3 (not P1)** | Do **not** implement persist lock until OQ-RES-1 decides how typed `qualifiers` relate to the existing UUID FK. Do not add `results.unit_id`. | Schema-changes “P3 none” contradicts JSON qualifiers. |

---

## 5. Recommended implementation order

**PR 1 — P1 only (licensed by this stamp + Lab Ops L1):**

1. Migration `0072` + models + `__init__` import (D1, D2, D9).  
2. Pydantic schemas + `AskedForService` (D4–D7) + analyses param-defs endpoints (D3).  
3. Router + `main.py` include.  
4. Pytest `test_asked_for_p1.py` (D11) — fail-first on 409/403/422/zero Tests is fine.  
5. `apiService` + `AskedFor.tsx` + form (not TestForm) + Sidebar + `App.tsx` + sample-detail section (D8).  
6. Jest Sidebar + AskedFor.  
7. Docs / UAT / schema-changes revision id (D10).  
8. Dogfood then UAT pass before merge to `main`.

**Do not** in PR 1: routing, work_orders, LimsRun WO-7 move, SOP Apply rewrite, parser dry-run UX, receive edits, TestForm reuse, Qubit/blood seeds.

**Later PRs (mapped, not licensed):**

| PR | Scope | Gate |
|----|--------|------|
| 2 | P2 routing + work_order + route + start via existing process instantiate + WO-7 start/publish | D12 + OQ-WO-1/3 Decided |
| 3 | P3 `persist_typed_result` + results UAT fold | D13 + OQ-RES-1 |
| 4 | P4 SOP Apply → process definition (nullable template on LimsRun steps) | L5 copy; OQ-SOP-2 if parser draft |
| 5 | P5 parser setup UX on existing `DataParsersManagement` | Independent of P1 code; still not in PR 1 |

Coding stays Grok Build. One phase per PR.

---

## 6. Cursor hand-off notes

Treat **D1–D11** as bounce for the P1 PR. Prompt the implementer to:

1. Follow existing FastAPI layout: `models/` + `app/schemas/` + `app/services/` + `app/routers/` + `main.py`. PEP8, existing HTTPException patterns, `require_test_assign` / `require_config_edit` from `app/core/rbac.py`.  
2. Frontend: MUI DataGrid + FillHeightPage like `TestsManagement`, but **new files**. ESLint via `react-scripts` (do not fight the broken root `.eslintrc.js`).  
3. **Update documentation, UAT test scripts, and README files** in the same PR: `UAT_Scripts/uat-post-receive-work-spine.md` (P1 cases only), `.docs/review/manuals/navigation.md`, `.docs/review/manuals/api-endpoints.md`, `.docs/review/manuals/accessioning-workflow.md`, `README.md` / `frontend/README.md` as needed, and schema-changes Alembic id.  
4. Do not expand to P2–P5. Do not invent testdata IDs for Qubit/blood. Do not reopen `/receive`.

**Pytest sketch (P1):** `backend/tests/test_asked_for_p1.py` using the same client/auth fixtures as `test_atomic_receive_phase3.py` / `test_tests.py`.

| Case | Expect |
|------|--------|
| POST one Available-for-Testing sample, empty params, active analysis | 201, `status=requested`, `COUNT(tests)` unchanged, no work_orders table needed |
| POST same `(sample, analysis)` again | 409 |
| Cancel then POST again | 201 |
| `params` unknown key (insert a def in-test or PUT param-defs as config:edit) | 422 |
| `tat_days=0` | 422 |
| User without project access | 403 (not 404) |
| Client role POST | 403 |
| Missing `test:assign` | 403 |
| Receive `analysis_ids: [uuid]` | still 422 `"analysis_ids must be empty"` |
| Multi `sample_ids` with one duplicate open | 409, **zero** new rows |

**Jest:** Asked-for heading; no “Assign test” / “Start”; Sidebar item after Receive.

**Parallel reviews:** Architecture / Security / QA / BA / UI stamps were not in the packet at this writing. Lab Ops opened P1. Do not merge P1 to `main` without those reviews Accept / Accept-with-conditions **or** an explicit Leadership waiver. This Developer stamp does not replace them.

---

## 7. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (D1–D11 for P1; D12–D13 bind later phases) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** (same as Lab Ops), provided D1–D11 land in the P1 PR |
| **P1** | Licensed. First PR. |
| **P2** | **CLOSED** (D12; OQ-WO-1/3 Open; type-eligibility column missing) |
| **P3** | **CLOSED** (D13; `results.qualifiers` type vs OQ-RES-1) |
| **P4 / P5** | File-mapped; not in P1 PR. P5 may be a later independent PR. |
| **Not licensed** | Receive reopen · TestForm reuse · mint Tests at asked-for · routing tables in 0072 · Qubit/blood testdata · dest-type E2E |

```
DEVELOPER REVIEW: Accept with conditions
```
