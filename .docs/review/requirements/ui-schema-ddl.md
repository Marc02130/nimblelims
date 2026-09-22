# Requirements: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Brief written** ([ui-schema-ddl-brief.md](ui-schema-ddl-brief.md) 2026-09-22) — OQ-4–13 **Decided**. Heidi / Hans / Deiter / Günter Accept-with-conditions stand. Implement gate **CLOSED** until Design Group UX Accept + Günter restamp. Coding stays Grok Build unless Marc/Rolf asks.  
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
| **OQ-3 Decided:** **role × table/column privileges** (read vs write; schema-admin separate) — **not** layout; API allow vs UI show | Marc + **Rolf Confirm** 2026-09-22 |
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
| AC0d | **Privileges (Brief OQ-10):** dedicated privilege registry; role × table/column **read/write**; default-deny; schema-admin for DDL. **Tobias Fail bars:** no-privilege write → **403/422** (not silent drop); privilege-denied read → refuse (not empty-as-layout); layout-hide ≠ API allow. |
| AC0e | **AI hints:** column registry stores public SOP-oriented field-name hints (barcode vs sample ID, vessel vs material, parent link, matrix/type). No proprietary house SOP text required in git. |
| AC1 | **ADD COLUMN** via UI on an allow-listed table (**Brief OQ-6**: `samples` non-identity + UI-created tables; OQ-8 types) creates a real Postgres column **plus** a column-registry row. |
| AC2 | **CREATE TABLE** via UI creates a real Postgres table (not a JSONB document store) **plus** a table-registry row. Platform columns **Brief OQ-7** (`id`, `client_id`, timestamps, `active`) then FORCE RLS. Slug `x_*` / `lab_*`. |
| AC3 | **Not JSONB-as-config (OQ-16):** UI must not satisfy AC1/AC2 (or layout/privilege/catalog writes) via `custom_attributes` or other JSONB bags. JSONB **is** allowed as a **data** column type for instrument/payload blobs — that is not configuration. |
| AC4 | **Tenant-safe:** shared schema + **FORCE RLS** on `client_id` (**Brief OQ-5**). Registries tenant-scoped in P1. |
| AC5 | **Migratable:** Hybrid apply + `ui_schema` Alembic head / DDL log replay (**Brief OQ-4 / OQ-11**). Core Alembic does not DROP UI objects. |
| AC6 | **Reversible:** deprecate first (retain data); DROP = schema-admin + confirm + impact + audit (**Brief OQ-9**, S-UI-6). |
| AC7 | **Permission (S-UI-1…6):** DDL/schema mutate = **schema-admin** only; **FORCE RLS**; privileges **default-deny** in API; **layout-admin ≠ DDL**; no **`lims_app` bypass**; DROP confirm+audit. Data read/write uses OQ-3. |
| AC8 | **Audit:** who/when/what (and before/after definition) recorded for every schema mutate. |
| AC9 | **Allow-list (Brief OQ-6):** ADD COLUMN on `samples` (non-identity) + UI-created tables. Identity/lineage fields (incl. freeze params, container type) never UI-droppable. CREATE TABLE = new lab entities only. |
| AC10 | **UX:** Mathilda Accept — lab-admin schema + **layout** admin (role × screen); bounce DBA-only chrome as default path. Layout is the UX centerpiece, not a column-registry footnote. |
| AC11 | **AI-ready metadata:** AI (later) reads **table + column + layout** registries (and allow-listed system descriptors) — not `information_schema` alone. No AI apply in this packet. Indexes/FKs not required in P1 catalog. |
| AC12 | **Four screens:** Admin→Schema exposes **Tables**, **Columns**, **Layouts**, **Privileges** as distinct surfaces ([ui-review](../ui-review/ui-schema-ddl.md)). Bounce burying privileges/layout on the column row alone. |
| AC13 | **DDL proof:** after CREATE/ALTER, UAT proves real Postgres relation/column via `information_schema` (or equivalent). Lab roles cannot DDL; **schema-admin** only. |
| AC14 | **OQ-15 layout defaults:** no layout row → show all columns the role may **read**, in column-registry order; never show write-denied as editable; known screen keys first (`receive`, `asked-for`, `samples.detail`, `samples.list`). |
| AC15 | **OQ-16:** config mutations (table/column registry, layout, privileges, DDL apply) never persist configuration in JSONB. Fail bar (Tobias/Mathilda): config path writing JSONB instead of real relations/DDL → **Fail**. Instrument/payload JSONB data columns remain in scope as data. |

## 6. Path exercised (happy)

1. Lab admin opens Schema / Fields admin (Mathilda name) backed by **table + column registries**.  
2. **Add column** on Samples: list-backed or scalar → preview impact → apply → real column **and** column-registry row; visible in forms/search as locked.  
3. **Create table** for a lab-specific entity (Heidi names the first allowed pattern) → real table **and** table-registry row → basic CRUD scaffold per lock (may be minimal in P1).  
4. Admin sets **layout** for Lab tech vs Admin on a screen → same schema, different visible fields/sections.  
5. Attempt cross-tenant read → denied.  
6. Deprecate column → layout rows updated/hidden per policy; data retained until controlled remove.

## 7. Open questions

OQ-4–13 **Decided** in the [Brief](ui-schema-ddl-brief.md). Living OQ doc: [`ui-schema-ddl.md` (open-questions)](../open-questions/ui-schema-ddl.md). OQ-14 parked. Design Group UX Accept + Günter restamp still wait.

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
| Science / CSO (Hans) | **Accept with conditions** (2026-09-22) — punches baked into Brief: SOP hint grains; OQ-9 deprecate; OQ-6 identity protect; classic Results first-class; no quantity+unit. |
| UI (Mathilda) | **Sketch Accept** @ `e12b0c2` — Tables/Columns/Layouts/Privileges; OQ-15 locked. **Design Group UX Accept pending.** |
| Security (Günter) | **Accept with conditions** (2026-09-22) @ `c6f0854` — **S-UI-1…6** baked into Brief. **Restamp pending** that they still hold. |
| Lab Ops (Deiter) | **Accept with conditions** (2026-09-22) @ `c6f0854` — Brief written (OQ-4–11). Still CLOSED until Design UX + Günter restamp. Layout vs receive/asked-for; Hide/Read-only/Deny copy; consult before new runtime screen. |
| Spec (Wilhelmina) | Living fold (this doc + Brief). |
| QA (Tobias) | UAT after implement gate opens — Fail bars (1)–(5) incl. OQ-16 JSONB-as-config. |

**Implement gate:** **CLOSED**. Brief written. Remains CLOSED until **Design Group UX Accept** and **Günter restamp**.
