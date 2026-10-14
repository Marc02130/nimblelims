# Known backend test failures

**None.** As of the `backend-test-cleanup` branch, the full suite passes on a fresh
testcontainers PostgreSQL 15 database: 723 passed, 0 failed, 0 errors
(`python -m pytest tests -q`).

The 46 tests listed here earlier (legacy batches/results/aliquots payloads,
seed_data fixtures, eav token fixture, ELN container-required rules, WO-7
sample types, RLS 0047 seed, atomic-receive invariants, result promotion,
sig figs) were rewritten against the current API and data rules. None were deleted.

Notes for anyone adding tests:
- `db_session` joins the outer test transaction with
  `join_transaction_mode="create_savepoint"`, so `commit()` in app code or
  fixtures only releases a savepoint and everything is rolled back after the test.
- Seed through `db_session`, not a separate `sessionmaker(bind=db_engine)`
  session. A separate commit made `TestSopApplyJob` depend on pool state left
  by earlier modules: it failed only in full runs and committed other tests' rows.
- Data that only exists in the Alembic-migrated DB (0058/0059 seed, Laboratory
  QC project, list names such as `sample_status`) must use `migrated_engine`
  or be created by the test.
- The suite has only been verified against the testcontainers DB, not the
  docker-compose stack.

## Configuring agent Step 1 bars that CI can't run

`tests/test_configuring_agent_locks.py` covers the build items (no drop/delete,
amount -> 0, confirming-user scope and escalation stops, every stop kept,
include + second confirm, one-transaction rollback, audit fields, safe rerun,
RESTRICT on identity FKs) against a real database and the real list/role/
container routes. The LLM call and key lookup are monkeypatched there.

These Done-bar items need a person, a live key, or the compose stack, so no
automated test asserts them:
- **D-1 Real lab input** and **D-5 Usable on the bench**: Katinka/Marc sign-off
  with CMDL-SOP2310 then Qubit 22975, then accession and process a sample.
- **D-2 Live call**: a live provider key and the stored provider/model. CI has
  no key and must not call a vendor.
- **D-9 Survives restart**: compose down/up. The tests prove the rows are
  committed, not that the volume survives.
- **L-3 Postgres statement log**: scored from the server's statement log in UAT.

## Configuring agent UAT fixes (145f6b3) that CI can't run

`tests/test_configuring_agent_uat_fixes.py` feeds the UAT's own model bodies
(names instead of ids, `name`/`table`/`required`, roles and tables by name) in
place of the model, on the migrated database, and proves table + column +
layout + relation apply and that the rerun is a no-op. Not automated:
- **Whether a live model follows the new prompt** (catalog ids, routes, reuse of
  `sample_types`/`matrix_types`, no invented lot numbers): needs a live key
  (D-2). Re-run UAT D-4/D-7/G5 with grok-4.7.
- **L-2 two-user test** with the seed `config-editor` persona (config:edit, no
  schema:edit): run `python seed_dev_passwords.py --apply` with
  `DEV_SEED_CONFIG_EDITOR_PASSWORD` set, then log in as that user. The test only
  checks the seed role's permissions.
- **Timeout long enough for grok-4.7**: default 300 s, `CONFIGURING_AGENT_TIMEOUT_S`.
  Only the setting reaching httpx is tested.

## Configuring agent re-score (06c630b) that CI can't run

`tests/test_configuring_agent_round2.py` covers D-5 (column on experiments is a
stop naming the analyte/analysis home; analyte + analysis + link apply and rerun
as No change), D-7 (renamed equivalent template is No change), G5 (re-adding an
existing column, with a call or as a gap row, is No change), near-matches, the
background run and polling, and D-3/L-4 (start commits no catalog rows; Apply
registers exactly the Schema display set). Not automated:
- **Whether grok-4.7 now proposes analytes for Qubit and reuses
  'K2EDTA Tube (5mL)'**: needs the live key (D-2). Re-run D-5/D-7/G5 in UAT.
- **A real 96-300 s model call in the background**: the tests run the task
  inline; the 300 s ceiling and the stale-run cutoff are checked by value only.
- **D-5 on the bench** (entering a Qubit concentration on the DNA sample's
  test after Apply): Katinka/Marc sign-off, as before.
