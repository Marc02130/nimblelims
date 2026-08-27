---
name: nimble-arch-review
description: >
  Formal NimbleLIMS architecture review of a feature packet. Thin wrap of gstack
  plan-eng-review: data model, APIs, migrations, contracts, failure modes, tests.
  Writes .docs/review/architecture-review/{stem}.md and verifies schema-changes when needed.
  Use when: "architecture review", "arch review", "nimble arch", "eng review of the sketch",
  "lock the architecture".
user-invocable: true
---

# Nimble architecture review (formal wrap of gstack plan-eng-review)

Shared packet rules: `.grok/skills/nimble-reviews/PACKET.md`.

## Persona

Staff/systems engineer: boundaries, contracts, migrations, observability, blast radius.  
**Not** diff code review (use gstack `/review` pre-land).

## Steps

### 1. Resolve packet

1. Feature **stem**.
2. Read:
   - `.docs/review/tech-sketch/{stem}.md`
   - `.docs/review/schema-changes/{stem}.md` (required if DB claims)
   - Requirements, Lab Ops/CEO conditions that bind implement
   - Prior `.docs/review/architecture-review/{stem}.md`
3. Flag if schema-changes missing but sketch implies migrations → condition **A\*** or Revise.

### 2. Nimble architecture checklist

| Area | Check |
|------|--------|
| Entry kinds / contracts | Grid wide, export long, save vs submit |
| Write-back | Submit-only; allowlist; no accessioning identity |
| Cohort | ExperimentSampleExecution and/or lims_runs.cohort lock |
| Aliquot execute | Transactional amount reduce; dest samples; methods matrix |
| Multi-tenant / RLS | Client isolation on samples, entries, runs |
| Migrations | Matches schema-changes; rollback story |
| APIs | Auth (experiment:manage etc.), error shapes |
| Failure modes | Insufficient amount, deps not met, empty grid |
| Tests | Packet spine tests named |

Conditions: **A1, A2, …**

### 3. Run gstack plan-eng-review

Read and follow:

```
~/.claude/skills/gstack/plan-eng-review/SKILL.md
```

Plan under review = tech sketch + schema-changes. Emphasize architecture + tests sections; map recommendations to Nimble checklist.

### 4. Write formal artifact

`.docs/review/architecture-review/{stem}.md`:

```markdown
# Architecture Review: {Title}

**Date:** YYYY-MM-DD  
**Status:** Accept | Accept with conditions | Revise | Hold  
**Tech sketch:** link  
**Schema changes:** link or N/A  

## Executive summary
…

## System shape (ASCII if helpful)
…

## Conditions
| ID | Condition |
|----|-----------|
| A1 | … |

## Test expectations
…

## Verdict
| Field | Value |
|-------|--------|
| **Verdict** | … |
```

### 5. Schema-changes alignment

If DB work: confirm `.docs/review/schema-changes/{stem}.md` lists every delta; if sketch drifted, require update (Revise or A\* condition).

### 6. Exit line

```
ARCHITECTURE REVIEW: {verdict}
SCHEMA-CHANGES: present | missing | N/A
```

## What not to do

- Do not merge architect review into code review.
- Do not implement migrations unless asked after Accept.
