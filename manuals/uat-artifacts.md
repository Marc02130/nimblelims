# UAT backups and secrets

Marc adopted this policy for User Acceptance Testing. It is documentation, not a scheduled job. Nothing in the repository deletes UAT backups on its own.

Related: [`UAT_Scripts/uat-seed-secrets.md`](../UAT_Scripts/uat-seed-secrets.md), [`.docs/review/development-process/uat/README.md`](../.docs/review/development-process/uat/README.md).

## Secrets

UAT sets seed passwords only with:

```bash
python backend/seed_dev_passwords.py --apply --secrets-out PATH
```

`PATH` must not exist yet unless you pass `--force`. The parent folder must exist. The script writes a temp file in that same directory (`O_CREAT|O_EXCL|O_NOFOLLOW`, mode `0600`) and `os.replace`s it over `PATH` only after the database commit succeeds. It `lstat`s the target and never follows a symlink, so `--force` cannot overwrite a decoy through a link. A failed apply removes the temp file and leaves `PATH` unchanged. Each key must match `^DEV_SEED_[A-Z][A-Z0-9_]*$` (the project prefix used by every seed persona). That refuses shell-reserved names such as `PATH`, `HOME`, and `IFS`. Each line is `KEY=<shlex.quote(value)>`. In `--secrets-out` mode, stdout is only the path line (`Generated passwords written to PATH`). Connect and status lines go to stderr. Do not use the local print-once path for UAT.

A second run at the same path without `--force` exits non-zero and leaves the file unchanged. `--force` replaces a regular file after commit and keeps mode `0600`. `--only` keeps other accounts' existing keys and replaces only the selected ones. The script refuses an existing symlink, directory, fifo, or dangling link, even when no password is generated. A missing parent folder exits non-zero with one error line and no traceback, including when every selected account already has an env password.

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

Scan only the plain evidence folder. Archives inside it are refused by signature. Do not pass a `.tgz` to the scanner.

```bash
python scripts/scan_uat_evidence.py /path/to/evidence --secrets-file PATH
```

`--secrets-file` is the `--secrets-out` file for the round. The scan also reads `POSTGRES_PASSWORD`, `LIMS_MIGRATE_PASSWORD`, `LIMS_APP_PASSWORD`, `SECRET_KEY`, and `DEV_SEED_*` / `SLICE_*` password variables from the environment.

The default reviewed allowlist is [`scripts/uat_evidence_allowlist.json`](../scripts/uat_evidence_allowlist.json). Each entry is a canonical evidence-relative path plus the file's SHA-256, with `reviewed_by`, `approved_by`, and `date`. There are no line entries. Every new allowlist entry needs Günter's (CSO) own review and approval, recorded in `reviewed_by` and `approved_by`. A hit is suppressed only when the identity tuple matches exactly and that same object's SHA-256 equals the entry hash. A sha entry may suppress only refused-binary and password-pool hits. It never suppresses configured-secret, bcrypt, dump/PGDMP, printed-once, unsafe-name, duplicate, link, archive (including the gzip-after-junk 32-candidate cap), size-cap, encoded-run, jwt, png-trailing, or unreadable hits. Identities are exact one-element tuples (the on-disk relative path) with no normalization. Duplicate or non-canonical allowlist paths refuse the whole allowlist (exit 2). There is no allow-by-extension. Changed bytes no longer match. Pass `--allowlist PATH` to use another file, or `--no-allowlist` to scan with none.

The scan refuses (exit 1, list of hits) on:

