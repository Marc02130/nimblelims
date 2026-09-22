# Open questions: UI-driven schema DDL (real Postgres)

**Date:** 2026-09-22  
**Status:** **Open** (OQ-1/2/3/15/16 **Decided**; Heidi **Architecture Accept with conditions** OQ-4–13 + OQ-16 Confirm @ `c6f0854`; Hans **Science Accept with conditions**; Deiter **Lab Ops Accept with conditions**; Günter **CSO Accept with conditions** S-UI-1…6) — full Leadership set — packet `ui-schema-ddl`  
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
| **OQ-15** | **Layout grain:** known product screen keys first; section → fields; default when no layout = all **read**-privileged columns in registry order; bench vs review separate layouts; layout read-only chrome ≠ API write. Four surfaces: Tables / Columns / Layouts / Privileges. | Mathilda Sketch Accept @ `e12b0c2` | 2026-09-22 |
| **OQ-16** | **JSONB = payload data only** (instrument results / similar blobs). **Not** for system configuration — schema, layout, privileges, and other config live in **real tables/columns** (registries + DDL). Bounce JSONB-as-config. | Marc + **Rolf Confirm** | 2026-09-22 |

### OQ-1 AI hints (Katinka)

Keep **public SOP field names** on the column registry (e.g. barcode vs sample ID, vessel vs material, parent link, matrix/type) so AI can map SOPs later. **No house SOP text in git.** Layout (OQ-2) should separate bench tech vs review roles the way public methods already do.

## Blocking questions (still open)

| ID | Question | Options / notes | Owner |
|----|----------|-----------------|-------|
| OQ-4 | **Apply model:** runtime DDL vs generated Alembic vs hybrid? | Upgrade-safe, auditable. | Heidi |
| OQ-5 | **Tenant isolation:** shared + RLS vs per-tenant schemas? Registry + privilege scope per tenant? | Fail closed. | Heidi + Günter |
| OQ-6 | **Allow-list:** which system tables get UI columns in P1? **Hans:** protect identity/lineage fields from casual UI overwrite. | Protect core upgrades + identity. | Heidi + Leadership + Hans |
| OQ-7 | **Platform columns on CREATE TABLE:** PK, tenant key, timestamps, soft-delete, audit? | Min physical shape. | Heidi |
| OQ-8 | **Supported types P1:** text, numeric, boolean, date/timestamptz, list→`list_entries`? | Indexes/FKs wait. | Heidi + Mathilda |
| OQ-9 | **Reversibility:** deprecate vs DROP; layout + privilege rows when column deprecated. **Hans:** science-safe deprecate before destructive DROP of data-bearing fields. | | Heidi + Leadership + Hans |
| OQ-10 | **Privilege store grain:** separate privilege registry vs columns on role/layout tables? Default deny? Inherit table→column? | Must support OQ-3 Fail bars. | Heidi + Günter |
| OQ-11 | **Collision with core migrations:** UI objects + registries vs Grok Build Alembic. | | Heidi |
| OQ-12 | **FieldDefinitions / Entries:** promote to real column (+ registries + layout + privileges)? | No mint blur. | Heidi + Wilhelmina |
| OQ-13 | **`custom_attributes`:** dual-read? hard cutover P1 or follow-on? | Bounce JSONB-as-schema. | Heidi + Leadership |
| OQ-14 | **AI metadata:** read table + column + layout + privilege descriptors? | Not login/reporting/storage AI. | Heidi + Wilhelmina |
| OQ-15 | ~~Layout grain~~ | **Decided** — see Decided table + [ui-review/ui-schema-ddl.md](../ui-review/ui-schema-ddl.md) §5. | Mathilda Sketch Accept 2026-09-22 |

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
3. **schema-admin** only for CREATE/ALTER; lab role cannot DDL.  
4. CREATE/ALTER proves real Postgres (`information_schema` / query), not JSONB-as-config.  
5. **OQ-16:** any **config** path (schema / layout / privileges / catalog) that writes **JSONB instead of** DDL or catalog rows → **Fail**. JSONB remains OK for instrument/payload **data** columns.

Plus catalog uniqueness / tenant isolation; role×layout visibility. UAT packet after Design UX stamp + Heidi conditions addressed.

## Architecture Accept (Heidi)

**Accept with conditions** (2026-09-22; restamp cited @ tip `c6f0854`). Conditions = remaining **OQ-4–13**. **OQ-16 Confirm** (JSONB = payload data only; not config). UI sketch: [ui-review/ui-schema-ddl.md](../ui-review/ui-schema-ddl.md) @ `e12b0c2`.

## Science Accept (Hans)

**Accept with conditions** (2026-09-22). Punches:

1. **SOP hint grains** — column-registry AI/SOP hints stay at public field-name grain (Katinka); no house SOP dump.  
2. **OQ-9 deprecate** — science-safe deprecate/remove path before destructive DROP of data-bearing fields.  
3. **OQ-6 identity protect** — allow-list must protect identity / lineage fields from casual UI overwrite.  
4. **Classic Results first-class** — do not replace structured Results with opaque JSONB config; JSONB payloads are data (OQ-16), not a Results substitute.  
5. **No quantity+unit** compound type this packet — prefer separate amount/unit (or existing Result patterns).

## Lab Ops Accept (Deiter)

**Accept with conditions** (2026-09-22, cited @ tip `c6f0854`):

1. Implement stays **CLOSED** until **OQ-4–11** addressed + **Günter** Accept + **Brief**.  
2. **Layout Apply** must not fight living **receive / asked-for** locks.  
3. **Hide vs Read-only vs Deny** copy must be loud (layout hide ≠ privilege deny).  
4. **Lab Ops consult** before a new UI-created table gets a **runtime** screen.

## CSO Accept (Günter)

**Accept with conditions** (2026-09-22, cited @ tip `c6f0854`) — **S-UI-1…6**:

| ID | Condition |
|----|-----------|
| **S-UI-1** | **schema-admin** only for CREATE/ALTER (and schema registry mutate) |
| **S-UI-2** | **FORCE RLS** on UI-created / UI-extended relations |
| **S-UI-3** | Privileges **default-deny** in the API (not UI-only) |
| **S-UI-4** | **layout-admin ≠ DDL** — layout editors cannot CREATE/ALTER |
| **S-UI-5** | No **`lims_app` bypass** of RLS / privilege checks |
| **S-UI-6** | **DROP** (or destructive remove) requires confirm + audit |

## Waiting

- Design UX stamp + Brief (Leadership) — implement still **CLOSED**  
- OQ-4–13 close enough for Brief  

## Unpark / decide rule

Design UX Accept → close OQ-4–13 enough for Brief → implement gate. Heidi + Hans + Deiter + Günter Accept-with-conditions stand. No product code before Brief.
