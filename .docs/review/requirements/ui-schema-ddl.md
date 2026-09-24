# Requirements: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Merged to main** @ `180f0c1` (feat `f05430c` incl. UAT Pass `b6d1920` + docs `9279ec6`). OQ-4–13 **Decided**. Heidi / Hans / Deiter / Günter Accept-with-conditions stand. Design Group UX Accept Met @ `f79e2a0`; Günter Brief restamp Met. Tobias Pass + Rolf Confirm Met stand. Packet **closed** unless Marc opens follow-ups.  
**Stem:** `ui-schema-ddl`  
**Leadership lock:** Core pivot 2026-09-22 — AI-config foundation needs **add tables and columns through the UI as real Postgres objects**, not JSONB pretending to be schema. Sample-processing critical path Met on `main` (E-10 → E-6).  
**Open questions:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Supersedes (scope):** June `schema-evolution` deferral of “add table” for this foundation packet — see §8. Narrow FieldDefinition-on-existing-entity work in [`schema-evolution.md`](schema-evolution.md) remains related, not a substitute.  
**UI owner:** Mathilda (lab-admin UX, not DBA).  
**Architecture stamp:** Heidi + Design Group (DDL model, tenant safety, migration/reversibility).  
**Not IC50. No product code in this PR.**

## 1. Purpose

Enable lab admins (with elevated schema permission) to **CREATE TABLE** and **ADD COLUMN** through the product UI such that the result is **real PostgreSQL objects** (typed columns, indexes, FKs as locked), **tenant-safe**, **migratable**, and **reversible**, with a **role-based layout** registry for on-screen presentation — the robust config layer AI config (north star goal 2) needs on top of framework/DB config (goal 1).

This packet is the **AI-config foundation**, not AI itself. It does **not** open AI for login / reporting / storage (those stay parked except where this schema-config is the explicit blocker — see [`ai-config-breadth.md`](../open-questions/ai-config-breadth.md)).

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Sample-processing critical path **Met** on `main` (E-10 / E-12 / E-14 / E-7 / E-6) | Leadership Core 2026-09-20…22 |
| Next: AI-config foundation = **UI CREATE TABLE / ADD COLUMN as real Postgres** — not JSONB-as-schema | Marc + Rolf 2026-09-22 |
| Tenant-safe, migratable, reversible | Rolf 2026-09-22 |
| Lab-admin UX, not DBA console | Rolf → Mathilda |
| No product code until sketch + Leadership / Heidi Accept | Rolf 2026-09-22 |
| Unpark AI breadth **only** where this schema-config is the blocker | Rolf 2026-09-22 |
| **OQ-1 Decided:** catalog minimum = **table registry** + **column registry** (not lab data); physical CREATE/ALTER still real Postgres; `information_schema` alone insufficient; indexes/FKs wait | Marc + **Rolf Confirm** 2026-09-22 |
| **OQ-2 Decided:** **role-based layout registry** (role × screen × visible columns/sections) — separate from table/column catalogs; schema ≠ layout | Marc + **Rolf Confirm** 2026-09-22 |
| **OQ-3 Decided:** **role × table/column privileges** (read vs write; permission **`schema:edit`** separate — not a new role) — **not** layout; API allow vs UI show | Marc + **Rolf Confirm**; overwrite 2026-09-23 |
| Column registry carries **public SOP field-name hints** for later AI mapping — no house SOP text in git | Katinka + Core 2026-09-22 |
| Not IC50 | Standing |

## 3. Goals

- Maintain **at least two catalog tables**: a **table registry** and a **column registry** that describe which real relations/columns the UI may create or edit (labels, order, nullability, tenant rules, AI hints). Catalogs are **not** the lab data.
- Admin can **add a column** to an allow-listed existing entity/table via UI → real `ALTER TABLE … ADD COLUMN` (typed), not a JSONB key — and a matching **column-registry** row.
- Admin can **create a new table** via UI → real `CREATE TABLE` with required platform columns (identity, tenant/RLS hooks, audit as locked by Heidi) — and a matching **table-registry** row.
- Changes are **reviewable**, **audited**, and leave a **durable migration trail** (**Brief OQ-4 Hybrid**: `lims_app` no DDL; schema-apply role / allow-listed function; `ui_schema` Alembic head or DDL log).
- Changes are **reversible** within policy (deprecate / soft-drop / migrate-out) without silent data loss.
- New objects participate in **RLS / tenant isolation** from first apply.
- New columns/tables are **discoverable** to config surfaces AI will later propose against (catalog metadata), without shipping AI in this packet.
- Mathilda UX: scientist/lab-admin vocabulary (name, type, required, list source) — hide raw SQL unless Heidi explicitly allows an advanced pane.

