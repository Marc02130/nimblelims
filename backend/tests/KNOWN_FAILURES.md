# Known backend test failures (not fixed in backend-test-cleanup)

Fresh-DB run on branch `backend-test-cleanup`: **668 passed, 28 failed, 18 errors**
(baseline on main e581266: 381 passed, 50 failed, 201 errors, 7 files failing to
collect). Every test still collects; none were deleted. Each remaining failure is
listed with the reason it was left. Fix these in a follow-up.

| Test(s) | Reason left |
|---|---|
| test_batches.py: create_batch, cross_project_* (3), *_qc_* (3) | Legacy module (was un-collectable). Payloads predate the current `BatchCreate` schema (`qc_additions` now need `container_type_id`/`matrix_id`); create returns 201 + new shape; rls_denial uses an undefined `ProjectUser` import. Needs a rewrite against the current batches API. |
| test_results.py: enter_batch_results* (5) | Legacy module. Posts the pre-US-28 payload (`analyte_id`/`raw_result`); `/results/batch` now requires `test_id` + `analyte_results`. Rewrite needed. (The 500 these tests uncovered is fixed; see PR.) |
| test_aliquots.py (5) | Legacy module. Fixtures still violate list_entries constraints (global unique `name`, NOT NULL `list_id`) and use removed fields. Rewrite needed. |
| test_eav_expansion.py (6, errors) | Fixture mints a JWT directly; the token gets 401 (no `password_epoch`/session claims the current auth requires). Should log in through `/auth/login` instead. |
| test_seed_data_usage_example.py (7, errors) | `tests/fixtures/seed_data_fixtures.py` uses string slugs (`"proj-mab-pk-001"`) as UUID ids and references fixtures (`cart_project`, `david_cro_client`) that no longer exist. |
| test_rls_experiment_isolation.py::TestElnProcess0047RlsIsolation (5, errors) | Inserts `eln_process_samples` without `container_id`, which is now NOT NULL (process_container_required rule). |
| test_eln_process_definitions.py::test_sample_journey, test_eln_processes.py::test_assign_advance_remove, test_work_order_p2.py::test_wo7_freezes_params_from_work_order_asked_for | Fixtures predate the container-required and accepted-sample-type rules for process steps; need samples in containers and step sample-type config. |
| test_lims_run_cohort.py::test_start_with_samples | No "Assigned/Pending" test status seeded; reuse the shared `cohort_sample_id` fixture in conftest. |
| test_result_promotion.py (3) | Fixture builds a `DataParser` with removed `experiment_template_id`; needs the instrument + ParserAnalysis setup (see `template_with_parser` in test_flexible_experiment.py). |
| test_atomic_receive_p0_invariants.py (3) | Expect seeded list entries ("Available for Testing", "Assigned/Pending") that only exist in a migrated DB (`NoResultFound`); the third one is a source-text assertion that trips on the word "TestClient" in a docstring. |
| test_conversions.py::test_validate_significant_figures | Significant-figures validator behavior differs from the test expectation; not yet triaged (could be a real bug). |
