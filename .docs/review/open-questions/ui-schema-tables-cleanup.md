# Open questions: Schema Tables cleanup + kill Custom Fields

**Stem:** `ui-schema-tables-cleanup`  
**Date:** 2026-10-01  
**Status:** P1 **implemented** 2026-10-03 (table browser + 1:N / 1:1 side links; alembic 0082). OQ-1 / OQ-2 / OQ-3 **Decided** by Marc's product locks (2026-10-03), then **narrowed for display** by the rule below. OQ-5 M:N **Deferred** (ids not globally unique). Prior `ui-schema-ddl` locks stand. UAT pass pending: `UAT_Scripts/uat-ui-schema-tables-cleanup.md`. Do not invent a UAT Pass.

## Display rule (current — Marc, after the table-browser PR)

A table appears on Schema only when a change can be made **and** used through configuration. If the application would ignore the change until code is refactored, leave the table off Schema. Do not document it as a schema table.

**`lists` and `list_entries` (list items) are not schema tables.** They store values edited at Admin → Lists. Application code reads those rows to populate lists, so an added column is unused until code changes. They stay off the Schema screen.

This supersedes, for **display membership only**, the 2026-10-03 sentence that put “system reference tables starting with `lists`” on the table list, and the OQ-1 System cell that names `lists`, `list_entries`. Those sentences stay below as history of what the catalog registered. Do not reopen: Custom Fields removal, system-column locks, side links as real FKs in `schema_relations`, M:N deferred, no universal join table, no `relationship()` from config.

**`projects` stays** on the Lab list. The table-browser PR did not drop it. The list is not “every table.”

## Marc product locks (2026-10-03 — do not reopen, except the display sentence marked history)

- Drop the Custom Fields area of the schema UI. A field is a column on a table. Custom Fields is not a place to work.
- **History (superseded for lists / list items by the display rule above):** Table list shows **every lab table** registered in `ui_schema` plus **system reference tables** starting with `lists`. Hide engine internals (migrations, sessions, audit plumbing). Badge **Lab** vs **System**. **Current truth:** Lab allow-list including `projects`, plus UI-created tables; System rows the catalog still registers other than `lists` and `list_entries`; engine internals hidden. `lists` and `list_entries` are off Schema.
- **System columns are not editable and not removable** in the UI: id, timestamps, created-by, relationship FKs, and `list_id` when the column is a list. Lab columns stay editable to the extent the UI already edits columns. No drop-column / DDL-apply button.
- ORM is SQLAlchemy 2 + Alembic on Postgres. **No `relationship()` generated from config.**
- 1:N and 1:1 = a **registry entry** (from table, to table, cardinality, child FK column). Key is a real FK on the child. Parent UI may show a read-only link to the child.
- **No universal join table, no systemwide unique ids, no fat junction tables** this phase. M:N with no payload waits until ids are globally unique. If a fact needs its own columns, it is its own table.
- Config bundles still update `ui_schema` registries. No separate agent UI file. OQ-16 stands. Do not mutate the database from the schema screen.

## OQ-1 — P1 Schema Tables allow-list (DECIDED — Marc, 2026-10-03)

**Decision: B.** Allow-list in `backend/app/services/ui_schema_catalog.py`:

| Badge | Set |
|-------|-----|
| **Lab** (`kind='core'`) | samples, containers, contents, tests, results, batches, projects, client_projects, experiments, lims_runs, work_orders, asked_for, routing_map, analyses, analytes, test_batteries, instruments, locations, eln_processes + UI-created (`kind='ui'`) |
| **System** (`kind='system'`) | **History of the shipped catalog:** lists, list_entries, units, container_types, instrument_types, sample_type_transitions, clients, users, roles. **Current display truth:** `lists` and `list_entries` are **not** schema tables. The other names are still what `SYSTEM_TABLES` registers. |
| Hidden | `alembic_version`, `revoked_tokens`, `login_throttle`, permission plumbing, `schema_*` registry, `ui_schema_ddl_log`, `custom_attributes_config`, `field_definitions`, `name_templates`, anything not allow-listed |

**Finding:** the short list was **not** a frontend filter — `ensure_core_catalog()` only ever registered `samples`. Replaced by `ensure_catalog()` (allow-list + Postgres reflection).

## OQ-2 — Custom Fields / `custom_attributes` cutover (DECIDED — A, park)

UI removed (`/admin/custom-fields` → redirect to Schema Tables with banner). `custom_attributes` JSONB data and `custom_attributes_config` / `field_definitions` tables are **left in place, hidden from the browser, unread by the schema path**. Migration of named keys → real columns is a later, separate slice.

## OQ-3 — Registry rows for system tables (DECIDED — B, lazy)

`ensure_catalog()` registers allow-listed tables that exist in Postgres on first Schema view and reflects their columns (`origin='reflected'`). Idempotent; FK/UNIQUE facts re-synced each view. No Alembic seed, no admin "Register" step. Alembic 0082 only widens checks and adds the reflection columns + `schema_relations`.

## OQ-4 — Which surfaces still show “custom” language (DECIDED for schema chrome; residual map Mathilda)

Schema chrome, sidebar, Help tip and route are clean. Residual “Custom Fields” wording in Experiment Templates helper copy (“not Custom Fields on Sample/Test”) is historical context for entry columns, not a navigable surface; rename when that screen is next touched.


## OQ-5e — M:N junction visibility (DEFERRED with OQ-5 M:N)

**Leadership lock (Decided 2026-10-01):** M:N junctions stay **behind the scenes**. Admin with `schema:edit` defines the relation; the product **creates/maintains** the junction table and its rows. Operators only **link / unlink** — no junction as a lab data-entry table or spreadsheet of link rows.

