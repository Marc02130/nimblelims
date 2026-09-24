# Implement Brief: UI-driven schema DDL

**Date:** 2026-09-22  
**Stem:** `ui-schema-ddl`  
**Branch:** `docs/ui-schema-ddl`  
**Status:** **Brief written** — OQ-4–13 **Decided** (this fold). Implement gate **OPEN** (Design Group UX Accept Met @ `f79e2a0`; Günter Brief restamp Met). Next: Marc green-light for Grok Build.  
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
| **OQ-2** | Role-based layout registry (role × screen × **membership**). Schema ≠ layout. **No layout hide** — not on layout = not shown. |
| **OQ-3** | Role × table/column privileges (read vs write). Permission **`schema:edit`** separate (not a new role). Not on layout ≠ API allow. |
| **OQ-15** | Known screen keys first; section → fields; default = all **read**-privileged columns; bench vs review separate. **Asked-for and routing leave as is** — not layout/schema-config this packet. |
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

1. Privilege check: permission **`schema:edit`** only (S-UI-1) — admin-assignable; not a new role.  
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
- Barcode ≠ sample ID. Container (vessel synonym) ≠ sample type. Parent = `parent_sample_id`. SOP hints use **sample type** (not matrix).

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
2. **DROP:** permission **`schema:edit`** only; confirm + impact (row count, layout/privilege refs) + audit (**S-UI-6**). No silent DROP of data-bearing objects.

**AC6** cites this section.

---

## 7. OQ-10 — Privilege store

Dedicated **privilege registry** — not columns on the layout table.

| Grain | Values |
|-------|--------|
| `role × table` | Read / Write / none |
| `role × column` | Read / Write / inherit table |

**Default deny:** missing table row = no access. Column inherit = table privilege; a column row can only **narrow**. Enforced in **API/service** (tenant RLS still applies). UI hide is never the gate (**S-UI-3**).

Permission **`schema:edit`** is separate from data Write on Samples (**S-UI-1**) — admin-assignable; small-lab friendly; **not** a new role. Permission **`layout:edit`** cannot CREATE/ALTER and privilege Write must **never** mint **`schema:edit`** (**S-UI-4**).

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
| **S-UI-1** | Permission **`schema:edit`** only for CREATE/ALTER + schema-registry mutate — **not** a new role; admin-assignable; small-lab friendly (**Marc Leadership overwrite 2026-09-23**). **Günter follow-on:** Admin role **defaults** to `schema:edit` + privilege admin (small-startup / no full-time IT) — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later; optional separate role later. |
| **S-UI-2** | FORCE RLS on UI-created / UI-extended relations (OQ-5) |
| **S-UI-3** | Privileges default-deny in the API (OQ-10) |
| **S-UI-4** | Permission **`layout:edit`** ≠ DDL; privilege Write must **never** mint **`schema:edit`** (**Marc overwrite 2026-09-23**) |
| **S-UI-5** | No `lims_app` bypass; revoke schema CREATE from `lims_app` |
| **S-UI-6** | DROP / destructive remove: confirm + impact + audit (OQ-9) |
| **Hans SOP hints** | **matrix removed** from hints — use **sample type**; **vessel = container** synonym; keep barcode ≠ sample ID; container ≠ sample type; parent = `parent_sample_id` (**Marc overwrite**) |
| **Hans Results** | **Confirm stands** — typed Result on a Test stays first-class; do not require a LimsRun for every Result field |
| **Deiter** | **receive / asked-for** = select samples then enter (simple). Must not fight standing Lab Ops locks |
| **Deiter** | **List pages** show role layout columns; on-the-fly add/remove columns is **ephemeral** (not stored in layout) |
| **Deiter** | Layout defines **displayed** columns (absent = not shown); **read/write** = role privileges. **No layout hide** — visibility = membership only (**Marc overwrite 2026-09-23**). Three-mode Hide/Read-only/Deny **retracted**. |
| **Deiter** | **Multi-row** = table with role data-type layout; **single record** = form |
| **Deiter** | Lab Ops consult before a UI-created table gets a **bench runtime screen**. P1 CREATE TABLE may exist without a bench screen. |

---

## 12. Gate status (implement OPEN)

