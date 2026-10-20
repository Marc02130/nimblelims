# UAT: seed passwords and evidence

Stem: `seed-secrets`. No migration.

UAT does not read generated passwords from stdout. `seed_dev_passwords.py --apply` for a UAT round always passes `--secrets-out`.

Backup and secrets policy: [manuals/uat-artifacts.md](../manuals/uat-artifacts.md).

## Preconditions

- Fresh or known database. Personas are locked until `--apply`.
- `--secrets-out` path is a new file outside the evidence folder, outside `/workspace/.uat-backups/`, and outside `/tmp`.
- The parent directory exists. The file must not exist yet.

## TC-SECRETS-001 — Write passwords to a new 0600 file

```bash
python backend/seed_dev_passwords.py --apply \
  --secrets-out "$HOME/uat-round-secrets.env"
```

Expect:

- Exit 0.
- Stdout is only `Generated passwords written to $HOME/uat-round-secrets.env`.
- Stderr has connect/status lines and no password.
- The file mode is `0600`.
- A second run with the same path and no `--force` exits non-zero and does not change the file.
- `--force` writes a same-directory temp file (`O_CREAT|O_EXCL|O_NOFOLLOW`, mode `0600`) and replaces the target only after the database commit. A failed commit leaves the target unchanged and removes the temp file.
- `--force --only client` keeps other accounts' existing keys in that file and replaces only the selected ones.
- An existing symlink, directory, fifo, or dangling link at the `--secrets-out` path is refused, including when `--force` points at a symlink to a file outside the folder. The decoy stays unchanged.
- A missing parent directory or a dangling `--secrets-out` link exits non-zero even when every selected account already has an env password (nothing generated).
- Secrets-file keys must match `^DEV_SEED_[A-Z][A-Z0-9_]*$`. `PATH`, `HOME`, and `IFS` are refused.

Load the variables from that file into the shell that runs UAT:

```bash
set -a
. "$HOME/uat-round-secrets.env"
set +a
```

Do not paste the file into the evidence folder.

## TC-SECRETS-002 — Scan evidence before sharing

1. Build the evidence folder. Leave backups in `/workspace/.uat-backups/<round>/`. Do not put archives in the folder.
2. If a captured log still has a `printed once` header, filter it before it goes into evidence:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Do not share `captured.log`.

3. Scan the plain folder, then pack only if it is clean:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence
python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
python scripts/pack_uat_evidence.py --verify evidence.tgz
```

Expect exit 0 and `evidence scan clean`. The default reviewed allowlist is `scripts/uat_evidence_allowlist.json` (canonical path plus SHA-256, no line entries, never by extension or path suffix). `reviewed_by` and `approved_by` are Günter (CSO). Identities are the on-disk relative path. A sha entry may suppress only refused-binary and password-pool hits. Duplicate or non-canonical allowlist paths exit 2. A non-zero exit lists hits and the folder is not packed. Hits are a `printed once` header, a 24-character mixed pool-token window, a configured compose or seed secret (including in names), a bcrypt marker, a dump/PGDMP, an archive/compressed signature (including the gzip-after-junk 32-candidate cap), a binary that is not on that allowlist, an unsafe name, a duplicate identity, a link or special file, a size-cap miss, a JWT whose first segment decodes to JSON with `alg` (including in names), or an unreadable path. A dirty folder must produce no `.tgz`. Name hits print `<redacted name hmac:xxxxxxxx>` and never the secret. The pack helper scans the extracted evidence directory (so allowlist paths stay `ui/...png`), name-scans the packed folder name, and requires a byte-identical rebuild with the same GNU tar, `--mode=u=rwX,go=`, extract `-p`, and `gzip -n -9` so the hash does not depend on umask. `--verify` fails on a missing or mismatched sidecar, an extra top-level entry, a top-level symlink, or an archive that is not a clean rebuild. Failed tar stderr, name hits, and verify output are redacted JWTs first, then configured secrets, then pool windows. The size cap is a 64 MiB (67108864 byte) total for the folder. Pack and verify require GNU tar and GNU gzip. On macOS install Homebrew `gnu-tar` and `gzip` and put `/opt/homebrew/bin` first on PATH.

## TC-SECRETS-003 — Reviewed allowlist and r38 clean lines

1. Scan `backend/tests/data/r38_clean_lines.txt` in a folder with `--no-allowlist`. Expect exit 0.
2. Copy that file, inject a runtime-generated pool password, and scan again with `--no-allowlist`. Expect a pool-token hit. The password must not appear in the hit text.
3. Confirm `scripts/uat_evidence_allowlist.json` lists these two SHA-256 entries, each with non-empty `reviewed_by`, `approved_by`, and `date`:
   - `ui/r38_results_America_New_York.png`
   - `ui/r38_results_UTC.png`
4. Changing one byte of an allowlisted file must make the entry stop matching.
5. `other/ui/r38_results_UTC.png` with a runtime-generated pool token must still be reported when only `ui/r38_results_UTC.png` is allowlisted.
6. A tar, gzip, zlib, xz, bz2, zip, zstd, or 7z file in the folder is an unsuppressible archive hit even when a sha entry matches that file.
7. Unsafe names (trailing space, leading-space folder, `\`, `|`, `!`, `:1`, controls, non-ASCII, casefold collisions) are unsuppressible hits. File and directory names are also scanned for pool tokens, configured secrets, and JWTs. A JWT in a name is printed as `<redacted name hmac:xxxxxxxx>` and never as the token. Symlinks, a directory link, a dangling link, a root link, a fifo, a socket, and a device are hits. An over-budget file and an unreadable dir or file are hits.
8. Line entries are refused (exit 2). A sha entry whose file later changes no longer matches. Neither a line entry nor a sha entry may suppress a configured secret, bcrypt, or printed-once hit.
9. Duplicate or non-canonical allowlist paths refuse the whole allowlist (exit 2).
10. A runtime-built JWT whose first segment base64url-decodes to JSON with `alg` is an unsuppressible hit, including tokens around 220 and 275 characters, a payload over 200 characters, a payload near 8192, and a header whose base64url length is not a multiple of 4. `eyJ.a.b` / `eyJ+.a.b`, `eyJx.y.z`, and a header without `alg` are not hits. A failed `eyJ` immediately adjacent to a real token still hits. Detection finds base64url runs once (`re.finditer(r"[A-Za-z0-9_-]+")`) and checks each `eyJ` in constant time; header length is not capped. The JWT walk is one pass per line when percent-decoding does not change the text. 256 KiB of `eyJ` with a dot every ~8000 chars must scan within the CI budget of 15 s (measured locally at about 2.1 s for detection plus JWT redaction; the old one-char walk took 71 s on 128 KiB of the same shape). The r38 clean-lines fixture stays clean.
11. When gzip-after-junk scanning reaches the 32-candidate cap, that is an unsuppressible archive hit. A matching sha allowlist entry cannot suppress it (it is not refuse-binary).
12. Failed tar stderr that echoes a JWT redacts JWTs first, then configured secrets, then pool windows. A real PyJWT-generated token (random key, built at runtime, never printed; PyJWT is already pinned in `backend/requirements.txt`) must have the full token, `header.payload`, and the payload segment absent from stdout and stderr. Cover a `missing_<JWT>` link target, a `gone/<JWT>` member, and a bare token in tar error text. Run each leak case over many random tokens (50+) so a pool-window-inside-JWT miss cannot pass by luck.

## Sign-off

Pass / Fail — executor, date, commit.
