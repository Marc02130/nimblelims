# AI configuration breadth (beyond sample processing)

**Date:** 2026-09-20  
**Status:** **Partially unparked** (2026-09-22) — schema-config foundation OPEN; login/reporting/storage AI still parked  
**Stamp:** [product-north-star-2026-09-20](../../decision-logs/product-north-star-2026-09-20.md)  
**Related guidance:** [ai-sop-north-star](../requirements/ai-sop-north-star.md) (sample-processing / SOP → process+parser; implement **CLOSED**)

## Question

When may we open AI-assisted configuration for surfaces **outside** sample-processing catalog authoring — e.g. login, reporting, storage setup, and other admin domains?

## Decision (2026-09-22 restamp)

| Item | Lock |
|------|------|
| **Sample processing** | Critical path **Met** on `main` (E-10 → E-6) |
| **Unpark (blocker only)** | Open **UI schema DDL** foundation — real CREATE TABLE / ADD COLUMN + **table/column registries** + **role-based layout** + **table/column privileges** ([`ui-schema-ddl` requirements](../requirements/ui-schema-ddl.md), [OQs](ui-schema-ddl.md)). This is goal-1 robust config so goal-2 AI has something honest to configure. |
| **Still parked** | AI config packets for **login**, **reporting**, **storage**, and similar admin domains |
| **Why** | Leadership: AI needs real schema-config first; do not fan out AI breadth until that layer exists |
| **Still in scope as guidance** | SOP → process + parser north star for **sample processing** authoring — separate from login/reporting/storage |

## Non-goals of this note

- Implement MCP / vector pipeline  
- AI applying DDL  
- Rewrite living UAT Pass stamps  
- IC50 / product code  

## Unpark rule

- **Schema-config / `ui-schema-ddl`:** OPEN for Spec + sketches (implement gate still CLOSED until Heidi/Leadership Accept).  
- **Login / reporting / storage AI:** stay parked until Leadership restamps after schema-config foundation Met (or an explicit narrower unblock).