## 4. Non-goals (this packet)

- AI proposing or applying DDL (north star goal 2 later; separate packet).
- AI config for login, reporting, storage (still parked — breadth OQ).
- Arbitrary low-code app builder, triggers, stored procedures, arbitrary PG types.
- Replacing FieldDefinitions on **Entries** (`experiment_data` / `experiment_sample_data`) — those stay entry FieldDefinitions unless a later lock says promote-to-column.
- Silent rewrite of `custom_attributes` JSONB as config (hard cutover may be a **follow-on**; this packet must not pretend JSONB keys are columns).
- **JSONB-as-config** for schema, layout, privileges, or catalogs (**OQ-16**). JSONB **payload/instrument data** is explicitly allowed.
- DROP DATABASE, cross-tenant DDL, or raw SQL paste / DBA-style DDL editor as the primary path (Mathilda bounce).
- Treating layout hide as the only access control (OQ-3).
- Product coding before Accept.

## 5. Acceptance criteria

Cite the [Brief](ui-schema-ddl-brief.md) for apply / tenant / allow-list / types / deprecate / privileges / Alembic / Entries / custom_attributes.

| ID | Criterion |
|----|-----------|
| AC0 | **Catalog minimum:** product ships (or migrates in) a **table registry** and a **column registry**. UI editing of schema goes through these registries; they store configurable metadata (`information_schema` alone is not enough). |
| AC0b | Applying create/add updates **both** the physical Postgres object **and** the corresponding registry row(s) in one controlled operation (**Brief OQ-4 Hybrid**: `lims_app` no DDL; schema-apply role / allow-listed function; audit + replay). |
| AC0c | **Layout registry:** product ships a **role-based layout** catalog (role × screen × visible columns/sections). Runtime screens honor layout for the signed-in role; missing layout falls back per Mathilda lock. Layout edits do **not** CREATE/ALTER physical columns by themselves. |
| AC0d | **Privileges (Brief OQ-10):** dedicated privilege registry; role × table/column **read/write**; default-deny; DDL needs **`schema:edit`**. **Tobias Fail bars:** no-privilege write → **403/422** (not silent drop); privilege-denied read → refuse (not empty-as-layout); not-on-layout ≠ API allow. |
| AC0e | **AI hints:** column registry SOP field-name hints — **sample type** (not matrix); **vessel = container**; barcode ≠ sample ID; container ≠ sample type; parent = `parent_sample_id`. No house SOP text in git. |
| AC1 | **ADD COLUMN** via UI on an allow-listed table (**Brief OQ-6**: `samples` non-identity + UI-created tables; OQ-8 types) creates a real Postgres column **plus** a column-registry row. |
| AC2 | **CREATE TABLE** via UI creates a real Postgres table (not a JSONB document store) **plus** a table-registry row. Platform columns **Brief OQ-7** (`id`, `client_id`, timestamps, `active`) then FORCE RLS. Slug `x_*` / `lab_*`. |
| AC3 | **Not JSONB-as-config (OQ-16):** UI must not satisfy AC1/AC2 (or layout/privilege/catalog writes) via `custom_attributes` or other JSONB bags. JSONB **is** allowed as a **data** column type for instrument/payload blobs — that is not configuration. |
| AC4 | **Tenant-safe:** shared schema + **FORCE RLS** on `client_id` (**Brief OQ-5**). Registries tenant-scoped in P1. |
| AC5 | **Migratable:** Hybrid apply + `ui_schema` Alembic head / DDL log replay (**Brief OQ-4 / OQ-11**). Core Alembic does not DROP UI objects. |
| AC6 | **Reversible:** deprecate first (retain data); DROP = permission **`schema:edit`** + confirm + impact + audit (**Brief OQ-9**, S-UI-6). |
| AC7 | **Permission (S-UI-1…6):** DDL/schema mutate = permission **`schema:edit`** only (not a new role); **FORCE RLS**; privileges **default-deny** in API; permission **`layout:edit`** ≠ DDL and privilege Write never mints **`schema:edit`**; no **`lims_app` bypass**; DROP confirm+audit. Data read/write uses OQ-3. |
| AC8 | **Audit:** who/when/what (and before/after definition) recorded for every schema mutate. |
| AC9 | **Allow-list (Brief OQ-6):** ADD COLUMN on `samples` (non-identity) + UI-created tables. Identity/lineage fields (incl. freeze params, container type) never UI-droppable. CREATE TABLE = new lab entities only. |
| AC10 | **UX:** Mathilda Accept — lab-admin schema + **layout** admin (role × screen); bounce DBA-only chrome as default path. Layout is the UX centerpiece, not a column-registry footnote. |
| AC11 | **AI-ready metadata:** AI (later) reads **table + column + layout** registries (and allow-listed system descriptors) — not `information_schema` alone. No AI apply in this packet. Indexes/FKs not required in P1 catalog. |
| AC12 | **Four screens:** Admin→Schema exposes **Tables**, **Columns**, **Layouts**, **Privileges** as distinct surfaces ([ui-review](../ui-review/ui-schema-ddl.md)). Bounce burying privileges/layout on the column row alone. |
| AC13 | **DDL proof:** after CREATE/ALTER, UAT proves real Postgres relation/column via `information_schema` (or equivalent). Without **`schema:edit`**, lab roles cannot DDL. |
| AC14 | **OQ-15 + Deiter layout:** layout = **membership** (absent = not shown); R/W = privileges. List pages use role layout; on-the-fly column add/remove is **ephemeral**. Multi-row = table; single record = form. **Receive** may keep select-then-enter as Lab Ops note. **Asked-for and routing leave as is** — not layout/schema-config this packet. Known screen keys first. No Schema-admin role — permission `schema:edit` on Admin only. |
| AC15 | **OQ-16:** config mutations (table/column registry, layout, privileges, DDL apply) never persist configuration in JSONB. Fail bar (Tobias/Mathilda): config path writing JSONB instead of real relations/DDL → **Fail**. Instrument/payload JSONB data columns remain in scope as data. |

