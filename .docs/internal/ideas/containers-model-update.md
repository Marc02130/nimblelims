# Idea: Containers model update

**Status:** Placeholder — product rules **Decided**; schema/UI **not implemented**  
**Date:** 2026-08-11  
**Related:** [open-questions/containers.md](../open-questions/containers.md) (locks); [manuals/containers.md](../manuals/containers.md); [materials-and-lot-tracking.md](materials-and-lot-tracking.md); experiment aliquot/pool (tech sketch §0.8)

## One-liner

Bring code and admin UX in line with the locked container inventory model: nested multi-element → single-element → contents; **solute mass only** (diluent not mass); type shape as **rows × columns** (drop free-text dimensions); **contents only on 1×1** vessels.

## Current state (NimbleLIMS)

| Exists | Gap vs locked model |
|--------|---------------------|
| `ContainerType` with free-text `dimensions` | Need integer **`rows`** / **`columns`**; remove `dimensions` as grid shape |
| `Container` hierarchy via `parent_container_id` + instance `row`/`column` | Not enforced against type grid; multi-element can still get contents |
| `Contents` on any container | Must restrict to **single-element** types only (`rows=1` and `columns=1`) |
| `amount` / `concentration` on both container and contents | Semantics fuzzy; should mean **solute mass** (+ vessel total / conc for \( V = m/C \)) |
| Aliquot plan stores mass, never volume | Vessel amount/conc not always kept consistent on execute |
| Diluent | No first-class action; correctly **not** stored as mass (Option A locked) |

**Canonical decisions:** [open-questions/containers.md](../open-questions/containers.md).

## Why

- Free-text dimensions cannot drive plate/rack layout, child spawn, or validation.
- Contents on plates breaks the “well holds liquid” model and confuses pooling.
- Clear solute-mass + derived volume is required for dilution, aliquot, and display without inventing a volume column.
- Admin and accessioning UIs still teach the old fields.

## Direction (implement slice when prioritized)

1. **Schema**  
   - Add `container_types.rows`, `container_types.columns` (INTEGER NOT NULL, ≥ 1).  
   - Drop `container_types.dimensions`.  
   - Backfill: well/tube → 1×1; 96-well plate → 8×12 (and other seeds); unknown → 1×1 with review.  
   - Optional DB check: contents only when type is 1×1.

2. **API / validation**  
   - Reject `Contents` create/update if container type is multi-element.  
   - Validate child `row`/`column` against parent type rows/columns.  
   - Document vessel amount/conc as single-element inventory only.

3. **Create multi-element containers**  
   - Decide: auto-spawn child 1×1 instances (wells/slots) vs create on demand.  
   - Naming for children (e.g. `PLATE-001-A1`).

4. **Admin UI**  
   - Container type form: rows + columns (not Dimensions).  
   - Show element count = rows × columns; badge single vs multi.

5. **Runtime UX**  
   - Accessioning / container management: only 1×1 types for sample contents.  
   - Display derived volume when mass + conc present.  
   - Aliquot/dilute execute: keep content mass and vessel amount/conc consistent.

6. **Tests / UAT / seeds**  
   - Update fixtures, UAT container scripts, seed types.

## Non-goals (this idea)

- Materials/reagent lots (diluent lot tracking) — [materials-and-lot-tracking.md](materials-and-lot-tracking.md).  
- Polymorphic contents beyond sample (cells/compounds as first-class types).  
- Lab freezer/room location hierarchy beyond container parent nesting — [lab-locations.md](lab-locations.md).  
- Rewriting dose-response `TemplateWellDefinition` (template layout stays separate from inventory containers).

## Open when prioritized

- Auto-spawn all children on multi-element create vs lazy create.  
- Whether vessel `Container.amount` is always sum of contents or independently editable.  
- Migration strategy for any existing multi-element containers that already have contents.  
- Capacity field: keep as optional physical max volume vs de-emphasize in favor of derived volume only.

## Suggested process when pulled into a cycle

Ideation (this doc) → requirements → tech sketch / schema-changes packet → reviews as needed → implement → docs sync → dogfood/UAT.

Do not start implementation until this idea is scheduled; locks in open-questions already block wrong designs.
