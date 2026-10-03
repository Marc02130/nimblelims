# Manual: Schema (table browser, real columns, side-link relations)

**UI:** Admin → **Schema** (`/admin/schema/tables`) — five surfaces: Tables, Columns, Relations, Layouts, Privileges  
**API:** `/v1/schema/*`  
**Permission:** mutate Tables/Columns/Relations/Privileges = **`schema:edit`** (Admin only by default). Layouts = **`layout:edit`** or `schema:edit`. `layout:edit` cannot DDL.  
**UAT:** `UAT_Scripts/uat-ui-schema-ddl.md` (CREATE/ALTER), `UAT_Scripts/uat-ui-schema-tables-cleanup.md` (browser + relations)  
**Briefs:** `.docs/review/requirements/ui-schema-ddl-brief.md`, `.docs/review/requirements/ui-schema-tables-cleanup-brief.md`

The Schema screen is a **browser over real Postgres tables**. A field is a column on a table. There is no Custom Fields area (`/admin/custom-fields` redirects here). Not JSONB-as-schema (OQ-16). `custom_attributes` is not this path. Many-to-many is not in this phase. There is no universal join table.

## Display rule (current — Marc, after the table-browser PR)

A table appears on Schema only when a change can be made **and** the application uses that change through configuration. If a new column would sit unused until application code is refactored, the table stays off Schema. Do not treat it as a schema table.

**Lists, list items, and units are off Schema.** `lists` and `list_entries` store the values edited at Admin → Lists. `units` stores a multiplier the conversion code reads: the lab picks one base unit per type (multiplier 1) and other units convert to it. Application code reads those rows by fixed columns, so a column added on any of them is unused until code changes. They are not schema tables. The Postgres tables stay. Edit lists at `/admin/lists` and units at `/admin/units`.

| Surface | Does |
|---------|------|
| Tables | Lists allow-listed tables that meet the display rule, with a **Lab** / **System** badge, source (Built-in / Created here), field count and link count. CREATE TABLE (`x_*` / `lab_*`) with platform columns + FORCE RLS. Deprecate / Drop only for tables created here. |
| Columns | Browses the columns of one table (`?table=<physical>`). ADD COLUMN on **Samples** and on tables created here (P1 types: Text, Number, Whole number, Yes/No, Date, Date and time, List). Add field is off on other built-in Lab tables and on System tables. System columns are locked. Shows a read-only **Links** row. |
| Relations | Declares one-to-many / one-to-one **side links** over an existing FK column on the child. Registry only; no DDL. |
| Layouts | Role × screen **membership**. Absent = not shown. No hide toggle. Screens: `receive`, `samples.list`, `samples.detail`. **Asked-for and routing leave as is.** |
| Privileges | Role × table Read/Write/none. Default deny. Does **not** mint `schema:edit`. |

## What is in the table list

Membership is an allow-list in `backend/app/services/ui_schema_catalog.py`, then the display rule. The registry is filled lazily on first view (`ensure_catalog`) and columns are **reflected** from `information_schema` / `pg_constraint` / `pg_index`. **`projects` stays** (the table-browser PR did not drop it). This is not “every Postgres table.”

| Badge | Tables |
|-------|--------|
| **Lab** | samples, containers, contents, tests, results, batches, projects, client_projects, experiments, lims_runs, work_orders, asked_for, routing_map, analyses, analytes, test_batteries, instruments, locations, eln_processes, plus every table created from the Tables tab |
| **System** | container_types, instrument_types, sample_type_transitions, clients, users, roles |
| **Not schema tables** | `lists`, `list_entries` (list items), and `units`. Off the Schema screen. Edit lists under **Lists** (`/admin/lists`) and units under **Units** (`/admin/units`). |
| Hidden | Engine internals: `alembic_version`, `revoked_tokens`, `login_throttle`, permission plumbing, the `schema_*` registry, `ui_schema_ddl_log`, legacy field/attribute config tables (`custom_attributes_config`, `field_definitions`, `name_templates`) |

`lists`, `list_entries`, and `units` are in `NOT_SCHEMA_TABLES`, not `SYSTEM_TABLES`. Lab tables other than Samples stay on the browser so side links can be declared over real FKs. A new column on those tables is not offered (`can_add_columns` is true only for `samples` and tables created here) and would not be read back except on Samples.

Add field is enabled only for `samples` and for tables created here (`kind='ui'`). Other built-in Lab tables are browsed and can carry a side link; they do not take a new column from this screen. A column added on Samples is read and written through sample `extra_fields`. Layouts apply to `receive`, `samples.list`, and `samples.detail`.

## System columns (locked)

Lock icon + **System** chip, no edit, no action menu. The lock set:

| Reason | Columns |
|--------|---------|
| Platform | `id`, `client_id`, `created_at`, `created_by`, `modified_at`, `modified_by`, `active` |
| Identity | Sample identity columns (name/barcode) |
| Relationship key | Any FK column that is **not** a list binding (e.g. `tests.sample_id`, `samples.project_id`). Type shows **Key**; *Points at* links to the parent table. |
| System table | Every column of a System table (`container_types`, `clients`, …). *Add field* is disabled on these tables. `lists`, `list_entries`, and `units` are not on this screen. |

A uuid FK to `list_entries` on a lab table is a **list binding** (type **List**), not a relationship-key lock, and not a reason to put `lists` or `list_entries` on Schema. Built-in columns owned by migrations are not editable here. A column **added on Samples** (origin `ui`) keeps Deprecate / Drop. There is **no** drop-column or DDL-apply button on reflected columns.

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
