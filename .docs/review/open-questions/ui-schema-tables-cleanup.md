# Open questions: Schema Tables cleanup + kill Custom Fields

**Stem:** `ui-schema-tables-cleanup`  
**Date:** 2026-10-01  
**Status:** Packet OPEN; implement CLOSED. Prior `ui-schema-ddl` locks stand.

## OQ-1 — P1 Schema Tables allow-list (OPEN — Marc)

Besides **`project`** and **`samples`**, which other tables are P1 for the Schema Tables list?

| Option | Meaning |
|--------|---------|
| **A** | `project` + `samples` + **any UI-created tables only** |
| **B** | Also include named system tables (e.g. containers, tests, clients, …) — Marc names the set |

**Rolf gate question (2026-10-01):** awaiting Marc. Spec will not freeze allow-list until Decided.

## OQ-2 — Custom Fields / `custom_attributes` cutover (OPEN)

Existing Custom Fields data / JSONB keys on samples (or elsewhere):

| Option | Meaning |
|--------|---------|
| **A** | Park: hide UI; leave data unread by new schema path; migrate later |
| **B** | One-shot migrate named keys → real columns (allow-listed) then drop Custom Fields path |
| **C** | Refuse: wipe / ignore with confirm (destructive — needs Marc Confirm) |

Brief must Decide before implement.

## OQ-3 — Registry rows for system tables (OPEN — Heidi)

For `project` (and other system tables once in allow-list): seed **table + column registry** rows how?

| Option | Meaning |
|--------|---------|
| **A** | Alembic seed on deploy for allow-listed system tables |
| **B** | Lazy register on first Schema Tables view |
| **C** | Admin “Register” action before Columns editable |

## OQ-4 — Which surfaces still show “custom” language (OPEN — Mathilda)

Any residual “custom attribute” labels on receive / results / list filters must be removed or renamed. Mathilda maps screens in sketch.


## OQ-5e — M:N junction visibility (OPEN unless Marc overwrites)

**Leadership lock (Decided 2026-10-01):** M:N junctions stay **behind the scenes**. Admin with `schema:edit` defines the relation; the product **creates/maintains** the junction table and its rows. Operators only **link / unlink** — no junction as a lab data-entry table or spreadsheet of link rows.

**Default (Rolf; Marc may overwrite):** auto-junction is **visible to `schema:edit` only** (Schema Tables as read-only metadata), **never** in operator layouts.

| Option | Meaning |
|--------|---------|
| **A (default)** | Visible in Schema Tables to `schema:edit` only; never on operator layouts |
| **B** | Fully hidden even from Schema Tables (Admin only sees the named M:N relation, not the junction table row) |
| **C** | Marc overwrite — other |

## Decided (from prior packet — do not reopen)

- OQ-16: JSONB-as-**config** Fail; JSONB payload/instrument **data** OK.
- `schema:edit` Admin-only; layout = membership; privileges ≠ layout.
- CREATE TABLE / ADD COLUMN Hybrid apply stands.
- Relations: 1:N / 1:1 / M:N = real FK / unique FK / junction (Leadership 2026-10-01); JSONB related-ids Fail.
- M:N junctions **behind the scenes**; operators link/unlink only; default visibility = `schema:edit` only, never operator layouts (OQ-5e; Marc may overwrite).

## OQ-5 — Relations cardinality + UI + on-delete (OPEN — Spec / Mathilda / Heidi)

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
| OQ-5b | On-delete policy defaults: **RESTRICT** vs **SET NULL** vs **CASCADE** (per relation? global default?) |
| OQ-5c | Operator UX: **Related list** on the parent vs FK field only vs both |
| OQ-5d | Which allow-listed pairs may relate in P1 (blocked until OQ-1) |

**Tobias:** any relation stored only in JSONB/`custom_attributes` → **Fail**.

