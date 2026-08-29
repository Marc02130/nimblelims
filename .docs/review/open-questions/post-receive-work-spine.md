# Open questions: post-receive-work-spine

**Status:** Living decision log  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| OQ-AF-1 | Asked-for UI: dedicated `/asked-for` vs sample-detail only? | **Decided (provisional)** | P1 | **Both:** `/asked-for` backlog + sample detail section. Not on receive. | 2026-08-28 | Leadership |
| OQ-AF-2 | Permission: new `order:create` vs reuse `test:assign`? | **Decided (provisional)** | P1 | Reuse **`test:assign`**. Do not add a permission this phase. | 2026-08-28 | Leadership |
| OQ-AF-3 | Param defs required in P1 or empty-object only? | **Decided (provisional)** | P1 | Table ships; OOB may have **zero** defs (working-note rows are **not seed**). Empty `params` OK. Unknown keys 422. | 2026-08-28 | Leadership |
| OQ-AF-6 | Conditional required (e.g. `protein_conc_mg_ml` only if `matrix=microsome`)? | **Decided** | P1 validation | **No built-in “required if” engine.** Params belong to the **analysis**. The person who sets up the analysis marks each key required or not. Unknown keys / missing required keys still 422. | 2026-08-28 | Leadership |
| OQ-AF-7 | Enum via `source_list_id` vs inline `allowed_values` jsonb? | **Decided (provisional)** | P1 schema | **Both columns.** Prefer list-backed when a Lists row exists; `allowed_values` for table-design / no list yet. | 2026-08-28 | Arch |
| OQ-TAT-1 | TAT overlap matching when two ranges overlap? | **Decided (provisional)** | P2 | **Refuse overlap for the same analysis on save** (409 / gist exclude). No first-match. | 2026-08-28 | Leadership (was open on framework stamps) |
| OQ-WO-1 | Auto-route on asked-for create vs explicit Route button? | **Decided** | P2 UX | **Tech hits Route.** Asked-for save never mints work. Route zero acceptable → 422; multiple acceptable → 409; exactly one mints. | 2026-08-29 | Leadership |
| OQ-WO-2 | work_order field list beyond route + status? | **Decided — superseded by Marc/Rolf ordered-route lock** | P2 | Snapshot ordered `process_definition[]`, asked-for/sample/analysis FKs, status. No due-date copy. | 2026-08-29 | Marc / Rolf |
| OQ-WO-3 | Process-instance linkage for an ordered route? | **Decided — superseded** | P2 schema | Each started `eln_process` points to the work order and records its route position. Unique `(work_order_id, route_position)`. Start instantiates first pending definition only. | 2026-08-29 | Marc / Rolf |
| OQ-WO-4 | Type eligibility on analysis vs execute steps? | **Decided — superseded** | P2 L2 | No map type field. Match analysis + TAT, then current type against each candidate’s first process / first Experiment-LimsRun list. Zero acceptable → 422; two or more → 409. Later starts gate current type then; empty fails closed. Dest-type Hold remains out. | 2026-08-29 | Marc / Rolf |
| OQ-RES-1 | Qualifiers shape for typed number? | **Decided** | P3 | **Typed token → `reported_result`.** `qualifiers` stays UUID FK to Result Qualifiers (`<LOD`, `ND`); NULL for a clean number. `raw_result` may copy the token on the manual path. **Reject** JSON `{"entered_as":…}` in `qualifiers` (type collision + destroys LOD/ND). No `results.unit_id`. Fold into RQ-RES-1 / AC-P3-1 (SC1–SC4). | 2026-08-28 | Sci CSO |
| OQ-SOP-1 | Apply always create process def, or user picks template vs process? | **Decided (provisional)** | P4 | **Always process definition** as success path. Template created only if an experiment step needs it. | 2026-08-28 | Leadership |
| OQ-SOP-2 | May Apply write inactive parser draft? | **Decided (provisional)** | P4 | **Yes, inactive and unbound** (S11). No bind to production runs. | 2026-08-28 | Security |
| OQ-IMP-1 | Is P5 blocked on anything in P1–P4? | **Decided** | P5 | **No.** May proceed in parallel after P1 if staffing allows. | 2026-08-28 | Leadership |

## Gate rule

- **P1:** Unblocked (OQ-AF-* decided, including AF-6: no conditional required).  
- **P2:** explicit Route; ordered `process_definition[]`; one process instance per later start with route position; no map sample-type field; zero acceptable routes 422; multiple acceptable routes 409. UI preserves process/step order and derives first-process / first-step types.
- **P3:** OQ-RES-1 **Decided**. Persist lock waits SC1–SC4 already folding into RQ-RES-1.  
- **P4:** OQ-SOP-2 Decided (inactive unbound). Extract-hold dest type remains a **different** Hold.  
- **P5:** Unblocked.

Do not start a phase while its blocking rows are **Open**.
