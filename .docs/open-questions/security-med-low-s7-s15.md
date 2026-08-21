# Open questions: security-med-low-s7-s15

**Status:** Living decision log  
**Date:** 2026-08-21  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| OQ-S9 | Permission for `/results/validate`: enter\|review\|read vs enter\|review only? | **Open** | P1 S9 | Lean: enter + review + read (validate is read-ish). | | Product + Security |
| OQ-S11a | Narrow containers 0062 `created_by` FOR ALL vs accept residual? | **Open** | P3 S11 | Lean: tighten WITH CHECK to INSERT-only path; SELECT via project/contents. | | Arch + Security |
| OQ-S11b | Enable RLS on `contents`? | **Open** | P3 | Lean: enable + policy mirroring containers/samples in same phase if low risk; else Deferred. | | Arch |
| OQ-S12 | Prod compose: separate file vs Compose profiles? | **Decided (provisional)** | P3 | Prefer `docker-compose.prod.yml` overlay; local keeps published 5432. | 2026-08-21 | Eng |
| OQ-S14 | biotype/temperature: drop from write-back allowlist or from system-RO? | **Open** | P1 S14 | Lean: **drop from write-back allowlist**; keep as sample system display fields. | | Product |
| OQ-S15 | In-memory throttle vs Redis/table for multi-worker? | **Open** | P2 | Lean: in-memory v1 + note for multi-replica; Redis later. | | Eng |
| OQ-S10 | Expand S10 to httpOnly cookie JWT this cycle? | **Decided** | — | **No** — docs honesty only. | 2026-08-21 | CEO |

## Gate rule

- **P1:** can start after reviews Accept; **OQ-S14** and **OQ-S9** should be Decided before coding those FRs (or ship provisional lean).  
- **P3:** blocked on **OQ-S11a/b**.  
- **P2 S15:** provisional in-memory OK if OQ-S15 undecided.
