# Requirements: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Draft — packet OPEN** (docs only). **Heidi Architecture Accept with conditions** (2026-09-22). Implement gate **CLOSED** until Design UX stamp + OQ-4–11 close enough for a Brief. Mathilda landing admin UX sketch (Tables/Columns/Layouts). Coding stays Grok Build unless Marc/Rolf asks.  
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
| **Three admin screens:** **Schema** (tables/columns → real DDL), **Layout** (role × screen × visible), **Privileges** (role × table/column read/write — not hide) | Mathilda UI lock 2026-09-22 |
| **Tobias Fail bars (UAT):** (1) privilege refuse → **403/422**, not silent drop; layout-hide ≠ API allow (2) privilege-denied read → refuse, not empty-as-layout (3) **schema-admin** only for CREATE/ALTER; lab role cannot DDL (4) CREATE/ALTER proves real Postgres (`information_schema` / query), not JSONB | Tobias 2026-09-22 |
| **Architecture Accept with conditions** (Heidi) — implement stays CLOSED until Design UX stamp + OQ-4–11 close enough for a Brief | Heidi via Mathilda; Rolf Confirm 2026-09-22 |
| Not IC50 | Standing |

## 3. Goals

- Maintain **at least two catalog tables**: a **table registry** and a **column registry** that describe which real relations/columns the UI may create or edit (labels, order, nullability, tenant rules, AI hints). Catalogs are **not** the lab data.
- Admin can **add a column** to an allow-listed existing entity/table via UI → real `ALTER TABLE … ADD COLUMN` (typed), not a JSONB key — and a matching **column-registry** row.
- Admin can **create a new table** via UI → real `CREATE TABLE` with required platform columns (identity, tenant/RLS hooks, audit as locked by Heidi) — and a matching **table-registry** row.
- Changes are **reviewable**, **audited**, and leave a **durable migration trail** (Heidi locks the apply model: runtime DDL vs generated Alembic — see OQ).
- Changes are **reversible** within policy (deprecate / soft-drop / migrate-out) without silent data loss.
- New objects participate in **RLS / tenant isolation** from first apply.
- New columns/tables are **discoverable** to config surfaces AI will later propose against (catalog metadata), without shipping AI in this packet.
- Mathilda UX: scientist/lab-admin vocabulary (name, type, required, list source) — hide raw SQL unless Heidi explicitly allows an advanced pane.

## 4. Non-goals (this packet)

- AI proposing or applying DDL (north star goal 2 later; separate packet).
- AI config for login, reporting, storage (still parked — breadth OQ).
- Arbitrary low-code app builder, triggers, stored procedures, arbitrary PG types.
- Replacing FieldDefinitions on **Entries** (`experiment_data` / `experiment_sample_data`) — those stay entry FieldDefinitions unless a later lock says promote-to-column.
- Silent rewrite of `custom_attributes` JSONB (hard cutover may be a **follow-on**; this packet must not pretend JSONB keys are columns).
- DROP DATABASE, cross-tenant DDL, or raw SQL paste / DBA-style DDL editor as the primary path (Mathilda bounce).
- Treating layout hide as the only access control (OQ-3).
- Product coding before Accept.

## 5. Acceptance criteria (draft — Heidi may punch)

