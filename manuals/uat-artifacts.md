# UAT backups and secrets

Marc adopted this policy for User Acceptance Testing. It is documentation, not a scheduled job. Nothing in the repository deletes UAT backups on its own.

Related: [`UAT_Scripts/uat-seed-secrets.md`](../UAT_Scripts/uat-seed-secrets.md), [`.docs/review/development-process/uat/README.md`](../.docs/review/development-process/uat/README.md).

## Secrets

UAT sets seed passwords only with:

```bash
python backend/seed_dev_passwords.py --apply --secrets-out PATH
```

`PATH` must not exist yet. The script creates that file exclusively (`O_CREAT|O_EXCL`) at mode `0600`. Stdout names the path and does not print a password. Do not use the local print-once path for UAT.

Export the variables from that file into the shell that runs UAT. Keep the file out of evidence folders, tarballs, and `/workspace/.uat-backups/`.

If a captured log still has a `printed once` header, filter it before it goes into evidence:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Do not share the unfiltered log.

Scan every evidence folder or tarball before sharing:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence
```

The scan refuses (exit 1, list of hits) on a `printed once` header, a 24-character password-pool token, a bcrypt marker (`$2a$`, `$2b$`, `$2y$`), or any `.dump` file. Hits name the file and line. They do not repeat the secret.

## Backups

Backups go in `/workspace/.uat-backups/<round>/`.

- The directory is mode `0700`.
- Files in it are mode `0600`.
- The path is gitignored. Do not commit it.
- Do not put this directory, or any file from it, inside an evidence folder or an evidence tarball.

`<round>` is the UAT round name, usually the script stem (for example `password-reset`).

### What is dumped

Users-table data is dumped separately from the rest of the database.

| File | Contents |
|------|----------|
| `lims_db_<round>_<sha7>_<ts>.dump` | The database without users-table data |
| `lims_db_<round>_<sha7>_<ts>_users.dump` | Users-table data only |
| `MANIFEST.sha256` | `sha256sum` of both dump files |

`<sha7>` is the first 7 characters of the commit under test. `<ts>` is UTC `YYYYMMDDTHHMMSSZ`.

Example:

```text
/workspace/.uat-backups/password-reset/lims_db_password-reset_2fd9159_20261019T180000Z.dump
/workspace/.uat-backups/password-reset/lims_db_password-reset_2fd9159_20261019T180000Z_users.dump
/workspace/.uat-backups/password-reset/MANIFEST.sha256
```

`pg_dump --exclude-table=users` writes the first file. `pg_dump --table=users` writes the second. Record both hashes in `MANIFEST.sha256`.

### Retention

Keep the round until the UAT verdict is recorded or the change merges to `main`, whichever is later, and then for 7 more days.

After that window, deleting that round is allowed under this standing rule. Deleting a backup earlier, or deleting anything outside `/workspace/.uat-backups/`, needs Marc's approval. Leave deletion manual. Do not add an automatic deleter.

## Postgres logging

Postgres statement logging is off during UAT. Do not set `log_statement`, `log_min_duration_statement`, or an equivalent that records SQL text. A statement log can capture passwords and seed-file contents.