| Gate | Status |
|------|--------|
| This Brief (OQ-4–13) | **Written** this fold |
| Design Group UX Accept on Tables / Columns / Layouts / Privileges | **Met** @ `f79e2a0` (Heidi / Hans / Deiter) |
| Günter restamp that S-UI-1…6 still hold under this Brief | **Met** |

Implement gate **OPEN**. Coding stays Grok Build unless Marc/Rolf asks; wait for **Marc green-light** before code. Tobias UAT uses Fail bars (1)–(5).

---

## 13. Confirms on Marc overwrite (2026-09-23)

| Reviewer | Confirm |
|----------|---------|
| **Günter** | Marc overwrite Confirmed (S-UI-1=`schema:edit`; S-UI-4=`layout:edit`). **Follow-on:** Admin defaults to `schema:edit` + privilege admin — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later; optional separate role later; `layout:edit` still no DDL; S-UI-2/3/5/6 unchanged. Brief-level restamp **Met**. |
| **Hans** | Marc overwrite Confirmed (SOP hints + Results Confirm). |
| **Deiter** | Marc overwrite Confirmed; **retracts** three-mode Hide/Read-only/Deny bench copy. |
| **Marc** | **Confirm closed:** default `schema:edit` + privilege admin = **Admin only** (not lab manager). |

**Rolf Confirm.** Implement gate **OPEN** (Design UX Accept Met @ `f79e2a0`). Next: Marc green-light for Grok Build.

**Marc Confirm (2026-09-23; Rolf):** Default **`schema:edit`** + privilege admin = **Admin only** (not lab manager). **Closed.** Optional re-assign later. Implement CLOSED (at the time; now OPEN).

## Marc Leadership overwrite — layout visibility (2026-09-23; Rolf Confirm)

**No “hidden” on layout.** Visibility = **membership** on the layout only. Do **not** add a hide / Visible toggle that keeps the field on the layout as hidden.

| Case | Rule |
|------|------|
| **Show** | Field is on the role × screen layout. |
| **Not shown** | Field is **not added** to the layout (absent = not shown — Deiter stands). |
| Neither read nor write | Not displayed; layout editor **must not offer** that field. |
| Read yes / Write no | May appear on layout as **read-only** — from **privileges**, not a layout hide. |

Retract any remaining copy that implies a hide mode or three-mode Hide / Read-only / Deny. Implement still **CLOSED** pending Design Group UX Accept (Günter Brief restamp **Met**) (at the time; now OPEN).
**Design Group punch fold 2026-09-23 (Rolf; tip after fold):** UX sketch §6 `schema:edit` (Admin-only); §5/§7 body has list ephemeral + receive/asked-for select-then-enter + multi-row table/single form; §6 “not on layout” (not Layout-hidden). Heidi/Hans/Deiter punches 1 and 4 Met. Awaiting Design Group UX re-stamp (at the time; now OPEN). Implement CLOSED (at the time; now OPEN).

## Marc Leadership overwrite — no Schema-admin role; asked-for/routing leave as is (2026-09-23; Rolf Confirm)

1. **No Schema-admin role.** Copy must say permission **`schema:edit`** on **Admin only** (small-startup; no large IT). Never invent a Schema-admin role. (Design punch 2 / Marc.)
2. **Asked-for and routing leave as is** — not designed for configuration. Do **not** make asked-for or routing layout/schema-config surfaces this packet. Deiter “select then enter” for **receive** may stay as a Lab Ops runtime note where it already applies; do **not** redesign asked-for/routing for OQ-2 layouts.
3. Still required: ephemeral list columns; multi-row = table / single = form; “not on layout” (never layout-hidden); `schema:edit` Admin-only.

Implement **CLOSED** (at the time; now OPEN). Design Group re-stamps after tip (at the time; now OPEN).
**UI Sketch Accept re-stamp (Mathilda; 2026-09-23):** Verified on tip `f79e2a0` — `schema:edit` Admin-only (no Schema-admin role); asked-for/routing leave as is; ephemeral list cols; multi-row table / single form; not on layout (membership only). Design Group UX Accept still pending on that tip (at the time; now OPEN). Implement CLOSED (at the time; now OPEN).

## Implement gate OPEN (2026-09-23; Rolf)

