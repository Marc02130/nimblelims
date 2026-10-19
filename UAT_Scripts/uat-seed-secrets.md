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

Expect exit 0 and `evidence scan clean`. A non-zero exit lists hits and the folder is not shared. Hits are a `printed once` header in any case, a 24-character mixed pool-token window, a configured compose or seed secret, a bcrypt marker, a `.dump` / `.dump.gz` / `PGDMP` dump, nested gzip/zlib/tar payloads, or a non-allowlisted binary.

## Sign-off

Pass / Fail — executor, date, commit.
