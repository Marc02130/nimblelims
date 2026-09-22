# Open questions: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Open** (OQ-1 / OQ-2 / OQ-3 **Decided**) — packet `ui-schema-ddl`  
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
| **OQ-2** | **Role-based layout registry** (separate): **role × screen × visible columns/sections**. Schema = what exists; layout = who **sees** what where. Do not bury layout only in the column registry. Mathilda centerpiece. | Marc + **Rolf Confirm** | 2026-09-22 |
| **OQ-3** | **Role-based access** to tables and columns — **not** the same as layout. Access = what the **API allows** (at least **read vs write** per role on table and column; **schema-admin** privilege separate). A field may be layout-hidden yet still write-forbidden; or visible but **read-only**. Tobias: Fail bars for **privilege refuse** vs **layout hide**. Günter + Heidi on Accept path. | Marc + **Rolf Confirm** | 2026-09-22 |

### OQ-1 AI hints (Katinka)

Keep **public SOP field names** on the column registry (e.g. barcode vs sample ID, vessel vs material, parent link, matrix/type) so AI can map SOPs later. **No house SOP text in git.** Layout (OQ-2) should separate bench tech vs review roles the way public methods already do.

## Blocking questions (still open)

| ID | Question | Options / notes | Owner |
|----|----------|-----------------|-------|
| OQ-4 | **Apply model:** runtime DDL vs generated Alembic vs hybrid? | Upgrade-safe, auditable. | Heidi |
| OQ-5 | **Tenant isolation:** shared + RLS vs per-tenant schemas? Registry + privilege scope per tenant? | Fail closed. | Heidi + Günter |
| OQ-6 | **Allow-list:** which system tables get UI columns in P1? | Protect core upgrades. | Heidi + Leadership |
| OQ-7 | **Platform columns on CREATE TABLE:** PK, tenant key, timestamps, soft-delete, audit? | Min physical shape. | Heidi |
| OQ-8 | **Supported types P1:** text, numeric, boolean, date/timestamptz, list→`list_entries`? | Indexes/FKs wait. | Heidi + Mathilda |
| OQ-9 | **Reversibility:** deprecate vs DROP; layout + privilege rows when column deprecated. | | Heidi + Leadership |
| OQ-10 | **Privilege store grain:** separate privilege registry vs columns on role/layout tables? Default deny? Inherit table→column? | Must support OQ-3 Fail bars. | Heidi + Günter |
| OQ-11 | **Collision with core migrations:** UI objects + registries vs Grok Build Alembic. | | Heidi |
| OQ-12 | **FieldDefinitions / Entries:** promote to real column (+ registries + layout + privileges)? | No mint blur. | Heidi + Wilhelmina |
| OQ-13 | **`custom_attributes`:** dual-read? hard cutover P1 or follow-on? | Bounce JSONB-as-schema. | Heidi + Leadership |
| OQ-14 | **AI metadata:** read table + column + layout + privilege descriptors? | Not login/reporting/storage AI. | Heidi + Wilhelmina |
| OQ-15 | **Layout grain (Mathilda):** screen identity; section vs field; default when no layout row; gloved use. | Three admin surfaces: Tables, Columns, Layouts. | Mathilda |

## Non-blocking / park

| ID | Note |
|----|------|
| AI apply DDL | Parked |
| AI login / reporting / storage | Parked — [`ai-config-breadth.md`](ai-config-breadth.md) |
| Indexes / FKs P1 | **Wait** |
| DBA-style DDL editor | **Bounce** (Mathilda) |
| Full low-code builder | Out of scope |

## UAT note (Tobias)

When ACs land: Fail bars that prove CREATE/ALTER hits **real Postgres** (not JSONB); catalog uniqueness / tenant isolation; **role×layout** visibility; and **privilege refuse vs layout hide** (OQ-3). Formal UAT after Heidi Accept + Ready path.

## Unpark / decide rule

Heidi + Mathilda sketches → Leadership + Heidi Accept → Spec fold → Günter → implement gate. No product code before Accept.
