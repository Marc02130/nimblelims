# UAT (User Acceptance Testing)

**Stage in process:** After **dogfood**, **before merge to `main` / production**.

## What it is

**Scripted** product acceptance: a human follows a written script and records pass/fail against requirements for this phase/feature.

## What it is not

| UAT | Not UAT |
|-----|---------|
| Scripted cases with expected results | Ad-hoc clicking (closer to dogfood) |
| Product acceptance gate for merge | Unit/integration CI (those run during implementation) |
| Pre-production | Production monitoring after merge |

## Where scripts live

| Location | Use |
|----------|-----|
| **[`UAT_Scripts/`](../../../UAT_Scripts/)** | Primary home: `uat-<topic>.md`, runners, `*_results.md` |
| **This folder** | Process notes, templates, optional feature-specific UAT notes |

Prefer adding scripts next to existing UAT scripts so operators find them in one place.

## Prerequisites

1. Implementation complete for the scoped phase.  
2. Docs sync (manuals / README) so steps match the UI.  
3. Dogfood complete (or waived with owner + reason).  
4. Test environment with known logins (see project README / admin-setup).

## How to run

1. Open the feature’s `UAT_Scripts/uat-*.md` script.  
2. Execute each case; mark pass/fail.  
3. Capture evidence (screenshots, IDs) for failures.  
4. **All must-pass cases green** (or written waiver) before merge.

## Exit criteria

| Result | Action |
|--------|--------|
| **Pass** | Eligible to **merge to `main`** → production |
| **Fail** | Fix on branch → re-dogfood if needed → re-UAT → then merge |
| **Waiver** | Document who, why, residual risk; still record in results |

## Script outline (template)

```markdown
# UAT: <feature>

**Phase:** P0 / P1 / …  
**Requirements:** link  
**Env:**  
**Build / commit:**  
**Executor:**  
**Date:**  

## Preconditions
- 

## Cases

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| 1.1 | | | | |

## Sign-off
Pass / Fail — signature
```

## Related

- [Parent process](../README.md)  
- [Dogfood](../dogfood/README.md)  
- Existing scripts: [`UAT_Scripts/`](../../../UAT_Scripts/)  