**Default (Rolf; Marc may overwrite):** auto-junction is **visible to `schema:edit` only** (Schema Tables as read-only metadata), **never** in operator layouts.

| Option | Meaning |
|--------|---------|
| **A (default)** | Visible in Schema Tables to `schema:edit` only; never on operator layouts |
| **B** | Fully hidden even from Schema Tables (Admin only sees the named M:N relation, not the junction table row) |
| **C** | Marc overwrite — other |


## OQ-5 research cite (2026-10-01; Rolf digest — not a freeze)

Industry / LIMSbase aligns with Leadership locks — **no Spec reopen**.

| Source | Pattern |
|--------|---------|
| **Odoo** | 1:N = FK on child + inverse Related list; M:N = ORM auto-junction; operators pick/link — never edit junction table. [Odoo relations](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/07_relations.html) |
| **SAP** (ABAP Dictionary / CDS) | Real junction + FKs; UI navigates associations; junction is composition under parent, not a lab spreadsheet. [SAP table relationships](https://learning.sap.com/learning-journeys/acquire-core-abap-skills/defining-relationships-between-database-tables_e55dbd61-6083-4747-bb5d-905ba29ab662) |
| **LIMSbase** (`/Users/marcbreneiser/Code/LIMSbase` / iggybase) | `table_object_children` (1:N link field) vs `table_object_many` (M:N via named link table); engine maintains link rows — `analysis.md` §4.3.2 |

**Leadership takeaway:** keep current locks (behind-the-scenes M:N; link/unlink; schema:edit metadata default).


## UX sketch (cite only — 2026-10-01)

Mathilda sketch tip **`564fe6f`** — [ui-schema-tables-cleanup.md](../ui-review/ui-schema-tables-cleanup.md) on [PR 139](https://github.com/Marc02130/nimblelims/pull/139). Spec base **`07ccd59`**. Sketch **pending Accept**. Encoded: Custom Fields chrome kill; Tables = Samples + Project + UI-created; Relations tab; operators link/unlink; junction metadata `schema:edit` only. OQ-1 / OQ-5b **not** frozen by sketch. Implement **CLOSED**. Rolf Confirm Met on land.

## Decided (from prior packet — do not reopen)

- OQ-16: JSONB-as-**config** Fail; JSONB payload/instrument **data** OK.
- `schema:edit` Admin-only; layout = membership; privileges ≠ layout.
- CREATE TABLE / ADD COLUMN Hybrid apply stands.
- Relations: 1:N / 1:1 / M:N = real FK / unique FK / junction (Leadership 2026-10-01); JSONB related-ids Fail.
- M:N junctions **behind the scenes**; operators link/unlink only; default visibility = `schema:edit` only, never operator layouts (OQ-5e; Marc may overwrite).
- Tobias Fail bar **(6):** operator opens junction as lab data-entry / spreadsheet of link rows / non–`schema:edit` layout → **Fail**.
- Tobias Fail bar **(7)** (provisional until OQ-5b freezes): CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail**.
- Katinka: vessel/container and parent→aliquot/derivative = **1:N FKs on the child** (SOP confirm).

## OQ-5 — Relations cardinality + UI + on-delete (1:N / 1:1 SHIPPED; M:N + on-delete DEFERRED)

**Shipped 2026-10-03 (P1):** Relations tab (`schema:edit`). A relation = `schema_relations` row: parent, child, cardinality, **existing FK column on the child**. UI offers only FK columns pointing at the chosen parent; 1:1 enabled only when Postgres has a single-column UNIQUE index on the key. Declaring writes the registry only — no DDL, no `relationship()`, no junction. `POST /v1/schema/relations` and config contract `ui_schema_relation` refuse `many_to_many`. Parent Columns view shows `Name → Child`, child shows `Name ← Parent` (read-only links). Resolves **OQ-5a** (declare over existing FK; new FK columns are a later ADD COLUMN type), **OQ-5c** (read-only link chips in schema chrome; operator Related lists still Mathilda), **OQ-5d** (any allow-listed pair with a real FK).

**Deferred:** M:N (ids not globally unique — Marc lock), OQ-5b on-delete defaults (registry does not change FK actions; Postgres actions stay as migrated).

**Leadership lock (Decided pattern; UI details open):** real Postgres only.

| Cardinality | Pattern |
|-------------|---------|
| **1:N** | FK on the many side (default; most LIMS links) |
| **1:1** | Unique FK on the dependent side (no shared-PK ceremony for Admin-created tables) |
| **M:N** | Junction table with two FKs + its own row identity; product maintains junction **behind the scenes**; operators link/unlink only (OQ-5e visibility) |

Operators **link records**; Admin with **`schema:edit`** defines the FK/junction. **No** fake M:N arrays / JSONB related-ids.

### Still open (Brief)

| Sub | Question |
|-----|----------|
| OQ-5a | Schema UI: how Admin creates FK / 1:1 unique / M:N junction (wizard vs column type “Reference”) |
| OQ-5b | On-delete policy defaults: **RESTRICT** vs **SET NULL** vs **CASCADE** (per relation? global default?). **Katinka SOP lean (not freeze):** RESTRICT on identity links (sample, barcode vessel); SET NULL only where link is optional. **Tobias Fail bar (7):** CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (provisional until OQ-5b freezes) |
| OQ-5c | Operator UX: **Related list / pickers** on parent or child (Mathilda) — never junction spreadsheet; FK field and/or Related list |
| OQ-5d | Which allow-listed pairs may relate in P1 (blocked until OQ-1) |

**Tobias:** any relation stored only in JSONB/`custom_attributes` → **Fail**. CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (bar 7; provisional until OQ-5b freezes).
