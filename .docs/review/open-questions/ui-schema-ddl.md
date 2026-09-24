# Open questions: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** OQ-1/2/3/15/16 **Decided**; **OQ-4–13 Decided** in [Brief](../requirements/ui-schema-ddl-brief.md). Design Group UX Accept **Met** @ `f79e2a0`. Günter Brief restamp **Met**. Implement gate **OPEN**. Next: Marc green-light for Grok Build. Packet `ui-schema-ddl`  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**Leadership:** Core pivot 2026-09-22 — CREATE TABLE / ADD COLUMN via UI as real Postgres; tenant-safe, migratable, reversible; role-based layout; role-based table/column access.  
**Owners:** Heidi (architecture), Mathilda (UX / layout), Günter (authZ), Tobias (UAT Fail bars), Wilhelmina (docs), Katinka (SOP field-name hints).  
**Not IC50. No product code until sketch + Accept.**

## Context

Sample-processing critical path is Met on `main`. AI config needs a **robust configuration layer**. Leadership locked: admins add **tables and columns through the UI as real database objects**, not JSONB — plus **layout** (what UI shows) and **access** (what API allows), which are **not** the same.

## Decided

| ID | Decision | Stamp | Date |
|----|----------|-------|------|
| **OQ-1** | **Catalog minimum = two schema registries:** (1) **table registry**; (2) **column registry** (name, type, nullability, order, display defaults, tenant rules, **AI/SOP field-name hints**). Catalogs **describe** configurable real Postgres objects; they are **not** lab data. **`information_schema` alone is not enough**. Physical **CREATE / ALTER … ADD COLUMN** still hits real DB. **Indexes / FKs wait**. Heidi Accept before implement. | Marc + **Rolf Confirm** | 2026-09-22 |
| **OQ-2** | **Role-based layout registry** (separate): **role × screen × membership**. Schema = what exists; layout = who **sees** what where (**on layout** = show; **not on layout** = not shown — **no hide toggle**). Do not bury layout only in the column registry. Mathilda centerpiece. | Marc + **Rolf Confirm**; overwrite 2026-09-23 | 2026-09-23 |
| **OQ-3** | **Role-based access** to tables and columns — **not** the same as layout. Access = what the **API allows** (at least **read vs write** per role on table and column; permission **`schema:edit`** separate — not a new role). A field may be **off the layout** yet still write-forbidden; or on the layout as **read-only** (from privileges). Tobias: Fail bars for **privilege refuse** vs **not on layout**. **No layout hide.** | Marc + **Rolf Confirm**; overwrite 2026-09-23 |
| **OQ-15** | **Layout grain:** known product screen keys first; section → fields; default when no layout = all **read**-privileged columns in registry order; bench vs review separate layouts; layout read-only chrome ≠ API write. Four surfaces: Tables / Columns / Layouts / Privileges. | Mathilda Sketch Accept @ `e12b0c2` | 2026-09-22 |
| **OQ-16** | **JSONB = payload data only** (instrument results / similar blobs). **Not** for system configuration — schema, layout, privileges, and other config live in **real tables/columns** (registries + DDL). Bounce JSONB-as-config. | Marc + **Rolf Confirm** | 2026-09-22 |
| **OQ-4** | **Apply model = Hybrid.** Lab HTTP on `lims_app` (no DDL). Physical DDL via schema-apply role / allow-listed function. Registry + audit + DDL one op. Replay via `ui_schema` Alembic head (or DDL log). Revoke `CREATE` on `public` from `lims_app` (S-UI-5). | Brief 2026-09-22 | 2026-09-22 |
| **OQ-5** | **Shared schema + FORCE RLS.** No per-tenant schemas. UI-created/extended tables ENABLE+FORCE RLS on `client_id`. Registries tenant-scoped in P1. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-6** | **ADD COLUMN** P1: `samples` (non-identity) + UI-created tables. Protect identity/lineage (name, parent_sample_id, sample_type, status, matrix, project_id, client_sample_id; container name/type; asked-for freeze params). CREATE TABLE = new `x_*`/`lab_*` entities only. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-7** | Platform columns: `id` UUID PK, `client_id` NOT NULL, created/modified at/by, `active`. Then FORCE RLS. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-8** | P1 types: text, numeric, integer, boolean, date, timestamptz, list→`list_entries`. JSONB data-only (OQ-16). No quantity+unit. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-9** | Deprecate first (retain data). DROP = permission **`schema:edit`** + confirm + impact + audit (S-UI-6). | Brief 2026-09-22 | 2026-09-22 |
| **OQ-10** | Dedicated privilege registry. role×table Read/Write/none; role×column Read/Write/inherit. Default deny. API-enforced. **`schema:edit`** ≠ Write on Samples. **`layout:edit`** ≠ DDL; privilege Write never mints **`schema:edit`**. | Brief + Marc overwrite 2026-09-23 | 2026-09-23 |
| **OQ-11** | Core Alembic owns Grok Build only. UI objects on `ui_schema` head / DDL log; prefix `x_`/`lab_`. Boot: core then UI trail. Collision fail closed. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-12** | **Leave Entries alone.** FieldDefinitions stay entry columns. No promote. No mint blur with E-11 dest FDs. | Brief 2026-09-22 | 2026-09-22 |
| **OQ-13** | **`custom_attributes` follow-on.** No dual-read-as-schema. No hard cutover P1. Bounce JSONB-as-column. | Brief 2026-09-22 | 2026-09-22 |

