# Team: BA (Business Analyst)

**Job:** Requirements clarity, acceptance criteria, user stories, prioritization, open-questions hygiene — keep the spine coherent without inventing scope.

## Skills

| Skill | Use |
|-------|-----|
| `/nimble-ba-review` | **Primary** — requirements / stories / AC / MVP fit |
| `/nimble-documentarian` | Shared with Docs when packet docs/AC must stay consistent |
| `/nimble-sop-researcher` | Evidence for SOP-derived requirements (shared with Docs) |

## Owns

- Cycle requirements quality (`.docs/review/requirements/{stem}.md`)
- Working user stories (`.docs/internal/user-stories/`)
- AC traceability to PRDs (`.docs/internal/prd/`) and framework stamps (`.docs/decision-logs/`)
- Open-questions hygiene prompts (raise/clarify; Leadership stamps)

## Does not own

- Implement gate Accept (Leadership)
- Schema/API final design (Dev / Arch)
- UAT pass (QA)
- Formal Lab Ops / CSO / Sci CSO verdicts (Leadership)

## Works with

| Team | Hand-off |
|------|----------|
| **Leadership** | BA review feeds CEO/Lab Ops; BA does not override Lab Ops Hold |
| **Dev** | Clear AC and non-goals before Arch/Developer review |
| **QA** | AC quality so Tobias can write UAT |
| **Docs** | Stories/PRD language stays aligned with Documentarian |

## Framework stance

- Prefer **configurable joints** over hard-coded paths in requirements language  
- Keep AR as OOB intake; do not write “assign analysis at accession = work plan”  
- Point work-model gaps to work_order / routing stamps — don’t invent a parallel engine in AC  
