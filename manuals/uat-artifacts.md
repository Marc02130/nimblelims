# UAT backups and secrets

Marc adopted this policy for User Acceptance Testing. It is documentation, not a scheduled job. Nothing in the repository deletes UAT backups on its own.

Related: [`UAT_Scripts/uat-seed-secrets.md`](../UAT_Scripts/uat-seed-secrets.md), [`.docs/review/development-process/uat/README.md`](../.docs/review/development-process/uat/README.md).

## Secrets

UAT sets seed passwords only with:

```bash
python backend/seed_dev_passwords.py --apply --secrets-out PATH
```

`PATH` must not exist yet. The script creates that file exclusively (`O_CREAT|O_EXCL`) at mode `0600`. Each line is `KEY=<shlex.quote(value)>`. Stdout names the path and does not print a password. Do not use the local print-once path for UAT.

Load the file into the shell that runs UAT:

```bash
set -a
. PATH
set +a
```

Keep the file out of evidence folders, tarballs, and `/workspace/.uat-backups/` while the round is active.

If a captured log still has a `printed once` header, filter it before it goes into evidence:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Do not share the unfiltered log.

Scan every evidence folder or tarball before sharing:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence
```

The scan refuses (exit 1, list of hits) on a `printed once` header, a password-pool token of 24 or more characters, a bcrypt marker (`$2a$`, `$2b$`, `$2y$`), any `.dump` file, or a file that starts with the `PGDMP` pg_dump signature. Hits name the file and line. They do not repeat the secret.

### After each round

The `--secrets-out` file stays mode `0600` and stays outside evidence. It is not copied into `RUN_DIR` and it is not printed.

- During the round, and until the retention window ends, leave the file where the operator created it (typically under `$HOME` or `/tmp`, never under evidence).
- When the retention window ends, quarantine it: `mv` the file into `$RUN_DIR/quarantine/`. Do not `rm` it in place. The quarantined copy stays `0600`.
- After that same standing retention rule, the quarantined secrets file may be removed from inside `RUN_DIR` only. Removing it earlier, or removing it from its original path, needs Marc's approval.

## Backups

Backups go in `/workspace/.uat-backups/<round>/`.

- The directory is mode `0700`.
- Files in it are mode `0600`.
- The path is gitignored. Do not commit it.
- Do not put this directory, or any file from it, inside an evidence folder or an evidence tarball.

`<round>` is the UAT round name, usually the script stem (for example `password-reset`).

For cleanup scripts, that directory is `RUN_DIR`:

```bash
RUN_DIR=/workspace/.uat-backups/<round>
```

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

After that window, cleaning that round is allowed under this standing rule. Cleaning a backup earlier, or touching anything outside the cleanup path allowlist, needs Marc's approval. Leave cleanup manual. Do not add an automatic deleter.

## Cleanup

Quarantine over delete. Move expired files into `$RUN_DIR/quarantine/` rather than `rm`. `rm` is allowed only after the retention window, only for paths already inside `RUN_DIR`, and only as a second step after quarantine. Never `rm` outside `RUN_DIR`.

Cleanup scripts use `set -euo pipefail`.

### Cleanup path allowlist

A cleanup script may only `mv` or `rm` paths that resolve inside one of these locations:

| Path | Use |
|------|-----|
| `$RUN_DIR` | The round directory, `/workspace/.uat-backups/<round>/` |
| `$RUN_DIR/quarantine/` | Quarantine folder for that round's dumps, `MANIFEST.sha256`, and the `--secrets-out` file after retention |

Refuse any other path, including `/workspace/.uat-backups/` itself (other rounds), `/tmp`, `$HOME`, the evidence folder, and the original `--secrets-out` path. To retire the secrets file, `mv` it into `$RUN_DIR/quarantine/` first so the later `rm` stays inside `RUN_DIR`.

## Postgres logging

Postgres statement logging is off during UAT. Do not set `log_statement`, `log_min_duration_statement`, or an equivalent that records SQL text. A statement log can capture passwords and seed-file contents.
