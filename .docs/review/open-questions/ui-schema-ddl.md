# Open questions: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Open** (OQ-1 + OQ-2 **Decided**) — packet `ui-schema-ddl`  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**Leadership:** Core pivot 2026-09-22 — CREATE TABLE / ADD COLUMN via UI as real Postgres; tenant-safe, migratable, reversible; role-based layout registry.  
**Owners:** Heidi (architecture), Mathilda (UX / layout), Günter (authZ), Wilhelmina (docs).  
**Not IC50. No product code until sketch + Accept.**

## Context

Sample-processing critical path is Met on `main`. AI config needs a **robust configuration layer**. Leadership locked: admins add **tables and columns through the UI as real database objects**, not JSONB keys dressed as schema — plus a **role-based layout** layer for what appears on screen.

Prior June `schema-evolution` explicitly deferred add-table. That deferral is **sequencing-superseded** for this foundation packet; historical CEO notes stay on disk.

## Decided

| ID | Decision | Stamp | Date |
|----|----------|-------|------|
| **OQ-1** | **Catalog minimum = two registry tables:** (1) **table registry** — which real relations the UI may create/edit; (2) **column registry** — name, type, nullability, order, display defaults (and tenant rules / AI hints as locked). These catalogs **describe** configurable real Postgres objects; they are **not** the lab data rows. **`information_schema` alone is not enough**. Physical **CREATE TABLE / ALTER TABLE … ADD COLUMN** still hits real DB objects. **Indexes / FKs can wait**. Heidi Architecture Accept still required before implement. | Marc + **Rolf Confirm** (Core 2026-09-22) | 2026-09-22 |
| **OQ-2** | **Role-based layout registry** (third catalog, separate from table/column): defines **what is shown on screen** — **role × screen × visible columns/sections** (placement/order as Mathilda locks). **Schema = what exists; layout = who sees what and where.** Do **not** bury layout rules only inside the column registry. Mathilda owns the UX centerpiece. Indexes/FKs still wait. Heidi Accept before implement. | Marc + **Rolf Confirm** (Core 2026-09-22) | 2026-09-22 |

## Blocking questions (still open)

| ID | Question | Options / notes | Owner |
|----|----------|-----------------|-------|
| OQ-3 | **Apply model:** controlled runtime DDL vs generated Alembic vs hybrid (propose → approve → apply)? | Upgrade-safe, auditable trail. | Heidi |
| OQ-4 | **Tenant isolation:** shared tables + `client_id` RLS vs per-tenant schemas vs hybrid? How do table/column/**layout** registries scope per tenant? | Fail closed across tenants. | Heidi + Günter |
| OQ-5 | **Allow-list:** which **system** tables may receive UI columns in P1? UI-created tables only if in table registry? | Protect core upgrades. | Heidi + Leadership |
| OQ-6 | **Platform columns on CREATE TABLE:** required PK, tenant key, timestamps, soft-delete, audit? | Min physical row shape + registry mirror. | Heidi |
| OQ-7 | **Supported types P1:** text, numeric, boolean, date/timestamptz, list→`list_entries` FK — else? | JSONB-as-cell ≠ JSONB-as-schema. Indexes/FKs wait. | Heidi + Mathilda |
| OQ-8 | **Reversibility:** deprecate vs DROP vs archive; layout rows when a column is deprecated. | AC6. | Heidi + Leadership |
| OQ-9 | **Permission:** `schema:edit` vs elevated `config:edit`? Who edits **layout** vs who edits **schema**? | May be same or split — Günter. | Günter |
| OQ-10 | **Collision with core migrations:** UI-added objects + registry rows vs Grok Build Alembic. | Prefixes; `system` vs `configurable` flags. | Heidi |
| OQ-11 | **FieldDefinitions / Entries:** promote entry FD → real Sample column (+ column-registry + layout rows) vs stay on entry? | Do not blur mint/extract-hold. | Heidi + Wilhelmina |
| OQ-12 | **`custom_attributes`:** dual-read? hard cutover P1 or follow-on? | Bounce JSONB keys as ADD COLUMN. | Heidi + Leadership |
| OQ-13 | **AI metadata:** AI reads table + column + **layout** registries (not `information_schema` alone)? | Authoring later; not login/reporting/storage. | Heidi + Wilhelmina |
| OQ-14 | **Layout grain (Mathilda):** screen identity model (route/page/entry-kind); section vs field; defaults when no layout row; gloved high-volume constraints. | Centerpiece of admin UX sketch. | Mathilda |

## Non-blocking / park

| ID | Note |
|----|------|
| AI apply DDL | Parked — after foundation Met. |
| AI login / reporting / storage | Parked — [`ai-config-breadth.md`](ai-config-breadth.md). |
| Indexes / FKs in catalog P1 | **Wait** (OQ-1). |
| Full low-code builder | Out of scope. |

## Unpark / decide rule

- **Heidi + Mathilda sketches** land; Leadership + Heidi Accept → Spec folds locks → Günter before implement gate.  
- Product code only after implement gate OPEN.
