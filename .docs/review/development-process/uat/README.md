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

Seed passwords for UAT use `--secrets-out` only. See [`UAT_Scripts/uat-seed-secrets.md`](../../../UAT_Scripts/uat-seed-secrets.md) and [`manuals/uat-artifacts.md`](../../../manuals/uat-artifacts.md).

## Publish evidence

Before sharing a folder:

1. Keep backups in `/workspace/.uat-backups/<round>/`. They are never inside evidence.
2. If a log still has a `printed once` header, run `python scripts/mask_printed_once.py` and keep only the filtered copy.
3. Scan the plain folder, then pack only if it is clean:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence
python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
python scripts/pack_uat_evidence.py --verify evidence.tgz
```

Share only when the scan exits 0 and the pack helper writes the `.tgz` plus its SHA-256. The default reviewed allowlist is [`scripts/uat_evidence_allowlist.json`](../../../../scripts/uat_evidence_allowlist.json) (canonical path plus SHA-256; no line entries; never by extension or path suffix; duplicate or non-canonical allowlist paths exit 2). A non-zero exit lists hits (`printed once`, a mixed 24-character pool window, a configured secret including in names, `$2[aby]$`, dump/PGDMP, an archive signature, a binary that is not on that allowlist, an unsafe name, a duplicate identity, a link/special file, a 64 MiB (67108864 byte) size-cap miss, or an unreadable path) and no `.tgz` is written. Name hits print `<redacted name hmac:xxxxxxxx>` and never the secret. The pack helper scans the extracted evidence directory, name-scans the packed folder name, and requires a byte-identical rebuild with the same GNU tar and `gzip -n -9`.

Known limitation: CI API tests connect as the testcontainer superuser, not as `lims_app`.

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
- Backups and secrets: [`manuals/uat-artifacts.md`](../../../manuals/uat-artifacts.md)  
