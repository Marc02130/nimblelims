# UAT: seed passwords and local evidence

Stem: `seed-secrets`. No migration.

UAT does not read generated passwords from stdout. `seed_dev_passwords.py --apply` for a UAT round always passes `--secrets-out`.

Backup, secrets, and local-evidence policy: [manuals/uat-artifacts.md](../manuals/uat-artifacts.md).

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

## TC-SECRETS-002 — Evidence stays on the test machine

1. Build the evidence folder on the machine that ran the cases. Leave backups in `/workspace/.uat-backups/<round>/`.
2. If a captured log still has a `printed once` header, filter the local copy:

```bash
python scripts/mask_printed_once.py < captured.log > filtered.log
```

The filter replaces the entire next line with `[redacted]`. It exits non-zero when the header is missing, when the header has no following line, or when the mask token is missing. Keep only the filtered copy locally.

3. Do not commit screenshots, captured logs, tarballs, or run outputs. Do not publish them. Do not open a pull request that adds them. There is no repository scanner, packer, or PNG chunk policy.

Record pass / fail in this script. Leave the evidence on the test machine.

## Sign-off

Pass / Fail — executor, date, commit.
