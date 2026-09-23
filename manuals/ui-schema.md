# Manual: Schema (UI CREATE TABLE / ADD COLUMN)

**UI:** Admin → **Schema** (`/admin/schema/tables`) — four surfaces: Tables, Columns, Layouts, Privileges  
**API:** `/v1/schema/*`  
**Permission:** mutate Tables/Columns/Privileges = **`schema:edit`** (Admin only by default). Layouts = **`layout:edit`** or `schema:edit`. `layout:edit` cannot DDL.  
**UAT:** `UAT_Scripts/uat-ui-schema-ddl.md`  
**Brief:** `.docs/review/requirements/ui-schema-ddl-brief.md`

Creates **real Postgres** tables/columns plus registry rows. Not JSONB-as-schema. `custom_attributes` is not this path.

| Surface | Does |
|---------|------|
| Tables | CREATE TABLE (`x_*` / `lab_*`) with platform columns + FORCE RLS |
| Columns | ADD COLUMN on Samples (non-identity) or UI tables. P1 types: Text, Number, Whole number, Yes/No, Date, Date and time, List |
| Layouts | Role × screen **membership**. Absent = not shown. No hide toggle. Screens: `receive`, `samples.list`, `samples.detail`. **Asked-for and routing leave as is.** |
| Privileges | Role × table Read/Write/none. Default deny. Does **not** mint `schema:edit`. |

Deprecate retains data. DROP needs confirm + audit.

Lab HTTP uses `lims_app` (no CREATE on `public`). Physical DDL is an allow-listed `schema_apply` function.
