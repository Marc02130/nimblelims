# UAT: Instrument E3 hardening

**Stem:** `instrument-e3-hardening`
**Bars:** IT-37..IT-39 (also listed in `uat-instrument-tracking.md`)
**API:** `/v1/instrument-maintenance-events`, `/v1/instruments`, `/v1/experiment-templates`, `/v1/lims-runs`
**Last run:** not yet run on this branch.

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| IT-37 | Void requires a reason | As `lab-manager` or `admin`, PATCH a maintenance event `{"active":false}` with no reason, then with `"   "`, then with `"wrong date"`. Use the Events **Void** dialog and type a reason. | Missing/blank **422** `void_reason_required`. With a reason **200**, `void_reason` stored, `event_void` audit has the reason. Dialog does not call the API until a reason is entered. |
| IT-38 | Track maintenance is Administrator-only | As `lab-manager` (no `config:edit`), PATCH an instrument `{"maintenance_tracked":true}` then `{"maintenance_tracked":false}`. As `admin`, both flips. | Manager both **403**. Admin **200** and `instrument_maintenance_audits` written. Behavior unchanged. |
| IT-39 | Inactive templates hidden from create-run | Deactivate a typed LIMS run template. As `lab-tech`, GET `/v1/experiment-templates` and GET with `include_inactive=true`. As `lab-manager`/`admin`, GET with `include_inactive=true`. Open the existing run. Create a new run from that template. Start the existing run. | Tech lists omit it (even with the flag). Manager/admin catalog includes it. Existing run still shows `experiment_template_id`. Create and start **422** `template_inactive`. |

## Held

- R5.11 run status audit/history table is **deferred**. Do not add it here.

## Local pytest skip

This Cloud Agent environment has previously shown **1 skipped** locally while CI shows **0 skipped**. In-repo skip candidates:

- `backend/tests/test_security_p3_s11_s12.py` — `pytest.skip` when `docker compose` is missing or `compose config` fails
- `backend/tests/test_security_s7_project_users.py` — `pytest.skip("Client role not seeded")`
- `backend/tests/test_eav_expansion.py` — skips when sample/test/project/client/batch status rows are missing

Record the exact skipped node id from `pytest -rs` on the E3 run. Do not silently skip.