## 6. Path exercised (happy)

1. Lab admin opens Schema / Fields admin (Mathilda name) backed by **table + column registries**.  
2. **Add column** on Samples: list-backed or scalar → preview impact → apply → real column **and** column-registry row; visible in forms/search as locked.  
3. **Create table** for a lab-specific entity (Heidi names the first allowed pattern) → real table **and** table-registry row → basic CRUD scaffold per lock (may be minimal in P1).  
4. Admin sets **layout** for Lab tech vs Admin on a screen → same schema, different visible fields/sections.  
5. Attempt cross-tenant read → denied.  
6. Deprecate column → layout rows updated/hidden per policy; data retained until controlled remove.

## 7. Open questions

OQ-4–13 **Decided** in the [Brief](ui-schema-ddl-brief.md). Living OQ doc: [`ui-schema-ddl.md` (open-questions)](../open-questions/ui-schema-ddl.md). OQ-14 parked. Design Group UX Accept **Met**. Günter restamp **Met**.

## 8. Relationship to prior schema-evolution docs

| Doc | Relationship |
|-----|--------------|
| [`requirements/schema-evolution.md`](schema-evolution.md) (2026-06-30) | Prior MVP deferred **add table**; prioritized FieldDefinitions on existing entities. **This packet re-opens CREATE TABLE + real ADD COLUMN** as AI-config foundation per 2026-09-22 Leadership lock. |
| [`ceo-review/schema-evolution.md`](../ceo-review/schema-evolution.md) | Historical CEO “defer add table” — **superseded for sequencing** by 2026-09-22 pivot; keep for history. |
| Entry FieldDefinitions / extract-hold | Unchanged: process data on entries is not this packet. |

## 9. Sign-off

