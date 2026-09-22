# Open questions: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Open** (OQ-1 **Decided**) — packet `ui-schema-ddl`  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**Leadership:** Core pivot 2026-09-22 — CREATE TABLE / ADD COLUMN via UI as real Postgres; tenant-safe, migratable, reversible.  
**Owners:** Heidi (architecture), Mathilda (UX), Günter (authZ), Wilhelmina (docs).  
**Not IC50. No product code until sketch + Accept.**

## Context

Sample-processing critical path is Met on `main`. AI config needs a **robust configuration layer**. Leadership locked: admins add **tables and columns through the UI as real database objects**, not JSONB keys dressed as schema.

Prior June `schema-evolution` explicitly deferred add-table. That deferral is **sequencing-superseded** for this foundation packet; historical CEO notes stay on disk.

## Decided

| ID | Decision | Stamp | Date |
|----|----------|-------|------|
| **OQ-1** | **Catalog minimum = two registry tables:** (1) **table registry** — which real relations the UI may create/edit; (2) **column registry** — name, type, nullability, order, display (and tenant rules / AI hints as locked). These catalogs **describe** configurable real Postgres objects; they are **not** the lab data rows. **`information_schema` alone is not enough** (system vs configurable, labels, tenant rules, AI hints). Physical **CREATE TABLE / ALTER TABLE … ADD COLUMN** still hits real DB objects. **Indexes / FKs can wait** (not P1 catalog). Heidi Architecture Accept still required before implement. | Marc question + **Rolf Confirm** (Core 2026-09-22) | 2026-09-22 |

## Blocking questions (still open)

| ID | Question | Options / notes | Owner |
|----|----------|-----------------|-------|
| OQ-2 | **Apply model:** Does the app run controlled runtime DDL, generate Alembic revisions for ops apply, or a hybrid (propose migration → approve → apply)? | Must stay upgrade-safe and auditable. Prefer reviewable trail over raw unchecked ALTER. | Heidi |
| OQ-3 | **Tenant isolation:** Shared tables + `client_id` RLS vs per-tenant schemas vs hybrid? How do registries scope per tenant? | Must fail closed across tenants. | Heidi + Günter |
| OQ-4 | **Allow-list:** Which existing **system** tables may receive UI columns in P1? Are **UI-created** tables only those present in the table registry? | Prevent breaking core upgrade migrations. | Heidi + Leadership |
| OQ-5 | **Platform columns on CREATE TABLE:** Required PK, tenant key, timestamps, soft-delete, audit on every UI-created table? | Define the minimum row shape written into physical table + mirrored in registries. | Heidi |
| OQ-6 | **Supported types P1:** text, numeric, boolean, date/timestamptz, list→`list_entries` FK — anything else? | JSONB-as-**cell type** ≠ JSONB-as-schema; be explicit. Indexes/FKs wait per OQ-1. | Heidi + Mathilda |
| OQ-7 | **Reversibility:** Deprecate vs DROP COLUMN vs archive; grace period; who approves destructive remove? Registry row vs physical object lifecycle. | AC6. | Heidi + Leadership |
| OQ-8 | **Permission:** New `schema:edit` (or similar) vs elevated `config:edit`? | Günter STRIDE. | Günter |
| OQ-9 | **Collision with core migrations:** How do UI-added columns/tables + registry rows survive when Grok Build ships Alembic for the same table? | Naming prefixes? Reserved names? Registry flags `system` vs `configurable`. | Heidi |
| OQ-10 | **Relation to FieldDefinitions / Entries:** When is an entry FieldDefinition **promoted** to a real Sample column (+ column-registry row) vs staying on the entry? | Do not blur mint/extract-hold locks. | Heidi + Wilhelmina |
| OQ-11 | **Relation to `custom_attributes`:** Dual-read during transition? Hard cutover in-scope for P1 or follow-on? | Bounce pretending JSONB keys satisfy ADD COLUMN. | Heidi + Leadership |
| OQ-12 | **Catalog metadata for AI:** Do AI proposers read **only** the two registries (+ allow-listed system tables), never invent DDL against `information_schema` alone? | Unparks AI **authoring** after foundation Met — not login/reporting/storage. | Heidi + Wilhelmina |
| OQ-13 | **First lab-admin UX:** Single “Schema” admin vs embedded “Add field” on Samples? Create-table wizard steps? Surfaces for editing registry display/order without raw SQL. | Lab-admin language. | Mathilda |

## Non-blocking / park

| ID | Note |
|----|------|
| AI apply DDL | Parked — separate packet after foundation Met. |
| AI login / reporting / storage config | Parked — [`ai-config-breadth.md`](ai-config-breadth.md). |
| Indexes / FKs in catalog P1 | **Wait** (OQ-1). |
| Full low-code builder | Out of scope. |

## Unpark / decide rule

- **Heidi + Mathilda sketches** land; Leadership + Heidi Accept → Spec folds locks into requirements → Günter before implement gate.  
- Product code only after implement gate OPEN.
