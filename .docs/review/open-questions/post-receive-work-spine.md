# Open questions: post-receive-work-spine

**Status:** Living decision log  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| OQ-AF-1 | Asked-for UI: dedicated `/asked-for` vs sample-detail only? | **Decided (provisional)** | P1 | **Both:** `/asked-for` backlog + sample detail section. Not on receive. | 2026-08-28 | Leadership |
| OQ-AF-2 | Permission: new `order:create` vs reuse `test:assign`? | **Decided (provisional)** | P1 | Reuse **`test:assign`**. Do not add a permission this phase. | 2026-08-28 | Leadership |
| OQ-AF-3 | Param defs required in P1 or empty-object only? | **Decided (provisional)** | P1 | Table ships; OOB may have zero defs. Empty `params` OK. Unknown keys 422. | 2026-08-28 | Leadership |
| OQ-TAT-1 | TAT overlap matching when two ranges overlap? | **Decided (provisional)** | P2 | **Refuse overlap on save** (409 / gist exclude). No first-match. | 2026-08-28 | Leadership (was open on framework stamps) |
| OQ-WO-1 | Auto-route on asked-for create vs explicit Route button? | **Open** | P2 UX | P1 has no routing. P2 default proposal: auto-route if map matches; else stay `requested` with CTA. | | Product + UI |
| OQ-WO-2 | work_order field list beyond chain + status? | **Decided (provisional)** | P2 | Snapshot chain, FKs to asked-for/sample/analysis, status, optional process_id. No due_date copy (use asked-for TAT). | 2026-08-28 | Arch |
| OQ-WO-3 | Single FK: `work_orders.process_id` vs `eln_processes.work_order_id`? | **Decided (provisional)** | P2 schema | SoT = **`eln_processes.work_order_id`** (Arch A6). | 2026-08-28 | Arch |
| OQ-RES-1 | Qualifiers shape for typed number? | **Decided** | P3 | **Typed token → `reported_result`.** `qualifiers` stays UUID FK to Result Qualifiers (`<LOD`, `ND`); NULL for a clean number. `raw_result` may copy the token on the manual path. **Reject** JSON `{"entered_as":…}` in `qualifiers` (type collision + destroys LOD/ND). No `results.unit_id`. Fold into RQ-RES-1 / AC-P3-1 (SC1–SC4). | 2026-08-28 | Sci CSO |
| OQ-SOP-1 | Apply always create process def, or user picks template vs process? | **Decided (provisional)** | P4 | **Always process definition** as success path. Template created only if an experiment step needs it. | 2026-08-28 | Leadership |
| OQ-SOP-2 | May Apply write inactive parser draft? | **Decided (provisional)** | P4 | **Yes, inactive and unbound** (S11). No bind to production runs. | 2026-08-28 | Security |
| OQ-IMP-1 | Is P5 blocked on anything in P1–P4? | **Decided** | P5 | **No.** May proceed in parallel after P1 if staffing allows. | 2026-08-28 | Leadership |

## Gate rule

- **P1:** Unblocked (OQ-AF-*).  
- **P2:** TAT overlap decided. OQ-WO-1 still Open (UX). OQ-WO-3 Decided (`eln_processes.work_order_id`). Type-eligibility column (A4) before P2 coding.  
- **P3:** OQ-RES-1 **Decided**. Persist lock waits SC1–SC4 already folding into RQ-RES-1.  
- **P4:** OQ-SOP-2 Decided (inactive unbound). Extract-hold dest type remains a **different** Hold.  
- **P5:** Unblocked.

Do not start a phase while its blocking rows are **Open**.
