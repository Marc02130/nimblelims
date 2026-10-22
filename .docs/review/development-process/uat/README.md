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

Share only when the scan exits 0 and the pack helper writes the `.tgz` plus its SHA-256. The default reviewed allowlist is [`scripts/uat_evidence_allowlist.json`](../../../../scripts/uat_evidence_allowlist.json) (canonical path plus SHA-256; no line entries; never by extension or path suffix; duplicate or non-canonical allowlist paths exit 2). A non-zero exit lists hits (`printed once`, a mixed 24-character pool window, a configured secret including in names, `$2[aby]$`, dump/PGDMP, an archive signature including the gzip-after-junk 32-candidate cap, a binary that is not on that allowlist, an unsafe name, a duplicate identity, a link/special file, a 64 MiB (67108864 byte) folder-total size-cap miss, a JWT with a JSON `alg` header found by a linear-time scan (lazy `re.finditer` 3-run window, at most 16 `eyJ` candidates per run and reaching that bound is an unsuppressible jwt hit that redacts the whole run through every following dot-joined run, early return when the line has no `eyJ`; a long header still searches its last 32 KiB; a header over 32 KiB / 32768 that contains `eyJ` and forms a dotted triple takes the same bound path if that window misses so a glued token cannot leak; tar-output newlines collapse with adjacent dots into one `.`; payload bounded at 8192; a signature over 8192 is still a hit and is fully redacted; percent-decode until unchanged, max 3, including `%u002E`; NFKC before matching; tar-unescape only on names and tar output, never file content; a `%2E`/`%252E`-encoded token is a jwt hit, not a pool hit; encoded runs redact before raw JWTs; one pass per line when percent-decoding and tar-unescape do not change the text), or an unreadable path). File content uses a JWT-only unescape pass; JSON `\uXXXX` is not a pool hit. Four or five percent layers fail closed and the whole run is redacted. Tar unescape repeats to a fixed point (double-escaped `\\056` leaves no 8-gram). Plain many-backslash text is not an encoded-run hit. A missing `--secrets-file` exits 2. `LZIP`/`Rar!` UTF-8 text is not an archive. PNG chunks outside `IHDR`/`PLTE`/`IDAT`/`IEND`/`sRGB`/`pHYs`/`gAMA`/`cHRM`/`tRNS`/`iCCP`, a truncated, length-overflowed, or oversized fixed-length chunk, an invalid `PLTE` size, a `tRNS` that does not fit the color type, an `iCCP` that fails name / method-0 / 1 MiB bounded-zlib / placement checks, `tEXt`/`zTXt`/`iTXt`/`eXIf` or an unknown chunk, a complete non-`IHDR` first chunk, or a bad CRC are png-trailing; trailing bytes on a walkable stream are walked by length; an unwalkable PNG with `IEND` plus tail is png-trailing; reviewed magic-plus-bytes PNGs stay refuse-binary. A compact `YYYYMMDDThhmm[ss][Z]` token bounded by non-alphanumerics is not a pool hit; overlap uses the core `YYYYMMDDThhmm` only, so a glued pool password still hits. A backslash-dot is a tar escape. 60/72/PEM/xxd wraps and `\u002e`/`\x2e` are JWT hits. `shlex`-dropped secrets-file values exit 2) and no `.tgz` is written. Name hits print `<redacted name hmac:xxxxxxxx>` and never the secret. Failed tar stderr, name hits, and verify output are redacted JWTs first (tar-unescape to a fixed point and NFKC, then encoded runs, then raw tokens), then configured secrets (NFKC / `quote` / raw-backslash needles) and pool windows matched on that prepared copy so a backslash, tab, or quote cannot leave a tail. Secret matching walks every unescape layer (no size-based skip) so a several-MiB stderr still redacts a depth-2–7 escaped configured secret; leftover escapes after 8 peels fail-closed on each `\S+` token that contains a backslash. `\u002e` / `\x2e` / `\X2E` / `\u{2e}` / `\U0000002e` / `&#46;` map in one linear `re.finditer` pass. Wrapped 76-column standard base64, PEM, and MIME bodies decode to a JWT. xxd default, `-p`, and `-g1` hex dumps join. Octal needles escape only bytes `>= 0x80`. Unbalanced quotes in `--secrets-file` exit 2. A peel that would emit more than 65536 escape pieces fail-closed instead of materializing a multi-gigabyte pair-run. Every printed pack path goes through `redact_name_path`; an archive or output name that matches a secret rule is refused. The pack helper scans the extracted evidence directory, name-scans the packed folder name, and requires a byte-identical rebuild with the same GNU tar, `--mode=u=rwX,go=`, extract `-p`, and `gzip -n -9`.

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
