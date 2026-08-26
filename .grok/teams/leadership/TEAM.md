# Team: Leadership

**Job:** Product scope, bench truth, scientific integrity, security — open/close the implement gate.

## Skills

| Skill | Use |
|-------|-----|
| `/nimble-lab-ops-review` | **Required** for lab-facing ELN/LIMS |
| `/nimble-ceo-review` | Scope freeze / ambition |
| `/nimble-cso-review` | Security / AuthZ / STRIDE |
| `/nimble-scientific-cso-review` | Assays, results, QC, params |
| `/nimble-review-packet` | Orchestrate formal set |

**BA team** owns `/nimble-ba-review` day-to-day — see [../ba/TEAM.md](../ba/TEAM.md). Leadership still consumes BA output for gate decisions.

## Owns

- Framework-first product stamps (`.docs/decision-logs/`, `.docs/discussions/`)
- Domain PRD intent (`.docs/internal/prd/`)
- Implement gate language on review artifacts (`.docs/review/*-review/`)

## Does not own

- Code implementation
- Detailed AC / user-story authoring (BA team)
- UAT script authoring (QA leads; Leadership accepts)

## Framework stance (2026-08-26)

See `.docs/decision-logs/framework-stamps-2026-08-26.md` and `.docs/discussions/2026-08-25-what-is-a-good-framework.md`.

- Fixed spine; DB-configured joints  
- Receive ≠ order ≠ work_order ≠ Process/Exp/LimsRun  
- AR = OOB intake; work_order + routing next  
- `config:edit` for framework mutate / sidebar activate  
