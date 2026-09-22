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
2. Layout Apply must **not** fight living **receive / asked-for** locks.  
3. Bench copy must keep **Hide vs Read-only vs Deny** loud — layout hide is not privilege deny.  
4. **Lab Ops consult** before any UI-created table is given a **runtime** screen.

## Aligns

- Four Admin→Schema surfaces (Tables / Columns / Layouts / Privileges).  
- OQ-16 JSONB = payload data only; not config.  
- Tobias Fail bars (1)–(5).

## Gate

Implement remains **CLOSED**. Original conditions stand (this note is not a Lab Ops restamp).

**Fold note 2026-09-22:** [Brief](../requirements/ui-schema-ddl-brief.md) written — OQ-4–13 **Decided** (incl. OQ-4–11). Günter **Accept with conditions** (S-UI-1…6) already on packet (`50141c5`). Still waiting **Design Group UX Accept** and **Günter restamp** that S-UI-1…6 hold under the Brief. Layout vs receive/asked-for, Hide vs Read-only vs Deny, and Lab Ops consult before a new-table runtime screen are baked into the Brief.
