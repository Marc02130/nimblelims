# Manual: Schema (table browser, real columns, side-link relations)

**UI:** Admin → **Schema** (`/admin/schema/tables`) — five surfaces: Tables, Columns, Relations, Layouts, Privileges  
**API:** `/v1/schema/*`  
**Permission:** mutate Tables/Columns/Relations/Privileges = **`schema:edit`** (Admin only by default). Layouts = **`layout:edit`** or `schema:edit`. `layout:edit` cannot DDL.  
**UAT:** `UAT_Scripts/uat-ui-schema-ddl.md` (CREATE/ALTER), `UAT_Scripts/uat-ui-schema-tables-cleanup.md` (browser + relations)  
**Briefs:** `.docs/review/requirements/ui-schema-ddl-brief.md`, `.docs/review/requirements/ui-schema-tables-cleanup-brief.md`

The Schema screen is a **browser over real Postgres tables**. A field is a column on a table. There is no Custom Fields area any more (`/admin/custom-fields` redirects here). Not JSONB-as-schema (OQ-16). `custom_attributes` is not this path.

| Surface | Does |
|---------|------|
| Tables | Lists every allow-listed table with a **Lab** / **System** badge, source (Built-in / Created here), field count and link count. CREATE TABLE (`x_*` / `lab_*`) with platform columns + FORCE RLS. Deprecate / Drop only for tables created here. |
| Columns | Browses the columns of one table (`?table=<physical>`). ADD COLUMN on Lab tables (P1 types: Text, Number, Whole number, Yes/No, Date, Date and time, List). System columns are locked. Shows a read-only **Links** row. |
| Relations | Declares one-to-many / one-to-one **side links** over an existing FK column on the child. Registry only; no DDL. |
| Layouts | Role × screen **membership**. Absent = not shown. No hide toggle. Screens: `receive`, `samples.list`, `samples.detail`. **Asked-for and routing leave as is.** |
| Privileges | Role × table Read/Write/none. Default deny. Does **not** mint `schema:edit`. |

## What is in the table list

Membership is an allow-list in `backend/app/services/ui_schema_catalog.py`, not a filter on the registry query. The registry is filled lazily on first view (`ensure_catalog`) and columns are **reflected** from `information_schema` / `pg_constraint` / `pg_index`.

| Badge | Tables |
|-------|--------|
| **Lab** | samples, containers, contents, tests, results, batches, projects, client_projects, experiments, lims_runs, work_orders, asked_for, routing_map, analyses, analytes, test_batteries, instruments, locations, eln_processes, plus every table created from the Tables tab |
| **System** | lists, list_entries, units, container_types, instrument_types, sample_type_transitions, clients, users, roles |
| Hidden | Engine internals: `alembic_version`, `revoked_tokens`, `login_throttle`, permission plumbing, the `schema_*` registry, `ui_schema_ddl_log`, legacy field/attribute config tables |

To add a table to the browser, add it to `LAB_TABLES` or `SYSTEM_TABLES`. Lab tables sort first.

## System columns (locked)

Lock icon + **System** chip, no edit, no action menu. The lock set:

| Reason | Columns |
|--------|---------|
| Platform | `id`, `client_id`, `created_at`, `created_by`, `modified_at`, `modified_by`, `active` |
| Identity | Sample identity columns (name/barcode) |
| Relationship key | Any FK column that is **not** a list binding (e.g. `tests.sample_id`, `samples.project_id`). Type shows **Key**; *Points at* links to the parent table. |
| System table | Every column of a System table (`lists`, `list_entries.list_id`, …). *Add field* is disabled on these tables. |

Lab columns (including a uuid FK to `list_entries`, shown as type **List**) stay editable to the extent the UI already edited them. There is **no** drop-column or DDL-apply button on reflected columns.

## Relations (1:N / 1:1)

A relation is a registry row: parent table, child table, cardinality, and the **existing FK column on the child**. The UI only offers FK columns that point at the chosen parent. **One to one** is enabled only when Postgres has a single-column UNIQUE index on that key; otherwise it is One to many. Declaring a relation writes `schema_relations` only — no DDL, no `relationship()` classes, no junction tables.

- Parent's Columns view shows `Name → Child`; child's view shows `Name ← Parent`. Clicking a chip switches tables.
- Undeclared FKs appear as grey `Column → Table` chips (facts from Postgres, not relations).
- Many-to-many is **not** in this phase: `POST /v1/schema/relations` and the `ui_schema_relation` config contract reject `many_to_many`. If a fact needs its own columns, it is its own table.

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/schema/tables` | `category`, `relation_count`, `can_add_columns`, `can_remove` per table |
| GET | `/v1/schema/columns?table_id=` | `is_fk`, `fk_table`, `is_unique`, `origin`, `is_system`, `system_reason`, `editable` |
| GET | `/v1/schema/tables/{id}/links` | Keys, outgoing/incoming relations |
| GET/POST | `/v1/schema/relations` | `schema:edit`; 422 on non-FK key, non-unique 1:1, or `many_to_many` |
| DELETE | `/v1/schema/relations/{id}` | Registry row only |

Deprecate retains data. DROP (UI-created tables only) needs confirm + audit. Lab HTTP uses `lims_app` (no CREATE on `public`). Physical DDL is an allow-listed `schema_apply` function.