| Review | Verdict |
|--------|---------|
| Leadership / CEO | **Packet OPEN** (pivot locked). Accept pending sketch. |
| Architecture (Heidi) | **Accept with conditions** (2026-09-22, restamp @ `c6f0854`) — conditions **OQ-4–13** now **Decided** in [Brief](ui-schema-ddl-brief.md); **OQ-16 Confirm**. |
| Science / CSO (Hans) | **Accept with conditions** (2026-09-22) — punches baked into Brief. **Confirm 2026-09-23** Marc overwrite (SOP hints + Results). |
| UI (Mathilda) | **Sketch Accept** @ `e12b0c2`; **re-stamped** @ `f79e2a0`. |
| Design Group | **UX Accept Met** @ `f79e2a0` (Heidi / Hans / Deiter). |
| Security (Günter) | **Accept with conditions** @ `c6f0854` — S-UI-1…6; overwrite S-UI-1=`schema:edit`, S-UI-4=`layout:edit`. **Confirm 2026-09-23** Marc overwrite + **Admin defaults** to `schema:edit` + privilege admin — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later (optional separate role later; S-UI-2/3/5/6 unchanged). **Brief restamp Met**. |
| Lab Ops (Deiter) | **Accept with conditions** (2026-09-22) @ `c6f0854` — Brief written (OQ-4–11). **Confirm 2026-09-23** Marc overwrite; **retract** Hide/Read-only/Deny three-mode copy. Implement **OPEN** (Design UX Accept Met @ `f79e2a0`). |
| Spec (Wilhelmina) | Living fold (this doc + Brief). |
| QA (Tobias) | **re-UAT Pass** on `b6d1920` (0081). §§2/3/6/7 Pass; Fail bars 1/2/4 Met; §§1/4/5/8 stand from `8c14a84`. Rolf Confirm **Met**. **Merged to main** @ `180f0c1`. |

**Implement gate:** **CLOSED** (shipped). Design Group UX Accept **Met** @ `f79e2a0` (Heidi/Hans/Deiter). Günter Brief restamp **Met**. Tobias Pass + Rolf Confirm Met stand. **Merged to main** @ `180f0c1` (feat `f05430c` incl. UAT Pass `b6d1920` + docs `9279ec6`). Packet **closed** unless Marc opens follow-ups.

**Marc overwrite Confirms (2026-09-23; Rolf):** Günter + Hans + Deiter Confirmed. Deiter retracts three-mode Hide/Read-only/Deny copy. **Günter follow-on:** Admin defaults to `schema:edit` + privilege admin — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later; optional separate role later; `layout:edit` still no DDL; S-UI-2/3/5/6 unchanged. Implement **CLOSED** (at the time; now OPEN).

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
**UI Sketch Accept re-stamp (Mathilda; 2026-09-23):** Verified on tip `f79e2a0` — `schema:edit` Admin-only (no Schema-admin role); asked-for/routing leave as is; ephemeral list cols; multi-row table / single form; not on layout (membership only). Design Group UX Accept still pending on that tip (at the time; now OPEN). Implement CLOSED (at the time; now OPEN).

## Implement gate OPEN (2026-09-23; Rolf)

| Gate | Status |
|------|--------|
| Design Group UX Accept | **Met** on tip `f79e2a0` (Heidi / Hans / Deiter) |
| Günter Brief restamp | **Met** |
| Implement gate | **OPEN** |

Tobias **re-UAT Pass** on `b6d1920` (0081). Rolf Confirm **Met**. **Merged to main** @ `180f0c1` (feat `f05430c` incl. UAT Pass `b6d1920` + docs `9279ec6`). Packet **closed** unless Marc opens follow-ups.

## Product branch + UAT (2026-09-23; Rolf / Marc)

| Item | Cite |
|------|------|
| Product / dogfood / UAT branch | `feat/ui-schema-ddl` |
| Product tip (Grok Build landed) | `8c14a84` |
| Product tip passed | `b6d1920` |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` on that branch |
| Docs living tip (implement OPEN) | `912c1a2` on `docs/ui-schema-ddl` |
| Merged to main | `180f0c1` (feat `f05430c` incl. UAT Pass `b6d1920` + docs `9279ec6`) |

Tobias owns UAT Pass/Fail against Fail bars (1)–(5). **No invent Pass.** Tobias Pass + Rolf Confirm Met stand. Packet **closed** unless Marc opens follow-ups.

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
| Merge | **Merged to main** @ `180f0c1` (feat `f05430c` incl. UAT Pass `b6d1920` + docs `9279ec6`). Packet **closed** unless Marc opens follow-ups. |

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

