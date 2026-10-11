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