### OQ-1 AI hints (Katinka)

Keep **public SOP field names** on the column registry. **Marc overwrite 2026-09-23:** **matrix removed** — use **sample type**; **vessel = container** synonym; keep barcode ≠ sample ID; container ≠ sample type; parent = `parent_sample_id`. **No house SOP text in git.** Layout (OQ-2) separates bench tech vs review roles.

## Blocking questions

OQ-4–13 are **Decided** in the [Brief](../requirements/ui-schema-ddl-brief.md) — see Decided table above. Remaining **non-blocking**:

| ID | Question | Status | Owner |
|----|----------|--------|-------|
| OQ-14 | **AI metadata:** read table + column + layout + privilege descriptors? | **Parked** (non-blocking). Not login/reporting/storage AI. | Heidi + Wilhelmina |

## Non-blocking / park

| ID | Note |
|----|------|
| AI apply DDL | Parked |
| JSONB for instrument/payload **data** | **Allowed** (OQ-16) — not a config store |
| JSONB-as-config | **Bounce** (OQ-16) |
| AI login / reporting / storage | Parked — [`ai-config-breadth.md`](ai-config-breadth.md) |
| Indexes / FKs P1 | **Wait** |
| DBA-style DDL editor | **Bounce** (Mathilda) |
| Full low-code builder | Out of scope |

## UAT note (Tobias) — Fail bars locked 2026-09-22

1. No-privilege write → **403/422**, not silent drop; layout-hide ≠ API allow.  
2. Privilege-denied read → **refuse**, not empty-as-layout.  
3. Permission **`schema:edit`** only for CREATE/ALTER; lab role without it cannot DDL.  
4. CREATE/ALTER proves real Postgres (`information_schema` / query), not JSONB-as-config.  
5. **OQ-16:** any **config** path (schema / layout / privileges / catalog) that writes **JSONB instead of** DDL or catalog rows → **Fail**. JSONB remains OK for instrument/payload **data** columns.

Plus catalog uniqueness / tenant isolation; role×layout visibility. UAT packet after Design UX stamp + Heidi conditions addressed.

## Architecture Accept (Heidi)

**Accept with conditions** (2026-09-22; restamp cited @ tip `c6f0854`). Conditions **were** remaining **OQ-4–13** — now **Decided** in the [Brief](../requirements/ui-schema-ddl-brief.md). Original stamp stands (this fold does not invent a Heidi restamp). **OQ-16 Confirm** (JSONB = payload data only; not config). UI sketch: [ui-review/ui-schema-ddl.md](../ui-review/ui-schema-ddl.md) @ `e12b0c2`.

## Science Accept (Hans)

**Accept with conditions** (2026-09-22). Punches:

1. **SOP hint grains** — public field-name grain; **matrix out / sample type in**; vessel=container; barcode ≠ sample ID; container ≠ sample type; parent=`parent_sample_id` (Marc overwrite).  
2. **OQ-9 deprecate** — science-safe deprecate/remove path before destructive DROP of data-bearing fields.  
3. **OQ-6 identity protect** — allow-list must protect identity / lineage fields from casual UI overwrite.  
4. **Classic Results first-class** — do not replace structured Results with opaque JSONB config; JSONB payloads are data (OQ-16), not a Results substitute.  
5. **No quantity+unit** compound type this packet — prefer separate amount/unit (or existing Result patterns).

## Lab Ops Accept (Deiter)

**Accept with conditions** (2026-09-22, cited @ tip `c6f0854`):

1. Implement stays **CLOSED** until **OQ-4–11** addressed + **Günter** Accept + **Brief**.  
2. **Layout Apply** must not fight living **receive / asked-for** locks — **select samples then enter** (simple).  
3. Layout = **membership** only (absent = not shown); **no layout hide**. R/W = privileges (read-only from Write=no). Three-mode Hide/Read-only/Deny **retracted**. **Marc overwrite 2026-09-23**.  
4. **Lab Ops consult** before a new UI-created table gets a **runtime** screen.  
5. **List pages:** role layout columns; on-the-fly add/remove is **ephemeral** (not stored).  
6. **Multi-row** = table + role data-type layout; **single record** = form.

## CSO Accept (Günter)

**Accept with conditions** (2026-09-22, cited @ tip `c6f0854`) — **S-UI-1…6**:

