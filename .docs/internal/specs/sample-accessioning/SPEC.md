# Spec: Sample accessioning

**Domain:** Sample accessioning  
**PRD:** [../../prd/sample-accessioning/PRD.md](../../prd/sample-accessioning/PRD.md)  
**Issues:** [../../prd/sample-accessioning/ISSUES.md](../../prd/sample-accessioning/ISSUES.md)  
**Date:** 2026-08-26 (framework-first + AR CORE)  
**Framework:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Design SoT:** [../../../review/tech-sketch/atomic-receive.md](../../../review/tech-sketch/atomic-receive.md)  
**AuthZ:** [../../../review/security-review/atomic-receive.md](../../../review/security-review/atomic-receive.md)  
**Gate:** Leadership team **IMPLEMENT GATE OPEN (CORE only)** — [lab-ops](../../../review/lab-ops-review/atomic-receive.md) · [ceo](../../../review/ceo-review/atomic-receive.md) · [rollup](../../../discussions/2026-08-26-ar-core-leadership-team-review.md)

---

## 0. Framework

| Item | Spec stance |
|------|-------------|
| OOB profile | **Atomic receive only** (FW-1) |
| Future profiles | DB-stored intake configs; activate to sidebar with **`config:edit`** (FW-1b) |
| Workflow Templates | Separate (FW-2) — not a substitute for intake profiles |
| Analysis at receive | Not the work plan; prefer omit on default body; work_order/routing is processing |
| AuthZ | Always sample create + project RLS regardless of profile |
| CORE vs later | **CORE** = identity + 1..N vessels + field align + docs/UAT. **Not CORE:** results-entry, profile engine, work_order |

**Implement:** Leadership team gate **OPEN for CORE** (2026-08-26). Spec sections marked **CORE** are normative for the first code slice.

---

## 1. Scope

### 1.1 CORE (normative)

| Area | Spec |
|------|------|
| API | `POST /api/samples/receive` |
| UI | New receive loop (scan → sticky → commit → stay) |
| Data | Sample + **1..N** Containers + Contents; optional Tests |
| AuthZ | Sample create + project RLS; one path; one txn |
| Cutover | Pytest + `uat-atomic-receive.md` as receive happy path |

### 1.2 Out of CORE

Results-entry API/UI as ship blocker; aliquot/derivative; intake-profile engine; FieldDefinitions on receive body; work_order/routing; wizard as forever path; second receive API.

### 1.3 Legacy (shipped, not happy path)

`POST /samples/accession` (wizard), `POST /samples/bulk-accession` — remain until cutover; must not be the CORE receive story.

---

## 2. Sample model (intake-relevant)

| Column | Rule at intake |
|--------|----------------|
| `name` | Unique lab ID from name template / sequence (**CORE**) |
| `sample_type`, `matrix`, `status` | Required FKs → `list_entries`; status written as Available for Testing |
| `project_id` | Required (**CORE**) |
| `received_date` | Set on receive (**CORE**) |
| `client_sample_id` | Optional unique |
| `temperature` | Optional; nullable if not already |
| `parent_sample_id` | Null at intake; set on derivatives later |
| `qc_type`, `specimen_biotype_id` | Optional / list-backed — **not** on CORE receive body |
| `custom_attributes` | Legacy JSONB — FieldDefinitions are extensibility path (not CORE body) |

**Code:** `backend/models/sample.py`, `backend/models/field_definition.py`

---

## 3. CORE contract — atomic receive

### 3.1 Request

```http
POST /api/samples/receive
```

```json
{
  "container_barcode": "string",
  "additional_container_barcodes": ["string"],
  "sample_type": "uuid",
  "matrix": "uuid",
  "project_id": "uuid",
  "analysis_ids": ["uuid"],
  "temperature": 4.0,
  "client_sample_id": "string"
}
```

| Field | Rule |
|-------|------|
| `container_barcode` | **Required** — primary vessel |
| `additional_container_barcodes` | Optional (0..N); each → another container + contents on the **same** sample |
| `sample_type`, `matrix`, `project_id` | **Required** |
| `analysis_ids` | Optional; prefer empty; if set → asked-for Tests only |
| `temperature`, `client_sample_id` | Optional |
| All barcodes | Unique among themselves and vs DB; any collision → **409** (no partial commit) |

**Omit from body:** sample name, status, container type, `due_date`, `qc_type`, `client_id`.

### 3.2 Server behavior (one transaction)

1. AuthZ: same as sample create + `has_project_access` / RLS for `project_id` (enforce in service). Clients → refuse.  
2. Resolve default **tube** container type (all vessels on this call).  
3. Generate `samples.name` via existing name template.  
4. Insert sample — status **Available for Testing**, `received_date=now`.  
5. For **primary + each additional** barcode: insert container (`name=barcode`) + contents → sample.  
6. Optional: create Tests for `analysis_ids` — status **Assigned/Pending** (not In Process).  
7. Commit. On any failure (including barcode 409) → **full rollback**.

**No new tables.** Ensure `containers.name` unique if missing; `temperature` nullable if needed. Do not add `status_history` or `results.unit_id`.

### 3.3 Response (minimum)

Return enough for toast/UX: created `sample_id`, `samples.name`, container id(s)/barcode(s). Exact schema may follow existing sample response patterns; must not require a sample-detail redirect.

### 3.4 UI behavior