- a `printed once` header in any case
- a 24-character password-pool window that contains upper, lower, digit, and a pool symbol (`_` and `-` count; mixed-case snake_case keys with three or more `_`/`-` separators and no other pool symbol are not hits)
- a configured compose or seed secret, matched literally and percent-encoded
- a configured secret, pool token, or JWT in a file or directory name (whole path and each segment)
- a bcrypt marker (`$2a$`, `$2b$`, `$2y$`)
- a `.dump` or `.dump.gz` name, or the `PGDMP` magic
- an archive or compressed file detected by signature (tar ustar at offset 257 or an old-style tar checksum, gzip `1f 8b` at offset 0, or gzip after junk when the bytes are `1f 8b 08`, the FLG reserved bits are zero, and a bounded inflate succeeds, or when gzip-after-junk scanning reaches the 32-candidate cap, zlib `78 01/5e/9c/da`, xz, bz2 `BZh`, zip `PK\x03\x04` plus empty `PK\x05\x06` and spanned `PK\x07\x08`, zstd, 7z, lz4, rar, cpio, lzma, compress `.Z`, lzip). Short or weak signatures in valid UTF-8 text are not hits (including `LZIP` and `Rar!` in UTF-8 text). The 32-candidate cap is an unsuppressible archive hit, not refuse-binary. A sha entry cannot hide an archive hit. PNG files may use the reviewed chunk allowlist (`IHDR`, `PLTE`, `IDAT`, `IEND`, `sRGB`, `pHYs`, `gAMA`, `cHRM`). A disallowed chunk, a truncated or length-overflowed chunk, a bad CRC, an oversized fixed-length chunk (`pHYs` 9, `gAMA` 4, `sRGB` 1, `cHRM` 32), a `PLTE` that is not 3–768 bytes or not a multiple of 3, or a complete first chunk that is not `IHDR` is an unsuppressible png-trailing hit. Trailing bytes on a walkable IHDR stream are detected by walking chunk lengths, not by searching for `IEND` (so `IEND` bytes inside `IDAT` are not a hit). A PNG that cannot be walked from IHDR to IEND but still contains an `IEND` marker plus trailing bytes is png-trailing. Reviewed magic-plus-bytes PNGs do not have a complete first chunk or an `IEND` and stay refuse-binary. A compact `YYYYMMDDThhmm[ss][Z]` token bounded by non-alphanumerics is not a password-pool hit; a digit-first pool password glued after `...T1200` still is. A missing `--secrets-file` exits 2.
- a binary file that is not PGDMP or UTF-8 text (a matching sha entry may suppress this hit)
- an unsafe name in any directory or file (`|`, `\`, `!`, controls, non-ASCII, leading/trailing whitespace, `.`/`..`/`//`, a drive letter, invalid UTF-8, or a casefold collision)
- a duplicate identity
- a symlink, fifo, socket, or device
- a folder whose scanned files exceed the 64 MiB total cap (67108864 bytes)
- a 200-character or longer hex or Base64 run
- a JWT of any realistic length (three base64url segments starting `eyJ` whose first segment base64url-decodes to JSON containing an `alg` key). Detection finds base64url runs lazily with a compiled `re.finditer(r"[A-Za-z0-9_-]+")` (a 3-run window; no materialized list) and does a constant-time check at each `eyJ` (Python 3.10; no possessive regex). At most 16 `eyJ` candidates are examined per base64url run. Reaching that bound is an unsuppressible jwt hit (same pattern as the gzip 32-candidate cap) and redaction covers the whole run through every following dot-joined run, so 16 `eyJ` decoys, a `.`, and a real token cannot leave the signature in the clear. Lines with no `eyJ` return immediately. A long header still searches its last 32 KiB for `eyJ` (same 16-candidate bound) so a real token after 32 KiB or more of base64url is found. If that window misses, a header run longer than 32 KiB (32768; chosen in the 16–64 KiB range so a long-header walk stays linear) that contains `eyJ` and forms a dotted triple takes the same bound-hit path (unsuppressible hit plus full-run redaction) so a glued token cannot leak. Tar-output newlines collapse with any adjacent dots into one `.` so `header.\\npayload` and CRLF cannot become `..` and leak. Payload stays bounded at 8192. A signature longer than 8192 is still a hit; the whole signature run is redacted. Detection percent-decodes until the text stops changing (max 3 passes), including `%u002E`, and applies NFKC. Consecutive tar octal runs decode as UTF-8 even under `LC_ALL=C`. Tar unescaping repeats to a fixed point (max 8) so a double-escaped `\\056` still hits. Tar unescaping applies to names and tar output. File content gets a JWT-only unescape pass so `\056` / newline-split tokens still hit, without running pool rules on that copy (JSON `\uXXXX` cannot become a pool false positive). Alternate unescape and percent-decode until unchanged (max 3); an extra peel that still yields a JWT-shaped run is an unsuppressible encoded-run hit. Plain backslash runs that only shrink are not. A fail-closed percent run is redacted whole. Lines with no `%`, `\`, or non-ASCII skip decode variants. Wrapped 64/76-column encodings are joined. Redaction finds spans on a prepared copy (unescape, newline join, NFKC), including configured secrets (NFKC and `quote` needles; a raw secret that contains a backslash is also matched on the original) and pool windows (a window that overlaps a compact timestamp is dropped; the rest of a pool run is redacted), maps them through escape-boundary pieces, and applies them with a single-pass join, then re-escapes controls. A token split mid-payload by a control or non-ASCII character in a filename is a known MVP limitation. A several-MiB `eyJ` blob must redact well under a few seconds. A JWT line, including a `%2E`/`%252E`-encoded token, is a jwt hit and not a pool hit. Separators must be a single `.`; `eyJheader..payload.sig` is not a JWT. `eyJ.a.b` / `eyJ+.a.b`, `eyJx.y.z`, and a header without `alg` are not hits. A failed `eyJ` immediately adjacent to a real token still hits, including a no-dot decoy `eyJx`. 256 KiB of `eyJ` with a dot every ~8000 chars must scan within the CI budget of 15 s (measured locally at about 2.1 s for detection plus JWT redaction; the old one-char walk took 71 s on 128 KiB of the same shape). One `eyJ` run plus `.a.b` at 256 KiB must stay well under 5 s
- bytes after the IEND chunk of a PNG
- an unreadable directory or file

Hits name the identity with `json.dumps`. A name segment that is a configured secret, pool token, or JWT is printed as `<redacted name hmac:xxxxxxxx>` (HMAC-SHA256 of the segment with a per-run random key, first 8 hex), including a parent segment that matches. A secret that contains `/` redacts the whole path. They do not print the secret. Hex SHAs, UUIDs, and snake_case identifiers such as `nimblelims_postgres_data` are not pool-token hits. The r38 clean-lines fixture (`backend/tests/data/r38_clean_lines.txt`) must scan clean with `--no-allowlist`.

### Packing evidence

Scan first. Pack only when the scan is clean. Use [`scripts/pack_uat_evidence.py`](../scripts/pack_uat_evidence.py):

```bash
python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz --secrets-file PATH
```

The helper requires GNU tar and GNU gzip (`tar --version`, `gzip --version`). On macOS install Homebrew `gnu-tar` and `gzip` and put `/opt/homebrew/bin` first on `PATH` (Homebrew gzip is `gzip`; gnu-tar is `gtar`, or `tar` via gnubin). It then packs into a temp name with `--format=gnu` and `gzip -n -9` (no name or mtime in the gzip header): `tar --format=gnu -C <parent> -cf <temp> --owner=0 --group=0 --numeric-owner --sort=name --mtime=@0 --mode=u=rwX,go= --use-compress-program='gzip -n -9' -- <dir>` (no `./`). `--mode=u=rwX,go=` normalizes member modes so the SHA-256 does not depend on the operator umask or the source file modes. It extracts that temp archive with `-p` (same permissions), requires exactly one top-level real directory, scans that directory as the evidence root (allowlist paths stay `ui/...png`), name-scans the directory's own name, rebuilds with the same flags, and requires a byte-identical SHA-256. Only then is the archive published and recorded in `<name>.tgz.sha256`. Pack and verify need the same GNU tar and gzip. A dirty folder or a dirty packed result produces no `.tgz` and no sidecar. The `.tgz` and sidecar are mode `0600`, created with `O_EXCL|O_NOFOLLOW`. Output inside the scanned folder, a symlinked output path, or a symlinked evidence root is refused. Failed tar stderr, name hits, and verify output are redacted JWTs first (tar-unescape and NFKC, then each `[A-Za-z0-9_.%-]+` run whose form after percent-decoding until unchanged (max 3, including `%u002E`) contains a JWT, or that still peels toward `eyJ`; the whole raw run is replaced, then raw tokens), then configured secrets and pool windows matched on that prepared copy so a backslash, tab, or quote in a configured secret cannot leave a tail. A 24-character pool window, a `%2E`/`%252E`/`%2D`/`%5F` signature hole, or a tar `\056` split cannot leave the payload in the clear. Encoded runs run before raw JWTs. Every printed path goes through `redact_name_path`. An archive or output name that matches a secret rule (JWT, pool token, or configured secret) is refused; sidecar names are redacted the same way. The JWT walk is one pass per line when percent-decoding and tar-unescape do not change the text.

Verify before sharing:

```bash
python scripts/pack_uat_evidence.py --verify evidence.tgz --secrets-file PATH
```

That requires a sidecar line `^[0-9a-f]{64}  <archive-name>$` and a matching SHA-256 (a missing, malformed, or mismatched sidecar fails). Then it extracts with `-p`, requires exactly one top-level entry that `lstat` says is a real directory, scans that directory (not the extraction root), name-scans the directory name, and requires a byte-identical rebuild with the same `--mode=u=rwX,go=` flags. Do not put an archive back into an evidence folder.

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

A JWT whose payload is split by a control or non-ASCII character in a filename is not detected. That is an accepted MVP limitation and will not be fixed in this slice.

## Postgres logging

Postgres statement logging is off during UAT. Do not set `log_statement`, `log_min_duration_statement`, or an equivalent that records SQL text. A statement log can capture passwords and seed-file contents.
