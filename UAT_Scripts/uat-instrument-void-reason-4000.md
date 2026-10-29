# UAT: Void reason max 4000

**Stem:** `instrument-void-reason-4000`
**Bars:** IT-37 length bound (also listed in `uat-instrument-tracking.md`)
**API:** `PATCH /v1/instrument-maintenance-events/{id}`
**Last run:** not yet run on this branch.

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| IT-37-len | Void reason max 4000 | As `lab-manager` or `admin`, PATCH a live maintenance event `{"active":false,"reason":"<4000 x>"}`. Repeat with 4001 `x`. Repeat as `lims_app` UPDATE of `void_reason`. In the Events **Void** dialog, confirm `maxLength` 4000, counter `n/4000`, 4000 submits, 4001 shows the max error and does not call the API. | 4000 **200**, stored `void_reason` is 4000 characters. 4001 **422** at the API and **23514** at the DB CHECK. Dialog helper `1–4000`. Whitespace/NBSP/U+2007/ZWSP/BOM bars in IT-37 are unchanged. |

## Notes

- Migration `0120_void_reason_4000` raises `ck_instrument_events_void_reason` from 1000 to 4000. Downgrade refuses if a trimmed `void_reason` is longer than 1000; it does not truncate or delete.
- Schedule / `maintenance_tracked` / type-deactivation reasons stay 4000. Substitute-instrument-type reason stays 1–1000 (out of scope).

## Local pytest skip

Exact local skip from `pytest -rs` on this branch:

- `tests/test_security_p3_s11_s12.py:110` — `compose config failed: unknown shorthand flag: 'f' in -f`. This Cloud Agent image's `docker` CLI does not accept `docker compose -f`. CI runs a real Compose file and shows **0 skipped**.
