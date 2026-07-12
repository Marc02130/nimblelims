# Dogfood

**Stage in process:** After **implementation** and **docs sync**, **before UAT** and **before merge to `main`**.

## What it is

Internal use of a feature that is **not yet production** (feature branch, staging, or preview deploy). “We use our own product” with realistic workflows.

## What it is not

| Dogfood | Not dogfood |
|---------|-------------|
| Real tasks, messy data | Only happy-path demo |
| On branch/staging | Already on production `main` |
| Find UX/bugs early | Formal scripted pass/fail (that’s **UAT**) |

## Prerequisites

1. Implementation for the phase is done enough to exercise.  
2. **Docs sync** so a colleague can follow how to try the feature.  
3. Environment available (local compose, staging, etc.).

## How to run

1. Deploy or run the **feature branch** / staging build.  
2. Exercise primary user paths (e.g. for parsers: create instrument → parser → test files → run import).  
3. Note confusion, errors, missing docs.  
4. File issues or checklist items; **fix blockers** before UAT.

## Exit criteria

- Feature exercised (prefer non-author).  
- Blockers fixed or explicitly accepted.  
- Optional log file: `dogfood/<feature-stem>.md` (date, who, env, findings).

## Log template

```markdown
# Dogfood: <feature>

**Date:**  
**Who:**  
**Env:** branch / staging URL  
**Build / commit:**  

## Paths tried
- 

## Findings
| Severity | Issue | Action |
|----------|-------|--------|
| Blocker / Major / Minor | | Fix / accept |

## Ready for UAT?
Yes / No — why
```

## Related

- [Parent process](../README.md)  
- [UAT](../uat/README.md)  
