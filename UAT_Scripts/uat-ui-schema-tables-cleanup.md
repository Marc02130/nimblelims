# UAT: Schema table browser + side-link relations (`ui-schema-tables-cleanup`)

**Stem:** `ui-schema-tables-cleanup`  
**Brief:** `.docs/review/requirements/ui-schema-tables-cleanup-brief.md`  
**Open questions:** `.docs/review/open-questions/ui-schema-tables-cleanup.md`  
**Schema delta:** `.docs/review/schema-changes/ui-schema-tables-cleanup.md` (alembic **0082**)  
**Manual:** `manuals/ui-schema.md`  
**Status:** Script ready. UAT pass **pending** (Tobias). Do **not** invent a Pass. Do **not** merge an empty Pass/Fail table.  
**Prior packet:** `uat-ui-schema-ddl.md` (CREATE TABLE / ADD COLUMN) — those sections still stand and are **not** repeated here.

**Display rule (current):** A table appears on Schema only when a change can be made and used through configuration. **Lists and list items (`Lists`, `List entries`) must not appear.** Their presence is a Fail, even though `ui_schema_catalog.py` still registers `lists` and `list_entries`. `projects` must still appear. Many-to-many stays refused. No universal join table.

## Fail bars (locked)

1. Any Custom Fields chrome (nav item, route page, dialog) still reachable → **Fail**. The route must redirect to Schema. Custom Fields is not a place to work.
2. Table list shows only samples (+ UI-created), **or** shows engine internals (`alembic_version`, `schema_*`, `revoked_tokens`, `ui_schema_ddl_log`), **or** shows **Lists** or **List entries** → **Fail**.
3. A System column (id, timestamps, created-by, relationship FK, `list_id`, any column of a System table) can be edited, deprecated or dropped from the UI or via `POST /v1/schema/columns/{id}/deprecate|drop` → **Fail**.
4. Declaring a relation creates a table, a column, a junction, or any DDL → **Fail**. Only a `schema_relations` row may appear.
5. API accepts `many_to_many`, a non-FK key, or a 1:1 over a non-UNIQUE key → **Fail**.
6. A new "drop column" or "apply DDL" button on reflected columns → **Fail**.

## Logins

- Admin: `admin` / `admin123` (has `schema:edit` + `layout:edit`)
- Lab tech: `lab-tech` / `labtech123` (no `schema:edit`)

## 1. Custom Fields is gone (Fail bar 1)

1. As Admin, open the sidebar Admin section. There is **Schema**; there is **no Custom Fields** item.
2. Open `/admin/custom-fields` directly. You land on `/admin/schema/tables?from=custom-fields` with an info banner: *Custom Fields are removed. A field is a column on a table — add a real field under Schema → Columns.*
3. Help → Admin section mentions Schema, not Custom Fields.
**Pass / Fail:**

## 2. Table list = Lab browser, lists and list items absent (Fail bar 2)

1. Schema → Tables. Tab bar reads **Tables, Columns, Relations, Layouts, Privileges**.
2. Set page size to 50. `Samples`, `Tests`, `Projects`, `Containers`, `Results`, `Batches` carry a **Lab** chip. `Projects` is present. Lab rows sort before any System rows. `Units`, `Container types`, `Clients`, `Users`, `Roles` may still carry a **System** chip (shipped catalog). **`Lists` and `List entries` must be absent.** If either row is on the screen, **Fail** — they are not schema tables.
3. No row named `schema_tables`, `schema_columns`, `alembic_version`, `revoked_tokens`, `ui_schema_ddl_log`, `permissions`, `field_definitions`.
4. `Samples` row: action menu has **Browse fields** only (built-in Lab tables cannot be dropped). A System row that is still listed (for example `Units`): **Browse fields** only. A table created from *Add table* keeps Deprecate / Drop.
5. API: `GET /v1/schema/tables` returns `category` (`lab`/`system`), `relation_count`, `can_add_columns`, `can_remove` on every row. `lists` and `list_entries` in that payload are a **Fail** against the display rule (the catalog still registers them today; that is the mismatch, not a pass).
**Pass / Fail:**

## 3. System columns are locked (Fail bar 3, 6)

