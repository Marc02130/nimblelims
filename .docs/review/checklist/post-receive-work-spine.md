# Checklist: post-receive-work-spine

**Stem:** `post-receive-work-spine`  
**Last updated:** 2026-08-28

- [ ] not started · [~] in progress · [x] done · [-] deferred

## Reviews (2026-08-28)

- [x] Lab Ops — Accept with conditions (L1–L5)
- [x] CEO — Accept with conditions (C1–C9), HOLD SCOPE
- [x] UI — Accept with conditions (U1–U14)
- [x] Architecture — Accept with conditions (A1–A10)
- [x] Security — Accept with conditions (S1–S12)
- [x] Scientific CSO — Accept with conditions (SC1–SC5); OQ-RES-1 Decided
- [x] BA — Accept with conditions (BA1–BA7)
- [x] QA — Accept with conditions (QA1–QA12 P1)
- [x] Developer — Accept with conditions (D1–D11 P1)
- [x] Documentarian — Accept with conditions (DOC1–DOC9)

## P1 Asked-for

- [ ] Migration `asked_for` + `analysis_param_defs` + RLS
- [ ] API create/list/get/cancel
- [ ] UI `/asked-for` + sample detail
- [ ] Sidebar item
- [ ] Pytest: 409/403/422/zero Tests
- [x] UAT script P1
- [x] Manuals

## P2 work_order

- [ ] routing_map + overlap 409 (same analysis + overlapping TAT **and** overlapping first-step allow-lists; extract-first vs Qubit-first same TAT is legal)
- [ ] work_orders
- [ ] route + start
- [ ] WO-7 LimsRun start / publish refuse
- [x] UAT P2 live stamp — overall **unsigned** on `8cfa2a9` (freeze skip unsigned: `{}` ambiguous; later-step type-gate unsigned)

## P3 results persist

- [ ] persist_typed_result
- [ ] 422 missing units_default
- [ ] UAT fold AR-RES

## P4 SOP Apply

- [ ] Apply → process definition
- [ ] Optional inactive parser draft
- [ ] Manuals: SOP+AI is not a lie

## P5 parser setup

- [ ] Dry-run + activate UX
- [ ] AI setup-only still gated
