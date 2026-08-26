# Discussion: Domain ISSUES sync — Leadership · BA · Dev

**Date:** 2026-08-26  
**Status:** Working sync (not implement gate)  
**Inputs:** Updated PRDs/SPECs under `.docs/internal/`; [framework stamps](../decision-logs/framework-stamps-2026-08-26.md); teams [`.grok/teams/`](../../.grok/teams/)  

---

## Leadership

- Keep **AR P0** as only OOB intake; do not revive wizard as framework.  
- **A-15 / X-5** resolved *directionally* by WO stamps — still **out of AR P0**; owned by processing work-order packet.  
- Prefer **omit analysis at receive** on default profile (PRD G5).  
- Containers: fixed inventory spine; types = config. Don’t soften Option A.  
- Processing: execute stack stays Process/Exp/LimsRun; missing middle = work_order + routing.

## BA

- Rewrite AC so “optional tests at receive” is not read as “work plan.”  
- Trace WO-2/3/7 into future requirements when work-order packet opens.  
- Fix stale path strings (`.docs-review` → `.docs/review`) in ISSUES.  
- User stories: receive = identity+vessel; order/params and work list are separate stories.

## Dev

- **Accessioning P0:** one receive service + txn; no profile engine yet; don’t build dual APIs.  
- **Containers:** C-1/C-8 (rows×columns + 1×1 contents enforce) pair well with AR first vessel; schedule after or with AR.  
- **Processing:** don’t start work_order schema until Leadership opens packet; unblock extract-hold E-9 restamp separately.  
- Sidebar “active configs” (FW-1b) is a **shared shell** later — not AR P0 scope.

## Agreed ISSUES disposition

| Domain | P0 / next | Park |
|--------|-----------|------|
| Accessioning | A-5–A-8, A-9–A-11 | A-1–A-4 profiles engine; A-15 → processing |
| Containers | C-1, C-8, C-6/C-7 with AR | C-9, C-10, lots |
| Processing | Document WO stamps in index; E-9 restamp; E-10/E-14 | Full WO packet until opened; registration/lots |

Artifacts updated: `prd/*/ISSUES*.md`.