1. Browse fields on a System row the catalog still shows, for example `Units`. **Add field** is disabled. Every row shows a lock icon and a **System** chip; no row has a three-dots action menu. Do not open `Lists` or `List entries`; those tables are not on Schema.
2. Columns → table `Tests`. Row `Sample` (`sample_id`): lock icon, System chip, Type **Key**, *Points at* **Samples** (link). Lock tooltip names the reason. Rows `id`, `created_at`, `created_by`, `modified_at` are locked. Row `status`: Type **List**, *Points at* **List** (a list binding on the lab table, not a link that puts list items on Schema).
3. The table picker has no `Lists` and no `List entries`.
4. API as Admin: `POST /v1/schema/columns/{id}/deprecate` and `POST /v1/schema/columns/{id}/drop` (with confirm) on a locked column → **422** with readable copy. `POST /v1/schema/tables/{id}/deprecate|drop` on Samples → **422**. If `lists` is still returned by the API, `POST /v1/schema/columns` and deprecate/drop on that id also → **422**, and section 2 is already a Fail.
5. No drop-column / apply-DDL button on any reflected column.
**Pass / Fail:**

## 4. Lab columns still editable (regression)

1. Columns → `Samples`. **Add field** is enabled. Add `Lab note`, type Text → row appears with **Lab** chip, no lock, action menu (Deprecate / Drop (confirm)).
2. Prove `information_schema.columns` has `lab_note` on `samples` (same bar as `uat-ui-schema-ddl` §3).
**Pass / Fail:**

## 5. Declare a one-to-many side link (Fail bar 4, 5)

1. Relations tab. Empty state: *No relations declared yet. Add relation to declare a link over a real key.*
2. Add relation → Parent `Projects — Lab`, Child `Samples — Lab`. *Key column on child* offers exactly **Project (project_id)**. **One to many** selected; **One to one** disabled with caption *One to one needs a UNIQUE key. Project is not unique in Postgres.*
3. Name `Project samples`. Preview: *Each Samples points at one Projects through Project. Projects lists its Samples. Stored as a real key on Samples.*
4. Declare relation → success banner *Declared "Project samples" over samples.project_id. No database change was made.* Grid row: Project samples / Projects / Samples / Project (project_id) / One to many.
5. Prove in DB: one new row in `schema_relations`; **no** new table or column anywhere (`information_schema.tables` count unchanged).
6. Columns → `Projects`: Links row has chip `Project samples → Samples`. Click it: table switches to `Samples`, Links shows `Project samples ← Projects`.
7. Tables tab: `Projects` and `Samples` show **Links = 1**.
8. Delete the relation from the Relations grid → row gone, links back to 0, still no DDL.
**Pass / Fail:**

## 6. Relation guards (Fail bar 5)

Use `POST /v1/schema/relations` as Admin:

1. `cardinality: "many_to_many"` → **422** (also rejected by `POST /v1/config/validate` with `ui_schema_relation`).
2. `fk_column_id` = a non-FK column (e.g. `samples.name`) → **422**.
3. `cardinality: "one_to_one"` over `samples.project_id` (not UNIQUE) → **422**.
4. Same key declared twice → **409** *That key already carries a relation.* (one relation per FK column).
5. As lab-tech, `POST /v1/schema/relations` → **403**.
**Pass / Fail:**

## 7. Lazy registry, no DDL from reflection (OQ-3 / OQ-16)

1. Fresh DB: first `GET /v1/schema/tables` registers Lab tables (including `projects`) and reflects their columns. `lists` and `list_entries` must not be treated as a pass if they come back. `ui_schema_ddl_log` gains **no** rows from browsing.
2. Add a column to `samples` by migration or `schema_apply`; reload Columns → it appears with `origin = reflected`.
**Pass / Fail:**

## Sign-off

| Role | Result | SHA |
|------|--------|-----|
| Tobias | | |
| Rolf Confirm | | |
| Merge | Marc's call | — |

### Section stamps

| § | Result | Tip |
|---|--------|-----|
| 1 Custom Fields gone | | |
| 2 Table list | | |
| 3 System columns locked | | |
| 4 Lab columns editable | | |
| 5 1:N side link | | |
| 6 Relation guards | | |
| 7 Lazy registry | | |

### Fail bars

| Bar | Result |
|-----|--------|
| (1) Custom Fields chrome | |
| (2) list filter | |
| (3) system columns read-only | |
| (4) relation = registry only | |
| (5) relation guards | |
| (6) no drop/apply on reflected | |

## Automated evidence (Cursor, pre-UAT)

- `backend/tests/test_ui_schema_table_browser.py` — list filter (Lab + System, internals hidden), system-column locks (UI + API 422), 1:N / 1:1 create + delete, non-FK / non-unique / M:N rejection, idempotent catalog. Those tests still **expect** `lists` and `list_entries` in the payload. That expectation matches the catalog and **fails** the display rule above. It is not a UAT Pass.
- `frontend/src/__tests__/schemaBrowser.test.ts` — badge, sort, lock, key-filter and sentence helpers.
