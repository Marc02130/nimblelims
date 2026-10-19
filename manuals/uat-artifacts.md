# UAT backups and secrets

Marc adopted this policy for User Acceptance Testing. It is documentation, not a scheduled job. Nothing in the repository deletes UAT backups on its own.

Related: [`UAT_Scripts/uat-seed-secrets.md`](../UAT_Scripts/uat-seed-secrets.md), [`.docs/review/development-process/uat/README.md`](../.docs/review/development-process/uat/README.md).

## Secrets

UAT sets seed passwords only with:

```bash
python backend/seed_dev_passwords.py --apply --secrets-out PATH
```

`PATH` must not exist yet unless you pass `--force`. The parent folder must exist. The script writes a temp file in that same directory (`O_CREAT|O_EXCL|O_NOFOLLOW`, mode `0600`) and `os.replace`s it over `PATH` only after the database commit succeeds. A failed apply removes the temp file and leaves `PATH` unchanged. Each key must match `^[A-Z_][A-Z0-9_]*$`. Each line is `KEY=<shlex.quote(value)>`. In `--secrets-out` mode, stdout is only the path line (`Generated passwords written to PATH`). Connect and status lines go to stderr. Do not use the local print-once path for UAT.

A second run at the same path without `--force` exits non-zero and leaves the file unchanged. `--force` replaces a regular file after commit and keeps mode `0600`. `--only` keeps other accounts' existing keys and replaces only the selected ones. The script refuses an existing symlink, directory, or fifo. A missing parent folder exits non-zero with one error line and no traceback.

Load the file into the shell that runs UAT:

```bash
set -a
. PATH
set +a
```

Keep the file out of evidence folders, tarballs, and `/workspace/.uat-backups/` while the round is active. Never put secrets or backups in `/tmp`. That directory is shared by every agent on the box.

If a captured log still has a `printed once` header (any case), filter it before it goes into evidence:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Do not share the unfiltered log.

Scan every evidence folder or tarball before sharing:

```bash
python scripts/scan_uat_evidence.py /path/to/evidence --secrets-file PATH
```

`--secrets-file` is the `--secrets-out` file for the round. The scan also reads `POSTGRES_PASSWORD`, `LIMS_MIGRATE_PASSWORD`, `LIMS_APP_PASSWORD`, `SECRET_KEY`, and `DEV_SEED_*` / `SLICE_*` password variables from the environment.

The default reviewed allowlist is [`scripts/uat_evidence_allowlist.json`](../scripts/uat_evidence_allowlist.json). Each entry is a concrete path plus either a line number or a file SHA-256, with `approved_by` and `date`. There is no allow-by-extension. Changed bytes no longer match. Pass `--allowlist PATH` to use another file, or `--no-allowlist` to scan with none.

The scan refuses (exit 1, list of hits) on:

- a `printed once` header in any case
- a 24-character password-pool window that contains upper, lower, digit, and a pool symbol (`_` and `-` count; mixed-case snake_case keys with three or more `_`/`-` separators and no other pool symbol are not hits)
- a configured compose or seed secret, matched literally and percent-encoded
- a bcrypt marker (`$2a$`, `$2b$`, `$2y$`)
- a `.dump` or `.dump.gz` name, or the `PGDMP` magic
- gzip or zlib payloads (decompressed, then scanned), including nested tarballs
- a binary file that is not gzip, zlib, tar, PGDMP, UTF-8 text, or an allowlisted SHA-256

Hits name the file and line. They do not repeat the secret. Hex SHAs, UUIDs, and snake_case identifiers such as `nimblelims_postgres_data` are not pool-token hits. The r38 clean-lines fixture (`backend/tests/data/r38_clean_lines.txt`) must scan clean with `--no-allowlist`.

### After each round

The `--secrets-out` file stays mode `0600` and stays outside evidence.

One retirement procedure:

1. Lock or rotate the seed accounts first, so the file is no longer the live login.
2. Then allow exactly one logged `mv` of that file into `/workspace/.uat-quarantine/<date>/`.
3. Do not `rm` the live file. Do not copy it. Do not move it into `RUN_DIR`.

`<date>` is UTC `YYYYMMDD`. That quarantine directory is mode `0700` and is gitignored.

## Backups

Backups go in `/workspace/.uat-backups/<round>/`.

- The directory is mode `0700`.
- Files in it are mode `0600`.
- The path is gitignored. Do not commit it.
- Do not put this directory, or any file from it, inside an evidence folder or an evidence tarball.
- Never write backups under `/tmp`.

`<round>` is the UAT round name, usually the script stem (for example `password-reset`).

For cleanup scripts, that directory is `RUN_DIR`:

```bash
RUN_DIR=/workspace/.uat-backups/<round>
QUARANTINE_DIR=/workspace/.uat-quarantine/<date>
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

Quarantine over delete. Use one convention everywhere: `/workspace/.uat-quarantine/<date>/` (mode `0700`). Move expired backups and the retired `--secrets-out` file there with `mv`. `rm` is allowed only after the retention window, only for paths already inside that quarantine directory, and only as a second step after the move. Never `rm` outside `QUARANTINE_DIR`.

Cleanup scripts use `set -euo pipefail`.

### Cleanup path allowlist

A cleanup script may only `mv` or `rm` paths that resolve inside one of these locations:

| Path | Use |
|------|-----|
| `$RUN_DIR` | The round backup directory, `/workspace/.uat-backups/<round>/`. `mv` out of here only. |
| `/workspace/.uat-quarantine/<date>/` | The only quarantine. Backups and the one logged secrets-file move land here. `rm` only inside this directory after retention. |

Refuse any other path, including `/workspace/.uat-backups/` itself (other rounds), `/tmp`, `$HOME`, the evidence folder, and the original `--secrets-out` path after the one logged move. The secrets file is moved once into `/workspace/.uat-quarantine/<date>/`; it is not moved into `RUN_DIR`.

## Known limitations

CI API tests connect as the testcontainer superuser, not as `lims_app`. Privilege and RLS checks still run as `lims_app` through the snapshot and role fixtures. A later change should make the request-path tests use `lims_app` as well.

## Postgres logging

Postgres statement logging is off during UAT. Do not set `log_statement`, `log_min_duration_statement`, or an equivalent that records SQL text. A statement log can capture passwords and seed-file contents.
