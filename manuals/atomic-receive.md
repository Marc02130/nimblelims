# Manual: Atomic receive (OOB / CORE)

**Status:** **CORE shipped + UAT Pass** (2026-08-27) — on `main` (`ebac94e` feature merge; UAT stamp `618fbbf`)  
**UI:** `/receive` — sidebar **Receive** (`frontend/src/pages/AtomicReceive.tsx`)  
**API:** `POST /samples/receive` (`backend/app/services/atomic_receive_service.py`)  
**UAT:** [`UAT_Scripts/uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md) · run report [`UAT_Scripts/atomic-receive/uat-run-2026-08-27.md`](../UAT_Scripts/atomic-receive/uat-run-2026-08-27.md)  
**Requirements:** `.docs/internal/prd/sample-accessioning/PRD.md` (RQ-AR-*) · SPEC §3  
**Sketch:** `.docs/review/tech-sketch/atomic-receive.md`

**After CORE (P1, not on this screen):** record **requested analysis** on **Asked-for** (`/asked-for`). See [asked-for.md](asked-for.md). Asked-for does **not** mint Tests or start work. Route / work_orders / WO-7 stay **out** of the P1 stamp. Results-entry persist lock remains a later packet (**NR-AR-1** / AR-RES).

The legacy `/accessioning` wizard is **removed**. `/accessioning` redirects to `/receive`.

---

## Purpose

High-volume intake: register specimen identity + **1..N vessels** in **one transaction**. Lab sample ID is system-assigned. Tube barcode is the vessel. Status on commit is **Available for Testing**. Requested analysis, work orders, and results entry are **out of receive**. After receive, analysts record requested analysis on **Asked-for** ([asked-for.md](asked-for.md)) — that still creates **zero Tests**.

Legacy wizard at `/accessioning` is **gone** (redirects here). See [accessioning-workflow.md](accessioning-workflow.md).

---

## Who

| Role | Access |
|------|--------|
| Lab tech / manager with `sample:create` | Receive UI + API |
| Client | No receive (403 / no nav) |
| Users without project access | Foreign project → 403 |

---

## UI loop (`/receive`)

1. Set sticky **sample type**, **project**, **container type** (session-sticky).  
2. Scan / type **primary barcode** (required).  
3. Optionally **Add** additional barcodes for the **same sample** (not aliquot). Extra barcodes = more tubes of **that** sample.  
4. Optional temperature / client sample ID.
5. **Receive** → toast → barcodes clear → sticky fields remain → focus primary.
6. Stay on the page for the next specimen.

**Container type:** required; **1×1 vessels only** (`rows=1` and `columns=1`). Plates / multi-well are hidden in the UI and refused by the API. Same type applies to all vessels on the commit.

**Not on the form:** sample ID, status, **analysis picker**, aliquot dialog, redirect to sample detail. OOB receive never offers analyses and never sends `analysis_ids`.

---

## API contract

```http
POST /samples/receive
```

```json
{
  "container_barcode": "NBIO-AR-0001",
  "additional_container_barcodes": ["NBIO-AR-0001B"],
  "sample_type": "<uuid>",
  "project_id": "<uuid>",
  "container_type_id": "<1x1 container type uuid>",
  "temperature": null,
  "client_sample_id": null
}
```

**Forbidden body fields (422):** `name`, `status`, `matrix`, `due_date`, `qc_type`, `client_id`, …  
**Required:** `sample_type`, `project_id`, `container_type_id` (1×1 only; plates → **400**).  
**Matrix:** dropped from intake (`samples.matrix` nullable; not set on receive).  
If `analysis_ids` is present and **non-empty** → **422**. Do not ignore. Do not mint Tests. Empty/omitted is the only accepted path; still zero Tests.

**`analysis_ids` (WO-7):** omit the field or send `[]`. Non-empty → **422**. Refuse, do not ignore, do not mint Tests.

**Server (one txn):**

1. AuthZ = sample create + project access/RLS (PR 68)  
2. Validate `container_type_id` is active **1×1** (refuse plates / multi-well)  
3. System `samples.name` via name template  
4. Sample status → Available for Testing; set `received_date`  
5. For each barcode → Container (`type_id` = sticky type) + Contents → same sample  
6. Return `tests: []`; CORE never inserts Test or Result rows

**Errors:** duplicate barcode → **409** (full rollback); missing required → **422**; non-empty `analysis_ids` → **422** before receive writes; no project access / client → **403**.

**Response (minimum):** `sample_id`, `sample_name`, `status`, `project_id`, `containers[]`, `tests[]`.

---

## Identities

| Identity | Field | Rule |
|----------|--------|------|
| Vessel | `containers.name` | Scanned barcode; unique; 409 on collision |
| Material | `samples.name` | System template; tech does not type it |

---

## Tests and requested analysis

- CORE receive creates **zero Tests** and **zero Results**.
- Happy-path body: **no** `analysis_ids` (or empty only). Non-empty → **422** before the receive transaction. UI never sends it.
- CORE never ignores, stores, or converts requested analyses into Tests. `analysis_param_defs` are **not** collected on receive (later: LimsRun start).
- **A-15 / asked-for** is the P1 lake on `/asked-for` ([asked-for.md](asked-for.md)), **not** on `/receive`. Do not add Tests from receive. Classic `/tests` still exists for typing a number on an existing Test; it is **not** the request path.
- `DELETE /tests/{id}` → **400** if results exist (A-14).

---

## Related docs

- API index: [api-endpoints.md](api-endpoints.md)  
- Containers: [containers.md](containers.md)  
- Legacy wizard: [accessioning-workflow.md](accessioning-workflow.md)  
- Asked-for (after receive): [asked-for.md](asked-for.md)  
- Navigation: [navigation.md](navigation.md)  
