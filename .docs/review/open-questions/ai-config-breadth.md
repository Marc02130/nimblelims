# AI configuration breadth (beyond sample processing)

**Date:** 2026-09-20  
**Status:** **Parked** (Leadership north star sequencing)  
**Stamp:** [product-north-star-2026-09-20](../../decision-logs/product-north-star-2026-09-20.md)  
**Related guidance:** [ai-sop-north-star](../requirements/ai-sop-north-star.md) (sample-processing / SOP → process+parser; implement **CLOSED**)

## Question

When may we open AI-assisted configuration for surfaces **outside** sample-processing catalog authoring — e.g. login, reporting, storage setup, and other admin domains?

## Decision (provisional park)

| Item | Lock |
|------|------|
| **Now** | Do **not** open packets for AI config of login, reporting, storage, or similar |
| **Prerequisite** | Sample processing living ISSUES closed enough that Leadership restamps (E-10 Met; next E-14/E-12 → E-6/E-7; uniqueness 7.9/7.9b honesty with Tobias) |
| **Why** | Goal 1 (framework / DB config) must be solid on the execute path before goal 2 (AI proposes config) fans out |
| **Still in scope as guidance** | SOP → process + parser north star remains the differentiator for **sample processing** authoring — separate from this breadth park |

## Non-goals of this note

- Implement MCP / vector pipeline  
- Rewrite living UAT Pass stamps  
- IC50 / product code  

## Unpark rule

Leadership restamp after sample processing close. Until then: track only; no Spec packet, no implement gate.
