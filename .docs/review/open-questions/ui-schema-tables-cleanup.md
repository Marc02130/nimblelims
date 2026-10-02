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

## Decided (from prior packet — do not reopen)

- OQ-16: JSONB-as-**config** Fail; JSONB payload/instrument **data** OK.
- `schema:edit` Admin-only; layout = membership; privileges ≠ layout.
- CREATE TABLE / ADD COLUMN Hybrid apply stands.