| ID | Condition |
|----|-----------|
| **S-UI-1** | Permission **`schema:edit`** only for CREATE/ALTER (and schema registry mutate) — not a new role; admin-assignable. **Günter follow-on:** Admin defaults to `schema:edit` + privilege admin — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later; optional separate role later |
| **S-UI-2** | **FORCE RLS** on UI-created / UI-extended relations |
| **S-UI-3** | Privileges **default-deny** in the API (not UI-only) |
| **S-UI-4** | Permission **`layout:edit`** ≠ DDL; privilege Write never mints **`schema:edit`** |
| **S-UI-5** | No **`lims_app` bypass** of RLS / privilege checks |
| **S-UI-6** | **DROP** (or destructive remove) requires confirm + audit |

## Waiting

- **Brief** — **written** 2026-09-22 ([ui-schema-ddl-brief.md](../requirements/ui-schema-ddl-brief.md)); OQ-4–13 Decided  
- **Design Group UX Accept** on Tables / Columns / Layouts / Privileges — pending (Mathilda Sketch Accept is not this stamp)  
- **Günter restamp** that S-UI-1…6 still hold under the Brief — **Met**  
- Implement gate **OPEN** (Design Group UX Accept Met @ `f79e2a0`)  

## Unpark / decide rule

Brief written. Design Group UX Accept **Met** @ `f79e2a0`. Günter Brief restamp **Met**. Implement **OPEN**. No product code until **Marc green-light** for Grok Build.

## Marc Leadership overwrite (2026-09-23)

**Rolf Confirm.** S-UI-1=`schema:edit`; S-UI-4=`layout:edit`; Hans SOP hints + Results Confirm; Deiter layout display locks (5)–(7). Implement CLOSED.

**Confirms 2026-09-23 (Rolf):** Günter + Hans + Deiter Confirmed Marc overwrite. Deiter **retracts** three-mode Hide/Read-only/Deny copy. Implement CLOSED.

**Marc Confirm (2026-09-23; Rolf):** Default **`schema:edit`** + privilege admin = **Admin only** (not lab manager). **Closed.** Optional re-assign later. Implement CLOSED.

## Marc Leadership overwrite — layout visibility (2026-09-23; Rolf Confirm)

**No “hidden” on layout.** Visibility = **membership** on the layout only. Do **not** add a hide / Visible toggle that keeps the field on the layout as hidden.

| Case | Rule |
|------|------|
| **Show** | Field is on the role × screen layout. |
| **Not shown** | Field is **not added** to the layout (absent = not shown — Deiter stands). |
| Neither read nor write | Not displayed; layout editor **must not offer** that field. |
| Read yes / Write no | May appear on layout as **read-only** — from **privileges**, not a layout hide. |

Retract any remaining copy that implies a hide mode or three-mode Hide / Read-only / Deny. Implement still **CLOSED** pending Design Group UX Accept (Günter Brief restamp **Met**).

## Marc Leadership overwrite — no Schema-admin role; asked-for/routing leave as is (2026-09-23; Rolf Confirm)

1. **No Schema-admin role.** Copy must say permission **`schema:edit`** on **Admin only** (small-startup; no large IT). Never invent a Schema-admin role. (Design punch 2 / Marc.)
2. **Asked-for and routing leave as is** — not designed for configuration. Do **not** make asked-for or routing layout/schema-config surfaces this packet. Deiter “select then enter” for **receive** may stay as a Lab Ops runtime note where it already applies; do **not** redesign asked-for/routing for OQ-2 layouts.
3. Still required: ephemeral list columns; multi-row = table / single = form; “not on layout” (never layout-hidden); `schema:edit` Admin-only.

Implement **CLOSED**. Design Group re-stamps after tip.

## Implement gate OPEN (2026-09-23; Rolf)

| Gate | Status |
|------|--------|
| Design Group UX Accept | **Met** on tip `f79e2a0` (Heidi / Hans / Deiter) |
| Günter Brief restamp | **Met** |
| Implement gate | **OPEN** |

Tobias **UAT Fail** on `8c14a84`. Marc green-lit Grok Build fix for blockers A+B. Re-UAT after new tip. No invent Pass; no merge until Pass + Rolf Confirm + Marc.

## Product branch + UAT (2026-09-23; Rolf / Marc)

| Item | Cite |
|------|------|
| Product / dogfood / UAT branch | `feat/ui-schema-ddl` |
| Product tip (Grok Build landed) | `8c14a84` |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` on that branch |
| Docs living tip (implement OPEN) | `912c1a2` on `docs/ui-schema-ddl` |

Tobias owns UAT Pass/Fail against Fail bars (1)–(5). **No invent Pass.** No merge until Rolf Confirm + Marc.

## Tobias UAT Fail + fix in flight (2026-09-23; Rolf / Marc)

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

**Status:** Grok Build fix A+B **in flight** on `feat/ui-schema-ddl`. Tobias **re-UAT** §§2/3/6/7 (and unscored bars) after new product tip. No merge until UAT Pass + Rolf Confirm + Marc.

