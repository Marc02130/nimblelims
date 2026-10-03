# Schema changes: ui-schema-tables-cleanup

**Feature / cycle:** Schema screen becomes a table browser; one-to-many / one-to-one side links as real-FK registry entries; Custom Fields UI removed  
**Phases covered:** P1 (browser + 1:N / 1:1). M:N explicitly **not** this cycle.  
**Status:** Implemented  
**Alembic revisions:** `0082_ui_schema_table_browser_relations`  
**Requirements:** `.docs/review/requirements/ui-schema-tables-cleanup-brief.md`  
**Open questions:** `.docs/review/open-questions/ui-schema-tables-cleanup.md`  
**UAT:** `UAT_Scripts/uat-ui-schema-tables-cleanup.md`  
**Prior cycle:** `ui-schema-ddl` (alembic 0081) — registry tables `schema_tables`, `schema_columns`, `schema_layouts`, `schema_layout_fields`, `schema_privileges`, `ui_schema_ddl_log`.

## 1. Summary

The registry must **describe tables it did not create**. `schema_tables.kind` gains `system` for reference tables; `schema_columns` gains reflection facts (FK target, UNIQUE, Postgres type, origin) so the UI can lock system columns and offer only real FK columns as relation keys. A new `schema_relations` table records one-to-many / one-to-one side links over an existing FK column on the child. Nothing in this delta issues DDL on lab tables; reflection reads `information_schema.columns`, `pg_constraint`, `pg_index` only.

**Display membership (current, after this delta):** `lists` and `list_entries` (list items) are **not** schema tables. A column added there is unused until application code changes, so they stay off the Schema screen. The migration still allows `kind='system'`, and the shipped catalog still registers those two names — that registration is a product mismatch, not this delta’s display rule. `projects` remains a Lab table. No universal join table. Many-to-many is out of scope (section 6).

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `schema_relations` | Side-link registry (1:N / 1:1). One row per child FK column. | `id`, `client_id` → `clients`, `display_name`, `from_table_id` → `schema_tables` (parent), `to_table_id` → `schema_tables` (child), `fk_column_id` → `schema_columns` (key on child), `cardinality` (`one_to_many` / `one_to_one`), `status` (`active` / `deprecated`), `active`, audit columns |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| `schema_tables` | `kind` check widened to `('core','ui','system')` | `core` = Lab built-in, `ui` = created from the Tables tab, `system` = reference table |
| `schema_columns` | ADD `is_fk boolean NOT NULL DEFAULT false` | Reflected from `pg_constraint contype='f'` |
| `schema_columns` | ADD `fk_table varchar(63) NULL` | Referenced table of the FK |
| `schema_columns` | ADD `is_unique boolean NOT NULL DEFAULT false` | Single-column UNIQUE index (`pg_index.indisunique AND indnkeyatts = 1`); gates 1:1 |
| `schema_columns` | ADD `pg_type varchar(64) NULL` | Raw `udt_name` |
| `schema_columns` | ADD `origin varchar(16) NOT NULL DEFAULT 'ui'` + check `('ui','reflected')` | Backfill: `is_platform OR is_identity` rows → `reflected` |
| `schema_columns` | `data_type` check widened with `uuid`, `jsonb`, `other` | Reflected columns only; the ADD COLUMN allow-list (P1 types) is unchanged in service code |

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| `schema_relations_cardinality_chk` | `cardinality IN ('one_to_many','one_to_one')` | M:N refused at the DB too |
| `schema_relations_status_chk` | `status IN ('active','deprecated')` | |
| `uq_schema_relations_fk_column` | UNIQUE `(client_id, fk_column_id)` | One relation per key (API → 409) |
| `ix_schema_relations_client` / `_from` / `_to` | btree | List / links lookups |
| `schema_columns_origin_chk` | `origin IN ('ui','reflected')` | |

### 2.4 Enums / types

None (string + check constraints, matching the 0081 registry).

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| `schema_relations` | **New** `schema_relations_access` FOR ALL, `is_admin()` or same `client_id` (system client sees all); `FORCE ROW LEVEL SECURITY` | Same shape as the 0081 registry tables. `GRANT SELECT, INSERT, UPDATE, DELETE` to `lims_app` when the role exists. |
| Lab / system tables | None | Browsing reflects catalogs; no policy touched |

## 4. Data migration / backfill

- [x] Backfill: `schema_columns.origin = 'reflected'` where `is_platform OR is_identity`.
- [x] Lazy registration (OQ-3 = B): first `GET /v1/schema/tables` inserts `schema_tables` rows for allow-listed Lab (`kind='core'`) and System (`kind='system'`) tables that exist in Postgres, and `schema_columns` rows (`origin='reflected'`) for their columns. Idempotent; re-syncs FK/UNIQUE facts on each view. **Display rule after this delta:** that insert still includes `lists` and `list_entries`; those two are not schema tables and must not be documented as ones.
- [ ] Dual-write period: none.

## 5. Rollback

`downgrade()` drops `schema_relations`, removes system-table registry rows and reflected non-seeded column rows (plus their `schema_layout_fields` / `schema_privileges` dependents), restores the 0081 `kind` and `data_type` checks, and drops the five new `schema_columns` columns. UI-created rows and platform/identity seed rows survive. No lab data is touched either way.

## 6. Explicitly out of scope (this cycle)

- **No junction tables, no universal join table, no systemwide unique ids.** M:N waits until ids are globally unique.
- **No DDL from the schema screen beyond the existing CREATE TABLE / ADD COLUMN path.** Reflection and relations are read / registry only.
- **No `relationship()` generation** from the registry.
- **No drop-column / apply-DDL** on reflected columns.
- `custom_attributes` / `custom_attributes_config` / `field_definitions`: untouched and hidden (OQ-2 = A, park).

## 6b. Multi-tenant readiness

`schema_relations` is tenant-scoped via `client_id` with the same RLS as the rest of the registry. Reflection facts are lab-global (they describe one physical schema). Nothing here adds a null-tenant or dual path.

## 7. Open schema blockers

None. OQ-1 / OQ-2 / OQ-3 decided in `.docs/review/open-questions/ui-schema-tables-cleanup.md`; OQ-5 (M:N / on-delete) deferred, does not block 1:N / 1:1.

## 8. Implementation checklist

- [x] Migration(s) match this doc
- [x] Models match migration (`backend/models/ui_schema.py`: `SchemaColumn` reflection columns, `SchemaRelation`)
- [x] RLS tested if changed (`backend/tests/test_ui_schema_table_browser.py` runs through the HTTP layer as admin; relation create/delete under policy)
- [x] This file updated with revision id(s)
