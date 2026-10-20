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

1. Build the evidence folder or tarball. Leave backups in `/workspace/.uat-backups/<round>/`.
2. If a captured log still has a `printed once` header, filter it before it goes into evidence:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Do not share `captured.log`.

3. Scan the folder or tarball:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence
```

Expect exit 0 and `evidence scan clean`. The default reviewed allowlist is `scripts/uat_evidence_allowlist.json` (canonical path plus SHA-256, no line entries, never by extension or path suffix). `reviewed_by` and `approved_by` are Günter (CSO). Identities are exact tuples (on-disk path, tar members, decode layers). Tar members need their own identity list. A sha entry may suppress only refused-binary and password-pool hits. Duplicate or non-canonical allowlist paths exit 2. A non-zero exit lists hits and the folder is not shared. Hits are a `printed once` header, a 24-character mixed pool-token window, a configured compose or seed secret, a bcrypt marker, a dump/PGDMP, nested gzip/zlib/tar payloads, a binary that is not on that allowlist, an unsafe name, a duplicate identity, a link or special file, or a nesting/decompress-cap miss.

## TC-SECRETS-003 — Reviewed allowlist and r38 clean lines

1. Scan `backend/tests/data/r38_clean_lines.txt` in a folder with `--no-allowlist`. Expect exit 0.
2. Copy that file, inject a runtime-generated pool password, and scan again with `--no-allowlist`. Expect a pool-token hit. The password must not appear in the hit text.
3. Confirm `scripts/uat_evidence_allowlist.json` lists these two SHA-256 entries, each with non-empty `reviewed_by`, `approved_by`, and `date`:
   - `ui/r38_results_America_New_York.png`
   - `ui/r38_results_UTC.png`
4. Changing one byte of an allowlisted file must make the entry stop matching.
5. `other/ui/r38_results_UTC.png` with a runtime-generated pool token must still be reported when only `ui/r38_results_UTC.png` is allowlisted.
6. A tar member named `ui/r38_results_UTC.png` with a runtime-generated pool token must still be reported when only the loose file path is allowlisted.
7. Unsafe names (trailing space, leading-space folder, `\`, `|`, `!`, `:1`, controls, non-ASCII, casefold collisions) are unsuppressible hits. Duplicate tar members, `./` / `//` / trailing-space members, `.tgz` duplicates, and tar link members are hits. Symlinks, a directory link, a dangling link, a root link, and a fifo are hits. Nesting past `MAX_NEST` is a hit.
8. Line entries are refused (exit 2). A sha entry whose file later changes no longer matches. Neither a line entry nor a sha entry may suppress a configured secret, bcrypt, or printed-once hit.
9. Duplicate or non-canonical allowlist paths refuse the whole allowlist (exit 2).

## Sign-off

Pass / Fail — executor, date, commit.
