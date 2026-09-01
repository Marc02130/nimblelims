# Spec: Post-receive work spine

**PRD:** [../../prd/post-receive-work-spine/PRD.md](../../prd/post-receive-work-spine/PRD.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../../../review/requirements/post-receive-work-spine.md)  
**Sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../../../review/tech-sketch/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../../../review/schema-changes/post-receive-work-spine.md)  
**Date:** 2026-08-28

Contracts. Product rules live in requirements. Do not fork a second execute API.

---

## P1 — Asked-for

### HTTP

```
POST   /api/v1/asked-for
GET    /api/v1/asked-for?sample_id=&project_id=&analysis_id=&status=
GET    /api/v1/asked-for/{id}
POST   /api/v1/asked-for/{id}/cancel
GET    /api/v1/analyses/{id}/param-defs
PUT    /api/v1/analyses/{id}/param-defs    # config:edit
```

### POST body

```json
{
  "sample_id": "<uuid>",
  "analysis_id": "<uuid>",
  "tat_days": 5,
  "params": { "cell_line": "A549", "incubation_h": 48 }
}
```

`params` keys must match `GET /analyses/{id}/param-defs`. Empty `{}` if that analysis has no defs. Example freeze objects (not seed): [`.docs/decision-logs/2026-08-28-analysis-param-defs.md`](../../../decision-logs/2026-08-28-analysis-param-defs.md) §3.

**P2 (not P1):** LimsRun start copies `asked_for.params` → `tests.asked_for_params` and freezes.

201: asked-for row, `status=requested`, `tests` not present.  
409: open row already exists for `(sample_id, analysis_id)`.  
403: no project access or missing `test:assign`.  
422: bad TAT, unknown param key, required param missing.

### AuthZ / RLS

Same project RLS as `tests` via `sample_id`. `test:assign` on write. `sample:read` on list/get. Client: read-only if they can read the sample.

### UI

- Route `/asked-for` (permission `test:assign` to create; `sample:read` to view)
- Sample detail: Asked-for table + add
- **Not** on `/receive`

---

## P2 — Routing + work_order

### HTTP

```
GET/POST/PATCH/DELETE /api/v1/routing-map          # config:edit mutate
POST /api/v1/asked-for/{id}/route                  # tech hits Route; mint WO if map matches (never on create)
GET  /api/v1/work-orders
POST /api/v1/work-orders/{id}/start                # instantiate first process (existing process AuthZ)
```

### Routing row

`(analysis_id, sample_type_id, tat_days_min, tat_days_max inclusive, process_definition_ids[])`

Overlap detect: same analysis+sample_type, ranges intersect → 409.

Match: sample.sample_type + asked-for.analysis_id + asked-for.tat_days inside range. Zero matches → 200 with `work_order: null` and `reason: no_route`. Multiple matches are impossible if overlap refuse holds.

### work_order row

Snapshot `process_definition_ids` at mint time. Later map edits do not mutate in-flight WOs.

Start: call existing process instantiate; set WO `in_progress`. Test still not created.

LimsRun start (existing): create/attach Test (WO-7); set `tests.asked_for_params` from the asked-for row (freeze). Publish: 422 if Test missing.

---

## P3 — Results persist

Existing `POST /tests/{id}/results` (or current results path):

- Typed token → `reported_result` (string as typed; no float roundtrip)
- `raw_result` optional copy
- `qualifiers` = existing UUID FK to Result Qualifiers list, or NULL
- Unit from `analytes.units_default`; null → 422 for numeric quantities
- No `unit_id` column
- Conflict with LimsRun-owned Test → 409

---

## P4 — SOP Apply

Existing SOP parse job:

- Apply success path: insert `eln_process_definitions` + `_definition_steps` (kinds from parse). Optionally still write ExperimentTemplate if a step needs it.
- Response includes `process_definition_id`. Draft `active=false` until user activates (existing process def activation if any; else explicit activate).
- Optional inactive parser draft; never auto-bind to production runs.

---

## P5 — Parser setup UI

Existing tables (`instruments`, `instrument_types`, `cro_sources`, `data_parsers`, `parser_analyses`). This phase is **admin UX + dry-run + activate**, not a new import engine.

`config:edit` only for mutate. Lab client users: no.

---

## Errors (shared)

| Code | When |
|------|------|
| 403 | RLS / missing perm |
| 409 | duplicate asked-for; TAT overlap; two writers on Test |
| 422 | params, missing units_default, publish without Test, Qubit-on-blood route |
| 404 | unknown ids (do not leak cross-project as 404 when RLS-hidden — **403** like receive close-out) |
