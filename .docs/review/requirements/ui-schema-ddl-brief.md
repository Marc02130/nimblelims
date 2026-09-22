# Implement Brief: UI-driven schema DDL

**Date:** 2026-09-22  
**Stem:** `ui-schema-ddl`  
**Branch:** `docs/ui-schema-ddl`  
**Status:** **Brief written** — OQ-4–13 **Decided** (this fold). Implement gate still **CLOSED** until Design Group UX Accept + Günter restamp.  
**Requirements:** [ui-schema-ddl.md](ui-schema-ddl.md)  
**Open questions:** [../open-questions/ui-schema-ddl.md](../open-questions/ui-schema-ddl.md)  
**UI sketch:** [../ui-review/ui-schema-ddl.md](../ui-review/ui-schema-ddl.md) (Mathilda Sketch Accept @ `e12b0c2` — not Design Group UX Accept)  
**Not IC50. No product code in this fold.**

This Brief closes the pre-implement blockers named by Leadership / Grok Bot: OQ-4–13 plus Günter S-UI-1…6, Hans punches, and Deiter conditions. Method stays **Brief → (Design UX + Günter restamp) → code → UAT → stamp → merge**.

---

## 0. Already decided (do not reopen)

| ID | Lock |
|----|------|
| **OQ-1** | Table registry + column registry. Physical CREATE/ALTER is real Postgres. `information_schema` alone is not enough. Indexes/FKs wait. |
| **OQ-2** | Role-based layout registry (role × screen × visible columns/sections). Schema ≠ layout. |
| **OQ-3** | Role × table/column privileges (read vs write). schema-admin separate. Layout hide ≠ API allow. |
| **OQ-15** | Known screen keys first; section → fields; default = all **read**-privileged columns; bench vs review separate. |
| **OQ-16** | JSONB = payload **data** only. Never config. |
| Surfaces | Admin → Schema: **Tables**, **Columns**, **Layouts**, **Privileges**. |
| Tobias Fail bars | (1)–(5) locked 2026-09-22. |

**Parked:** AI apply DDL; AI login/reporting/storage; Indexes/FKs UI; DBA SQL console; OQ-14 AI metadata.

---

## 1. OQ-4 — Apply model → **Hybrid**

Lab HTTP stays on `lims_app` with RLS on. `lims_app` **must not** `CREATE`/`ALTER` (today it has `GRANT CREATE ON SCHEMA public` — **revoke** that; S-UI-5).

Physical DDL runs as a dedicated **schema-apply** role (or a `SECURITY DEFINER` function owned by that role) that may execute **only** allow-listed ops:

- `CREATE TABLE` with the OQ-7 platform set + FORCE RLS
- `ALTER TABLE … ADD COLUMN` of an OQ-8 type on an OQ-6 allow-listed table
- Deprecate / controlled DROP (OQ-9)

That role **must not** `SELECT` lab rows, **must not** `DROP DATABASE`, **must not** take arbitrary SQL from the UI.

**One controlled operation:**

1. Privilege check: **schema-admin** only (S-UI-1).  
2. Write registry row(s) + `schema_changes` audit (who / when / what / before / after).  
3. Call schema-apply for the physical DDL.  
4. Persist a **replayable upgrade artifact** (generated Alembic revision on a **second head** `ui_schema`, or an equivalent versioned DDL log that migrate-on-boot replays).  

Fail any step → roll back the registry write. No half-applied column.

**Bounce:** runtime DDL as superuser; “wait for a deploy” as the only apply path.

**AC5 / AC0b / AC8** cite this section.

---

## 2. OQ-5 — Tenant isolation → **Shared schema + FORCE RLS**

Do **not** per-tenant schemas (fights every existing table and `has_project_access`).

Every UI-created table, and every core table that receives a UI column:

- `ENABLE ROW LEVEL SECURITY`
- **`FORCE ROW LEVEL SECURITY`** (same pattern as `0073`)
- Policy keys off `client_id` (OQ-7)

Table / column / layout / privilege **registry rows** are tenant-scoped (`client_id`) in P1. No global catalog rows this packet. Client A never reads Client B catalogs or data.

**S-UI-2 Met** by this lock. **AC4** cites this section.

---

## 3. OQ-6 — Allow-list (P1)

**ADD COLUMN** allowed on:

- `samples` — **non-identity** columns only
- UI-created tables (`x_*` / `lab_*`)

**ADD COLUMN out of P1:** `asked_for` freeze payload, `tests` / `results` identity, `containers` / `contents` identity, `eln_*` process join, `routing_map` / `work_orders`.

**Never UI-droppable or rename-destructive (Hans):**

- `samples.name`, `parent_sample_id`, `sample_type`, `status`, `matrix`, `project_id`, `client_sample_id`
- Container `name`, `type_id`
- Asked-for **freeze params** / freeze payload (identity of what was ordered — not UI-droppable even though ADD COLUMN on `asked_for` is already out of P1)
- Barcode ≠ sample ID (Katinka). Vessel type ≠ matrix / sample type.

**CREATE TABLE:** new lab entities only. Display name → physical slug `x_<slug>` (or `lab_<slug>`). Never a second Samples table.

