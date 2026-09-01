# Nimble Grok teams

**Date:** 2026-08-26  
**Purpose:** Group review/supporting skills into four teams for routing work.

## Docs layout (everyone)

Marc reorganized docs under **`.docs/`**:

| Path | Role |
|------|------|
| `.docs/review/` | Committed review spine (was `.docs-review/`) |
| `.docs/internal/` | Working PRDs / specs / design / ideas (was `.docs-internal/`; git-tracked) |
| `.docs/discussions/` | Multi-persona discussions |
| `.docs/decision-logs/` | Stamps |

Update skill artifacts and Agents.md to use these paths. Do not invent a third tree.

## Teams

| Team | Folder | Job |
|------|--------|-----|
| **Leadership** | [leadership/](leadership/TEAM.md) | Scope, bench, science, security — implement gate |
| **BA** | [ba/](ba/TEAM.md) | Requirements, AC, user stories, prioritization |
| **Dev** | [dev/TEAM.md](dev/TEAM.md) | Architecture, implementability, UI |
| **QA** | [qa/TEAM.md](qa/TEAM.md) | Testability, UAT, fixtures |
| **Docs** | [docs/TEAM.md](docs/TEAM.md) | Living docs, research, hand-off hygiene |

## Default packet flow

```text
Leadership (Lab Ops → CEO + CSOs)
        ↓
BA (requirements / AC / stories)
        ↓
Dev (Arch + Developer + UI)
        ↓
QA (QA + Test Data)
        ↓
Docs (Documentarian)
```

Or: `/nimble-review-packet {stem}` then deepen by team.