| Rule | Detail |
|------|--------|
| Fields sticky | `sample_type`, `matrix`, `project_id` (+ optional temp / client_sample_id) |
| Barcodes | Primary required; control to add more before submit |
| Absent | Sample-ID field; status picker; container type picker; aliquot dialog |
| After success | Toast; clear barcode field(s); keep sticky; focus primary; **stay on receive** |
| Dup barcode | 409 toast; stay on screen; no partial commit |

### 3.5 AuthZ (S-AR-1..5)

| ID | Rule |
|----|------|
| S-AR-1 | Same AuthZ as sample create; no new receive permission |
| S-AR-2 | Project RLS inside receive service |
| S-AR-3 | One API; one txn; 1..N vessels in that txn |
| S-AR-4 | Refuse orphan multi-call as receive substitute |
| S-AR-5 | No client bypass |

---

## 4. Related CORE endpoints (thin)

| Endpoint | CORE rule |
|----------|-----------|
| `POST /api/samples/{id}/tests` | Optional later attach; not required for empty-analysis receive |
| `DELETE /api/samples/{id}/tests/{test_id}` | **400** if any results exist (A-14 light-ride OK) |

**Not CORE:** `POST /api/tests/{id}/results` as a ship/UAT blocker. Persist lock (typed number → `reported_result` + `qualifiers`; `raw_result` may copy; unit from `analytes.units_default`) remains design SoT for a **follow-on** slice.

---

## 5. Acceptance criteria (testable)

Maps to PRD §6 / RQ-AR-*.

| ID | Assertion | PRD |
|----|-----------|-----|
| **AC-AR-1** | Primary-only receive → 1 sample, 1 container, 1 contents; status Available for Testing; `received_date` set | RQ-AR-1..7 |
| **AC-AR-2** | Primary + K additional → 1 sample, 1+K containers, 1+K contents; all same `sample_id`; one txn | RQ-AR-2,3 |
| **AC-AR-3** | Duplicate primary or additional barcode (DB or within request) → 409; zero new rows | RQ-AR-4 |
| **AC-AR-4** | Forced mid-txn failure → zero sample/container/contents/tests from attempt | RQ-AR-2 |
| **AC-AR-5** | UI/API has no sample-name input; name from template | RQ-AR-5 |
| **AC-AR-6** | Request without project / foreign project / client role → 4xx as locked | RQ-AR-7,11 |
| **AC-AR-7** | Empty `analysis_ids` succeeds; non-empty creates Assigned/Pending tests only | RQ-AR-10 |
| **AC-AR-8** | Default tube used; type not required in body | RQ-AR-8 |
| **AC-AR-9** | Body rejects or ignores banned fields (`due_date`, `qc_type`, `client_id`, status, container_type) | RQ-AR-9 |
| **AC-AR-10** | Post-success UX stays on receive (manual UAT) | RQ-AR-12 |

**Pytest minimum (CORE):** AC-AR-1, AC-AR-2, AC-AR-3, AC-AR-4, AC-AR-6, AC-AR-7.  
**UAT minimum (CORE):** HV primary, HV multi-barcode, dup, identity, status, sticky, RBAC — from `UAT_Scripts/uat-atomic-receive.md`. **AR-RES not required for CORE pass.**

---

## 6. Shipped contracts (legacy)

### 6.1 Wizard accession

```http
POST /samples/accession
```

- Creates sample + tests; status forced **Received**; tests often **In Process**  
- Containers often created by **frontend** separate calls (orphan risk)  
- UI: `/accessioning` three-step wizard (`AccessioningForm.tsx`)  
- **Not** CORE happy path  

### 6.2 Bulk accession

```http
POST /samples/bulk-accession
```

- Backend txn: samples + containers + contents + tests  
- May auto-create project (**banned** for atomic receive)  
- Shipped; **not** MVP happy path  

---

## 7. Projects / clients

```text
Client → (ClientProject) → Project → Sample.project_id
```

Access: `project_users` + RLS (`has_project_access`). Atomic receive: project **required sticky**, no per-tube auto-create. Clients refuse.

---

## 8. Field Management

- OOB sample fields in Field Management UI  
- Experiment entries treat accessioning identity as **RO display**  
- Extensibility via FieldDefinitions — **not** new CORE receive body columns  

---

## 9. Cutover (when implementing CORE)

1. Implement `SampleReceiveRequest` + service + route (AuthZ inside service)  
2. New receive page (do not bolt onto wizard forever)  
3. Pytest: AC-AR-1..4, AC-AR-6, AC-AR-7 (include **N≥2** vessels)  
4. Docs sync; UAT: `UAT_Scripts/uat-atomic-receive.md` as receive happy path  
5. Demote wizard UAT as receive SoT; keep bulk as secondary  
6. Dogfood → UAT pass → merge to `main`  

---

## 10. Bounce (spec gate)

Same as PRD §3.3. Implement PRs that violate bounce conditions fail CORE acceptance.

---

## 11. Code index

| Area | Path |
|------|------|
| Sample model | `backend/models/sample.py` |
| Accession / bulk (legacy) | `backend/app/routers/samples.py` |
| Name generation | `backend/app/core/name_generation.py` |
| Wizard UI (legacy) | `frontend/src/pages/AccessioningForm.tsx` |
| AR lists | `backend/db/migrations/versions/0060_atomic_receive_p0_lists.py` |
| Invariants tests | `backend/tests/test_atomic_receive_p0_invariants.py` |
| Sketch | `.docs/review/tech-sketch/atomic-receive.md` |
| Security | `.docs/review/security-review/atomic-receive.md` |
| UAT | `UAT_Scripts/uat-atomic-receive.md` |