| Gate | Status |
|------|--------|
| Design Group UX Accept | **Met** on tip `f79e2a0` (Heidi / Hans / Deiter) |
| Günter Brief restamp | **Met** |
| Implement gate | **OPEN** |

Tobias **re-UAT Pass** on `b6d1920` (0081). Rolf Confirm **Met**. Merge = Marc’s call — no merge until Marc says.

## Product branch + UAT (2026-09-23; Rolf / Marc)

| Item | Cite |
|------|------|
| Product / dogfood / UAT branch | `feat/ui-schema-ddl` |
| Product tip (Grok Build landed) | `8c14a84` |
| Product tip passed | `b6d1920` |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` on that branch |
| Docs living tip (implement OPEN) | `912c1a2` on `docs/ui-schema-ddl` |

Tobias owns UAT Pass/Fail against Fail bars (1)–(5). **No invent Pass.** No merge until Rolf Confirm + Marc.

## Tobias UAT Fail on 8c14a84 (history — superseded by re-UAT Pass on b6d1920)

| Item | Cite |
|------|------|
| Product tip UAT’d | `8c14a84` on `feat/ui-schema-ddl` |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` |
| Evidence | `/workspace/uat-ui-schema-ddl-8c14a84/` |
| Overall | **Fail** — no invent Pass; **no merge** |

### Section stamps (Tobias)

| § | Result |
|---|--------|
| 1 Surfaces | **Pass** |
| 2 CREATE TABLE | **Fail** — 500 `UiSchemaDdlLog.seq` NotNullViolation |
| 3 ADD COLUMN | **Fail** — 422 `schema_apply` ≠ samples owner |
| 4 schema:edit | **Pass** (lab-tech 403) |
| 5 Layout membership | **Pass** |
| 6 Privileges | **Fail** (403 not proven; blocked by §3) |
| 7 Deprecate/DROP | **Fail** |
| 8 JSONB-as-config | **Pass** |

### Fail bars

| Bar | Result |
|-----|--------|
| (1) privilege refuse write | **not scored** |
| (2) privilege refuse read | **not scored** |
| (3) schema:edit only for DDL | **Met** |
| (4) real Postgres proof | **Fail** on API |
| (5) JSONB-as-config | **Met** |

### Blockers (Marc green-lit Grok Build fix)

| ID | Blocker |
|----|---------|
| **A** | `UiSchemaDdlLog.seq` ORM NULL → CREATE TABLE **500** |
| **B** | `schema_apply` cannot ALTER `samples` → ADD COLUMN **422** |

**Status:** Grok Build fixed A+B on `b6d1920`; re-UAT Pass — see next section.

## Tobias re-UAT Pass + Rolf Confirm (2026-09-23)

| Item | Cite |
|------|------|
| Product tip | `b6d1920` on `feat/ui-schema-ddl` (alembic **0081**) |
| Prior Fail tip | `8c14a84` — Fail history stands; A+B fixed |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` |
| Evidence | `/workspace/uat-ui-schema-ddl-b6d1920/` |
| Overall | **Pass** |
| Rolf Confirm | **Met** |
| Merge | **Marc’s call** — no merge until Marc says |

### Section stamps

| § | Result | Tip |
|---|--------|-----|
| 1 Surfaces | **Pass** | `8c14a84` (stands) |
| 2 CREATE TABLE | **Pass** | `b6d1920` |
| 3 ADD COLUMN | **Pass** | `b6d1920` |
| 4 schema:edit | **Pass** | `8c14a84` (stands) |
| 5 Layout membership | **Pass** | `8c14a84` (stands) |
| 6 Privileges | **Pass** | `b6d1920` |
| 7 Deprecate/DROP | **Pass** | `b6d1920` |
| 8 JSONB-as-config | **Pass** | `8c14a84` (stands) |

### Fail bars

| Bar | Result |
|-----|--------|
| (1) privilege refuse write | **Met** (`b6d1920`) |
| (2) privilege refuse read | **Met** (`b6d1920`) |
| (3) schema:edit only for DDL | **Met** (`8c14a84`) |
| (4) real Postgres proof | **Met** (`b6d1920`) |
| (5) JSONB-as-config | **Met** (`8c14a84`) |

Blockers A (`UiSchemaDdlLog.seq`) and B (`schema_apply` ALTER `samples`) **cleared** on `b6d1920`. Compose down. Not IC50.

