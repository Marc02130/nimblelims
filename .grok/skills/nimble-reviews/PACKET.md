# NimbleLIMS formal review packet (shared)

All formal review skills share this packet model. Do not invent parallel folders or verdict language.

## Feature stem

One slug for the cycle, e.g. `experiment-template-entries`, `data-parsers-lims-runs`.

| Role | Path |
|------|------|
| Requirements | `.docs/requirements/{stem}.md` (or linked PRD section) |
| Tech sketch | `.docs/tech-sketch/{stem}.md` |
| Schema delta | `.docs/schema-changes/{stem}.md` (if DB) |
| Lab Ops review | `.docs/lab-ops-review/{stem}.md` |
| CEO review | `.docs/ceo-review/{stem}.md` |
| UI review | `.docs/ui-review/{stem}.md` |
| Architecture review | `.docs/architecture-review/{stem}.md` |
| Security review | `.docs/security-review/{stem}.md` |
| Open questions | `.docs/open-questions/` (decision log) |
| Checklist | `.docs/checklist/` as applicable |

## Pipeline order (full path)

```
Requirements → Tech sketch
    → Lab Ops (required for ELN/LIMS lab workflows)
    → CEO / UI / Architecture / Security (parallel after Lab Ops has spoken when possible)
    → Open questions cleared
    → Implement (phased)
    → Dogfood → UAT → merge main
```

See `.docs/development-process/README.md`.

## Verdict language (all formal reviews)

| Verdict | Meaning |
|---------|---------|
| **Accept** | Ship as designed for named scope |
| **Accept with conditions** | Ship only if listed conditions land in the **same phase** |
| **Revise** | Update requirements / sketch before implement |
| **Hold** | Do not implement this slice until named work is specified |

Condition ID prefixes by review:

| Review | Prefix |
|--------|--------|
| Lab Ops | L1, L2, … |
| CEO | C1, C2, … |
| UI | U1, U2, … |
| Architecture | A1, A2, … |
| Security | S1, S2, … |

## Artifact header (minimum)

Every review doc must open with:

```markdown
# {Review type}: {Title}

**Date:** YYYY-MM-DD  
**Status:** Accept | Accept with conditions | Revise | Hold  
**Tech sketch:** link  
**Related reviews:** links (Lab Ops / CEO / …)

## Executive summary
…

## Conditions (if any)
| ID | Severity / note | Condition |
|----|-----------------|-----------|

## Verdict
| Field | Value |
|-------|--------|
| **Verdict** | … |
| **Date** | … |
```

## Lab Ops gate

For ELN experiments, templates, entries, processes, sample journey, LIMS runs, parsers, accessioning/containers/batches when sample flow changes:

- Lab Ops **Hold** or missing → **implement gate closed**
- Other reviews Accept without Lab Ops Accept / Accept-with-conditions on lab-facing work → **invalid for implementation**

## gstack path resolution

Prefer, in order:

1. `~/.claude/skills/gstack/{skill}/SKILL.md`
2. Repo `.agents/skills/gstack/{skill}/SKILL.md` if vendored
3. `~/.claude/skills/gstack/.agents/skills/gstack-{skill}/SKILL.md`

If unreadable, state that gstack is missing and complete the Nimble sections only (still write the artifact).

## Read-only vs implement

Formal reviews are **review artifacts only**. Do not implement product code unless the user explicitly asks after the review is done.
