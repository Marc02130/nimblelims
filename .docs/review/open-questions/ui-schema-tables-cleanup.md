# Open questions: Schema Tables cleanup + kill Custom Fields

**Stem:** `ui-schema-tables-cleanup`  
**Date:** 2026-10-01  
**Status:** Packet OPEN; implement CLOSED. UX sketch tip **`564fe6f`** pending Accept. Prior `ui-schema-ddl` locks stand.

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
| OQ-5b | On-delete policy defaults: **RESTRICT** vs **SET NULL** vs **CASCADE** (per relation? global default?). **Katinka SOP lean (not freeze):** RESTRICT on identity links (sample, barcode vessel); SET NULL only where link is optional. **Tobias Fail bar (7):** CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (provisional until OQ-5b freezes) |
| OQ-5c | Operator UX: **Related list / pickers** on parent or child (Mathilda) — never junction spreadsheet; FK field and/or Related list |
| OQ-5d | Which allow-listed pairs may relate in P1 (blocked until OQ-1) |

**Tobias:** any relation stored only in JSONB/`custom_attributes` → **Fail**. CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (bar 7; provisional until OQ-5b freezes).