**AC9 / AC1** cite this section.

---

## 4. OQ-7 — Platform columns on CREATE TABLE

Fixed checklist (UI shows it; not free-add):

| Column | Rule |
|--------|------|
| `id` | UUID PK |
| `client_id` | NOT NULL FK `clients` — tenant key |
| `created_at` / `created_by` | audit |
| `modified_at` / `modified_by` | audit |
| `active` | boolean, default true (soft-delete) |

Then FORCE RLS (OQ-5). Bounce CREATE without this set. **AC2** cites this section.

---

## 5. OQ-8 — P1 type enum

| UI label | Postgres |
|----------|----------|
| Text | `text` |
| Number | `numeric` |
| Whole number | `integer` |
| Yes/No | `boolean` |
| Date | `date` |
| Date and time | `timestamptz` |
| List | `uuid` FK → `list_entries.id` |

JSONB is allowed **only** as a **data** column type for instrument/payload blobs (**OQ-16**). Never offered as “add a config field.” **No** quantity+unit compound type (Hans). **AC1** cites this section.

---

## 6. OQ-9 — Deprecate vs DROP

1. **Deprecate:** registry `status=deprecated`; hide from new layouts; data retained; existing queries still work. Default science-safe path.  
2. **DROP:** **schema-admin** only; confirm + impact (row count, layout/privilege refs) + audit (**S-UI-6**). No silent DROP of data-bearing objects.

**AC6** cites this section.

---

## 7. OQ-10 — Privilege store

Dedicated **privilege registry** — not columns on the layout table.

| Grain | Values |
|-------|--------|
| `role × table` | Read / Write / none |
| `role × column` | Read / Write / inherit table |

**Default deny:** missing table row = no access. Column inherit = table privilege; a column row can only **narrow**. Enforced in **API/service** (tenant RLS still applies). UI hide is never the gate (**S-UI-3**).

**schema-admin** is a separate permission, not “Write on Samples” (**S-UI-1**). **layout-admin** cannot CREATE/ALTER and cannot mint schema-admin by writing privileges (**S-UI-4**).

**AC0d / AC7** cite this section.

---

## 8. OQ-11 — Alembic collision

| Trail | Owns |
|-------|------|
| Core `alembic_version` | Grok Build migrations only. Must **not** `DROP` UI columns/tables they do not own. |
| `ui_schema` head (or versioned DDL log) | UI-created tables/columns + registry rows. Names `x_*` / `lab_*`. |

Boot: apply core Alembic, then replay the UI trail. Collision → **fail closed**, not silent rename. **AC5** cites this section.

---

## 9. OQ-12 — FieldDefinitions / Entries

**Leave Entries alone this packet.** Experiment `FieldDefinitions` stay entry columns. Do not promote them to Sample columns. Do not blur with aliquot/pool dest FDs (that is **E-11**, a different packet).

---

## 10. OQ-13 — `custom_attributes`

**Follow-on.** P1 does not dual-read JSONB keys as schema and does not hard-cutover. Bounce any UI path that writes a JSONB key and calls it a column (**OQ-16**). Existing `samples.custom_attributes` stays until a later packet.

---

## 11. Leadership conditions (baked in; do not reopen)

| Source | Lock |
|--------|------|
| **S-UI-1** | Only **schema-admin** CREATE/ALTER + schema-registry mutate |
| **S-UI-2** | FORCE RLS on UI-created / UI-extended relations (OQ-5) |
| **S-UI-3** | Privileges default-deny in the API (OQ-10) |
| **S-UI-4** | layout-admin ≠ DDL; privilege write must not mint schema-admin |
| **S-UI-5** | No `lims_app` bypass; revoke schema CREATE from `lims_app` |
| **S-UI-6** | DROP / destructive remove: confirm + impact + audit (OQ-9) |
| **Hans SOP hints** | barcode ≠ sample ID; vessel ≠ matrix/sample type; parent = `parent_sample_id` |
| **Hans Results** | Typed Result on a Test stays first-class; do not require a LimsRun for every Result field |
| **Deiter** | Layout Apply on receive / asked-for / `samples.*` must not reintroduce one-hop or fight standing Lab Ops locks |
| **Deiter** | Hide vs Read-only vs Deny copy — layout hide ≠ privilege deny |
| **Deiter** | Lab Ops consult before a UI-created table gets a **bench runtime screen**. P1 CREATE TABLE may exist without a bench screen. |

---

## 12. Still waiting (implement stays CLOSED)

| Gate | Status |
|------|--------|
| This Brief (OQ-4–13) | **Written** this fold |
| Design Group UX Accept on Tables / Columns / Layouts / Privileges | **Pending** — Mathilda Sketch Accept is not this stamp |
| Günter restamp that S-UI-1…6 still hold under this Brief | **Pending** |

After both stamps: implement gate **OPEN**. Coding stays Grok Build unless Marc/Rolf asks. Tobias UAT uses Fail bars (1)–(5). Signed reviews (Lab Ops / Science / CSO / UI sketch) got **fold notes** only — this Brief does **not** invent Design UX Accept or a Günter restamp.