| ID | Criterion |
|----|-----------|
| AC0 | **Catalog minimum:** product ships (or migrates in) a **table registry** and a **column registry**. UI editing of schema goes through these registries; they store configurable metadata (`information_schema` alone is not enough). |
| AC0b | Applying create/add updates **both** the physical Postgres object **and** the corresponding registry row(s) in one controlled operation (Heidi locks transaction/apply model). |
| AC0c | **Layout registry:** product ships a **role-based layout** catalog (role × screen × visible columns/sections). Runtime screens honor layout for the signed-in role; missing layout falls back per Mathilda lock. Layout edits do **not** CREATE/ALTER physical columns by themselves. |
| AC0d | **Privileges:** role × table and role × column privileges enforce API **read/write** (and schema-admin for DDL). **422/403** (Heidi/Günter lock) on privilege refuse even if layout would show the field. Layout hide must not be the only access control. |
| AC0e | **AI hints:** column registry stores public SOP-oriented field-name hints (barcode vs sample ID, vessel vs material, parent link, matrix/type). No proprietary house SOP text required in git. |
| AC1 | **ADD COLUMN** via UI on an allow-listed core table creates a real Postgres column of a supported type (text, number/numeric, date/timestamptz, boolean, list/FK-to-`list_entries` as locked) **plus** a column-registry row. |
| AC2 | **CREATE TABLE** via UI creates a real Postgres table (not a JSONB document store) **plus** a table-registry row. Required platform columns / constraints per Heidi lock. |
| AC3 | **Not JSONB-as-schema:** UI must not satisfy AC1/AC2 by writing only into `custom_attributes` or equivalent JSONB bags. |
| AC4 | **Tenant-safe:** new tables/columns enforce RLS (or Heidi-approved isolation) so Client A never reads Client B. |
| AC5 | **Migratable:** every applied change leaves an auditable, re-playable trail compatible with upgrades (exact mechanism = Heidi OQ). |
| AC6 | **Reversible:** deprecate/hide and controlled remove/archive paths exist; destructive remove requires confirmation + impact surface; no silent DROP of data-bearing objects. |
| AC7 | **Permission:** schema mutate uses **schema-admin** (elevated; not general `config:edit` alone unless re-locked). Data read/write uses OQ-3 table/column privileges. Günter stamps. |
| AC8 | **Audit:** who/when/what (and before/after definition) recorded for every schema mutate. |
| AC9 | **Allow-list:** which base tables may receive columns, and whether CREATE TABLE is unrestricted within tenant namespace, is Heidi-locked before implement. |
| AC10 | **UX:** Mathilda Accept — lab-admin schema + **layout** admin (role × screen); bounce DBA-only chrome as default path. Layout is the UX centerpiece, not a column-registry footnote. |
| AC11 | **AI-ready metadata:** AI (later) reads **table + column + layout** registries (and allow-listed system descriptors) — not `information_schema` alone. No AI apply in this packet. Indexes/FKs not required in P1 catalog. |
| AC12 | **Three screens:** admin UX exposes **Schema**, **Layout**, and **Privileges** as distinct surfaces (Mathilda). Bounce burying privileges or layout on the column row alone. |
| AC13 | **DDL proof:** after CREATE/ALTER, UAT proves a real Postgres relation/column via `information_schema` (or equivalent query) — not a JSONB key. Lab roles cannot DDL; **schema-admin** only. |

## 6. Path exercised (happy)

1. Lab admin opens Schema / Fields admin (Mathilda name) backed by **table + column registries**.  
2. **Add column** on Samples: list-backed or scalar → preview impact → apply → real column **and** column-registry row; visible in forms/search as locked.  
3. **Create table** for a lab-specific entity (Heidi names the first allowed pattern) → real table **and** table-registry row → basic CRUD scaffold per lock (may be minimal in P1).  
4. Admin sets **layout** for Lab tech vs Admin on a screen → same schema, different visible fields/sections.  
5. Attempt cross-tenant read → denied.  
6. Deprecate column → layout rows updated/hidden per policy; data retained until controlled remove.

## 7. Open questions

All blocking OQs live in [`ui-schema-ddl.md` (open-questions)](../open-questions/ui-schema-ddl.md). Do not invent DDL apply mechanics in requirements beyond AC5–AC6.

## 8. Relationship to prior schema-evolution docs

| Doc | Relationship |
|-----|----------------|
| [`requirements/schema-evolution.md`](schema-evolution.md) (2026-06-30) | Prior MVP deferred **add table**; prioritized FieldDefinitions on existing entities. **This packet re-opens CREATE TABLE + real ADD COLUMN** as AI-config foundation per 2026-09-22 Leadership lock. |
| [`ceo-review/schema-evolution.md`](../ceo-review/schema-evolution.md) | Historical CEO “defer add table” — **superseded for sequencing** by 2026-09-22 pivot; keep for history. |
| Entry FieldDefinitions / extract-hold | Unchanged: process data on entries is not this packet. |

## 9. Sign-off

| Review | Verdict |
|--------|---------|
| Leadership / CEO | **Packet OPEN** (pivot locked). Accept pending sketch. |
| Architecture (Heidi) | **Accept with conditions** (2026-09-22). Conditions punch list to fold when Mathilda/Heidi publish it; OQ-4–11 remain open. |
| UI (Mathilda) | **Sketch landing** — Schema / Layout / Privileges. Design Group woken for UX Accept (Mathilda is UX SoT from Core). |
| Security (Günter) | **Needed** before implement gate. |
| Lab Ops / CSO | Consult if new tables become lab workflow entities. |
| Spec (Wilhelmina) | Draft requirements + OQs (this doc). |
| QA (Tobias) | UAT after Accept — Fail bars: real Postgres not JSONB; catalog uniqueness/tenant; layout visibility; privilege refuse vs layout hide. |

**Implement gate:** **CLOSED**. Heidi Architecture Accept stands with conditions. Remains CLOSED until Design UX stamp + open OQs (OQ-4–11) close enough for a Brief (Rolf 2026-09-22).
