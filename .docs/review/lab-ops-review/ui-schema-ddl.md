# Lab Ops review: UI-driven schema DDL

**Date:** 2026-09-22  
**Reviewer:** Deiter (Lab Ops)  
**Stem:** `ui-schema-ddl`  
**Packet tip cited:** `c6f0854` (`docs/ui-schema-ddl`)  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**OQs:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Not IC50. No product code.**

## Verdict

**Lab Ops Accept with conditions** (2026-09-22).

## Conditions

1. Implement remains **CLOSED** until **OQ-4–11** + **Günter** Accept + Leadership **Brief**.  
2. Layout Apply must **not** fight living **receive / asked-for** locks. **receive / asked-for** = select samples then enter (simple).  
3. Layout defines **displayed** columns (absent = not shown); **read/write** = role privileges. **Retract** three-mode Hide / Read-only / Deny bench copy (Marc overwrite Confirm).  
4. **Lab Ops consult** before any UI-created table is given a **runtime** screen.  
5. **List pages** show role layout columns; on-the-fly add/remove columns is **ephemeral** (not stored in layout).  
6. **Multi-row** = table with role data-type layout; **single record** = form.

## Aligns

- Four Admin→Schema surfaces (Tables / Columns / Layouts / Privileges).  
- OQ-16 JSONB = payload data only; not config.  
- Tobias Fail bars (1)–(5).

## Gate

Implement remains **CLOSED**. Original conditions stand (this note is not a Lab Ops restamp).

**Fold note 2026-09-22:** [Brief](../requirements/ui-schema-ddl-brief.md) written — OQ-4–13 **Decided** (incl. OQ-4–11). Günter **Accept with conditions** (S-UI-1…6) already on packet (`50141c5`). Still waiting **Design Group UX Accept** and **Günter restamp** that S-UI-1…6 hold under the Brief. Layout vs receive/asked-for and Lab Ops consult before a new-table runtime screen are baked into the Brief. Three-mode Hide/Read-only/Deny copy **retracted**.

**Fold note 2026-09-23 (Marc Leadership overwrite; Rolf Confirm):** receive/asked-for select-then-enter; list ephemeral columns; layout = display; privileges = R/W; multi-row table vs single-record form.

**Confirm 2026-09-23 (Deiter; Rolf):** Marc Leadership overwrite Confirmed. Three-mode Hide/Read-only/Deny copy **retracted** — layout = display; privileges = R/W. Implement CLOSED.
