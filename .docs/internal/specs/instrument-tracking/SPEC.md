# Spec: Instrument tracking

**PRD:** [../../prd/instrument-tracking/PRD.md](../../prd/instrument-tracking/PRD.md)  
**UAT:** [`UAT_Scripts/uat-instrument-tracking.md`](../../../../UAT_Scripts/uat-instrument-tracking.md) (IT-1 to IT-24, not yet run)  
**Date:** 2026-10-26  
**Status:** Working draft (requirements level). Marc's rulings relayed 2026-10-26 (PRD R-1 to R-7) and the same-day decisions on OQ-IT-1 through OQ-IT-7 are folded in. OQ-IT-6 stays Deferred with no decision. This spec has **no** Accept, **no** Confirm, and **no** UAT Pass. The acceptance statements in §6 are requirements for QA to test. They are not results.  
**Branch:** `instrument-tracking`, at the #235 merge `f8be768`, Alembic head `0114_instrument_hardening`. "Shipped" means merged to this branch, not to `main`.

Paths are FastAPI routes under `/v1` as mounted in `backend/app/main.py`. The UI calls them under `/api`. There is no DELETE route for any instrument table. Removal is a status flag (Marc L-B).

---

## 1. Rules

Each rule has an ID that §6 traces to a slice and an acceptance statement. The label in brackets gives the rule's state: **[Shipped]** means merged to `instrument-tracking`, **[E2]** means in progress in #236 and not merged, and **[Not built]** means neither.

### Scope and label

- **IT-REQ-1 [Shipped]** User-facing copy says **Instrument**. No screen, toast, or API message says "Equipment". Configurable labels are later. **[Not built]**
- **IT-REQ-2 [Shipped]** Only a LIMS run ties an instrument to results. The instrument is recorded on `lims_run_imports.instrument_id` and on `instrument_uses.lims_run_id`. Publish promotes only from LIMS run imports.
- **IT-REQ-3 [Shipped]** Experiment equipment is recorded as `instrument_uses` with `experiment_id`, through the Instruments entry. It writes no Result and does not feed publish.

### Types

- **IT-REQ-4 [Shipped]** Types are entries in the `instrument_types` list: name, description, and Active only. There is no vendor, model, or other type metadata.
- **IT-REQ-5 [Shipped]** A type has no maintenance default. `maintenance_tracked` on a type create or PATCH is **422**. `instrument_type_defaults` is read-only history.
- **IT-REQ-6 [Shipped]** With `config:edit`, a lab adds a type and removes one by setting Active to false **with a required reason** (1–4000; **422** `instrument_type_deactivate_reason_required`). The reason is stored on `instrument_type_deactivations`. List PATCH/DELETE cannot deactivate a type. DELETE on `/v1/instrument-types` is **405**. Assigning an inactive type to an instrument is **422** `instrument_type_inactive`.
- **IT-REQ-7 [E2]** A LIMS run template names its import type, in exactly one `run_import` slot with an active type. After any run references the template, changing that type is refused.
- **IT-REQ-8 [Not built; E2 scope change, OQ-IT-2 Decided]** On an ad hoc run, the instruments used are edited on the entry itself, and instrument types can be added and removed on that entry. A LIMS run's type is required, including when the run has no template, because parsing and the rest of the run need it. [#236](https://github.com/Marc02130/nimblelims/pull/236) does not do this: an ad hoc run may leave `lims_runs.instrument_type_id` null, and a null snapshot is not type-checked. Shipped today is add and remove of instruments on an experiment entry (`allowed_instrument_ids`), not of types, and a LIMS run has no type at all.

### Maintenance

- **IT-REQ-9 [Shipped]** `instruments.maintenance_tracked` defaults to false. An instrument created without the flag is false.
- **IT-REQ-10 [Shipped]** With tracking off, maintenance never blocks. Only use is recorded. Downtime, inactive, retired, and out of service still block.
- **IT-REQ-11 [Shipped]** A new schedule's `next_due` and `last_done` are null. No path seeds them: create, interval PATCH, an event before the first due date, the agent, or a client body. The schedule is **Awaiting first due date**.
- **IT-REQ-12 [Shipped]** Only Administrator or Lab Manager sets the first due date, once (`POST /v1/instrument-maintenance-schedules/{id}/first-due`), with a required reason (1–4000; **422** `schedule_change_reason_required`). A second call is **422** `first_due_already_set`. The schedule row is locked for the check. The backup is a second Lab Manager user (OQ-IT-1). No new role.
- **IT-REQ-13 [Shipped]** With tracking on, an import or use is **422** in three cases: `instrument_no_schedule` (no active schedule), `instrument_awaiting_first_due` (an active schedule with null `next_due`), and `instrument_overdue` (`next_due` before the lab day).
- **IT-REQ-14 [Shipped]** A passing event recomputes `last_done` and `next_due` (performed on + interval) only after the first due date is set.
- **IT-REQ-15 [Shipped]** An interval change does not recompute `next_due` and does not clear an overdue block.
- **IT-REQ-16 [Shipped]** Voiding the only remaining passing event sets `last_done` and `next_due` to null. The instrument is **Awaiting first due date**.
- **IT-REQ-17 [Shipped]** Turning `maintenance_tracked` off is one confirm (OQ-IT-5) and is **Administrator only**. For the API, that is the PATCH itself (`403` `maintenance_tracked_admin_only` for Configuration Editor, Lab Manager, Lab Technician, and clients). A value change **requires** `reason` (1–4000; **422** `maintenance_tracked_reason_required`). The configuring agent cannot send the flag. For the admin UI, **Save** on the instrument dialog is that confirm: Cancel and Save, no second prompt, and Save sends `maintenance_tracked` plus the reason only when the user is an Administrator.

### Roles

- **IT-REQ-18 [Shipped]** Schedule create, schedule PATCH, and first due need Administrator or Lab Manager. The API checks with `require_lab_manager`. The database backs it up with `is_lab_manager_or_admin()` on schedule INSERT and with the update guard trigger on schedule UPDATE. Other roles get **403**. The backup (OQ-IT-1) is a second user with the Lab Manager role. There is no new role.
- **IT-REQ-19 [Shipped]** Maintenance events, event voids, downtime, and uses need `experiment:manage`. The catalog (types, instruments, CRO sources) needs `config:edit`. Turning **Track maintenance** on or off needs the Administrator role in addition to `config:edit`.

### Runs

- **IT-REQ-20 [Shipped]** A run with any stored import cannot be canceled: **422** `run_has_imported_data`. Fail needs a non-empty reason. It sets `failed_by`, `rejected_at`, and `status_reason`, and keeps every import row. Cancel, fail, import, and every other status change take the run row lock (`FOR NO KEY UPDATE`). Lock timeout is **409** `run_busy`.
- **IT-REQ-21 [Shipped]** File import parses, locks the run, and then checks eligibility again for both the instrument sent and the instrument resolved from the parser. JSON import without an instrument, CRO source, or parser is **422** `import_source_required`, except for an Administrator (`admin_override`).
- **IT-REQ-22 [E2]** The instrument at import must be of the run's type, which is the template type snapshotted at start or the substituted type. A mismatch is **422** `instrument_type_mismatch`. This applies equally to a type-scoped parser of another type and to an instrument-scoped parser whose instrument is of another type.
- **IT-REQ-23 [E2; OQ-IT-3 Decided]** The person running the experiment is whoever created it. #236 uses `lims_runs.created_by` (there is no `started_by`): a Lab Technician substitutes a run they created, and a Lab Manager or Administrator substitutes any non-terminal run. The reason is required. One append-only audit row records who, when, from, to, and reason. The template is unchanged. Earlier imports keep the type they were checked against. Terminal runs are refused.
- **IT-REQ-24 [E2]** Untyped LIMS run templates are removed with no backward compatibility. Under L-B they are set inactive and the rows stay. Creating a run on a template with no typed `run_import` slot is **422** `run_template_type_required`.

### Audit

- **IT-REQ-25 [Shipped]** Setting the first due date writes one `instrument_schedule_audits` row: action `first_due`, who, when, old null, the new date, and the required reason.
- **IT-REQ-26 [Shipped]** A schedule Active flip, interval change, kind change, or service-vendor change writes one row (`schedule_active`, `schedule_interval`, `schedule_kind`, or `schedule_vendor`) with old, new, overdue-at-the-time, and the required reason (1–4000; **422** `schedule_change_reason_required`).
- **IT-REQ-27 [Shipped]** An event void writes one row (`event_void`) with the event id and `next_due` before and after.
- **IT-REQ-27b [Shipped; OQ-IT-7 Decided, widened]** A Lab Technician may create a maintenance event and cannot update one. `update_event` requires Administrator or Lab Manager. A technician PATCH (void last, void non-last, void failed, restore attempt, or field edit) is 403. The same UPDATE as `lims_app` with a technician `current_user_id` raises `42501` `maintenance_event_update_forbidden`. INSERT stays allowed. The return to **Awaiting first due date** (IT-REQ-16) is shipped.
- **IT-REQ-27c [Shipped; Marc 2026-10-28]** A voided maintenance event stays voided. `PATCH` `{active: true}` is **422** `voided_event_stays_voided`. There is no restore route. The correction is a new event. Existing `event_restore` audit rows stay valid. The DB trigger still allows a Lab Manager / Admin `lims_app` UPDATE `active` false→true until Edmund decides on a migration.
- **IT-REQ-28 [Shipped]** Every change to `maintenance_tracked` writes one `instrument_maintenance_audits` row with who, when, old, new, and the required reason (1–4000; **422** `maintenance_tracked_reason_required`). A create with it false still writes False→False with no reason. An Administrator create with it true writes one `instrument_schedule_audits` row (`action=maintenance_tracked`, old null, new `true`, no reason). The configuring agent does not write either row because it cannot set the flag.
- **IT-REQ-29 [Shipped]** Both audit tables are append-only for `lims_app`: SELECT and INSERT only, with UPDATE and DELETE revoked and FORCE RLS on. E2 adds the rule `created_by = current_user_id()` on INSERT. **[E2]**

### Configuring agent

- **IT-REQ-30 [Shipped]** An instrument POST or PATCH from the agent that includes `maintenance_tracked` is a stop. The agent does not ask whether the lab tracks maintenance and does not set the flag. An Administrator can turn it on. The agent's proposal never includes schedule routes, `next_due`, `last_done`, `status`, `active`, events, downtime, or uses. A type body carrying `maintenance_tracked` is stopped.

---

## 2. Statuses (contract)

| Field | Values | Source |
|-------|--------|--------|
| `instruments.status` | `in_service`, `out_of_service`, `retired` (retired also sets `active` false) | #223 |
| `instruments.active` | true / false | #223 |
| Downtime | Down while an active `instrument_downtime` row has `ended_at` null | #223 |
| Maintenance (tracked only) | No schedule · **Awaiting first due date** (`next_due` null) · Current · Overdue (`next_due` < lab day) | #225, #235 |
| `lims_runs.status` | `draft`, `ordered`, `running`, `results_received`, `complete`, `published`, `failed`, `canceled` | existing |

Eligibility checks run in this order, and the first match wins: retired, out of service, inactive, down, then (tracked only) no schedule, awaiting first due, overdue. `GET /v1/instruments/{id}/eligibility` returns the same code and `maintenance_tracked` without writing.

---

## 3. Data (shipped through `0114`)

| Table | Purpose | Delete |
|-------|---------|--------|
| `list_entries` in list `instrument_types` | Types | Revoked; retire with `active` |
| `instruments` | Instrument: type, vendor, model, serial, asset tag, location, status, active, `maintenance_tracked` | Revoked |
| `instrument_maintenance_schedules` | Kind, interval, `last_done`, `next_due`, service vendor, active | Revoked |
| `instrument_maintenance_events` | Performed on, by (user or vendor), pass/fail, certificate URL, note, active | Revoked |
| `instrument_downtime` | Started, ended, reason, optional event, note, active | Revoked |
| `instrument_uses` | Instrument on a run and/or an experiment, used on, active | Revoked |
| `instrument_maintenance_audits` | `maintenance_tracked` old/new, who, when | Append-only |
| `instrument_schedule_audits` | `first_due`, `schedule_active`, `schedule_interval`, `event_void` | Append-only |
| `instrument_type_defaults` | Retired type default, kept as history | SELECT only |

E2 (`0115_instrument_type_slots`, **not merged**) adds: `instrument_uses.entry_id` and `slot_key`, `lims_runs.instrument_type_id`, `lims_run_imports.note`, `instrument_schedule_audits.reason`, and the append-only `lims_run_type_substitutions`. It drops nothing.

---

## 4. Routes (shipped)

`/v1/instrument-types`, `/v1/instruments`, `/v1/instruments/{id}/eligibility`, `/v1/cro-sources`, `/v1/instrument-maintenance-schedules`, `/v1/instrument-maintenance-schedules/{id}/first-due`, `/v1/instrument-maintenance-events`, `/v1/instrument-downtime`, `/v1/instrument-uses`, `/v1/experiments/{id}/instruments`, `PATCH /v1/lims-runs/{id}/cancel`, `POST /v1/lims-runs/{id}/fail` (alias `/reject`), `POST /v1/lims-runs/{id}/import`, `POST /v1/lims-runs/{id}/import-file`. Detail: [`manuals/api-endpoints.md`](../../../../manuals/api-endpoints.md).

UI: Admin → **Instruments** (`/admin/instruments`, `config:edit`). **Instrument maintenance** (`/instrument-maintenance`, Administrator or Lab Manager). LIMS run detail → instruments used. Experiment template **Type → Instruments**.

E2 route (not merged): `POST /v1/lims-runs/{id}/substitute-instrument-type` with body `{instrument_type_id, reason}`.

---

## 5. Out of this spec

Delete paths. Auto-seeded due dates. An instrument column on `lims_runs`. Type metadata. Type-level maintenance defaults. Lab-room locations. IQ/OQ/PQ packages. Agent writes to schedules, due dates, or bench records. Configurable labels (later).

---

## 6. Requirements-to-slice traceability (for QA)

Each acceptance statement below is a requirement that QA must verify. None of them is a recorded result. The UAT column names the existing bar in `uat-instrument-tracking.md` that exercises the rule, where one exists. A dash means no bar covers it yet. That bar has not been run.

| Rule | Slice | State | Acceptance statement | UAT bar |
|------|-------|-------|----------------------|---------|
| IT-REQ-1 | #223, #235 | Shipped | No user-facing string on the instrument screens, the run page, or the experiment Instruments entry contains "Equipment". | — |
| IT-REQ-2 | #223 | Shipped | A file import with an instrument stores that `instrument_id` on the import and writes one `instrument_uses` row with the run id. `lims_runs` has no instrument column. | IT-5 |
| IT-REQ-3 | #223 | Shipped | Recording an instrument use on an experiment writes an `instrument_uses` row with `experiment_id` and creates no Test or Result. | IT-7 |
| IT-REQ-4 | #223 | Shipped | The type form and API accept name, description, and Active only. Vendor and model appear only on the instrument. | IT-1 |
| IT-REQ-5 | #235 | Shipped | POST or PATCH of a type with `maintenance_tracked` is 422. `lims_app` cannot INSERT or UPDATE `instrument_type_defaults`. | IT-21 |
| IT-REQ-6 | #223, #225 | Shipped | A `config:edit` user creates a type (201) and retires it with Active off. DELETE is 405. Creating an instrument on the retired type is 422 `instrument_type_inactive`. | IT-24, IT-16 |
| IT-REQ-7 | E2 #236 | In progress | Saving a LIMS run template whose `run_import` slot has no active type is 422. Changing that type after a run references the template is 422 `run_import_type_locked`. | — (E2 adds IT-25 to IT-31 on its branch) |
| IT-REQ-8 | E2 scope change beyond #236 | Not built | On an ad hoc run, adding and removing an instrument on the entry changes the instruments used, and adding and removing an instrument type on the entry changes the types. A LIMS run with no type, including an ad hoc run, is refused. A null `lims_runs.instrument_type_id` on an ad hoc run, which is what #236 allows, fails this bar. | — |
| IT-REQ-9 | #225, #235 | Shipped | An instrument created without `maintenance_tracked` reads back false. | IT-21 |
| IT-REQ-10 | #225 | Shipped | On an untracked instrument with an overdue schedule or none, a use is 201. An open downtime row is 422 `instrument_down`. | IT-19 |
| IT-REQ-11 | #235 | Shipped | A schedule created by any route, including one with dates in the body, has null `next_due` and `last_done`. A passing event before the first due date leaves both null. | IT-4, IT-18 |
| IT-REQ-12 | #235 | Shipped | Lab Manager first due → 200. Repeat → 422 `first_due_already_set`. Lab Technician → 403. A second user with the Lab Manager role can set first due. No other role exists for this. While one caller holds the schedule lock, a second call waits. | IT-22 |
| IT-REQ-13 | #223, #225, #235 | Shipped | A tracked instrument is refused with exactly these codes: `instrument_no_schedule` when it has no schedule, `instrument_awaiting_first_due` when a schedule has no next due, and `instrument_overdue` when next due is before the lab day. The refusals apply to both import and use. | IT-3, IT-20 |
| IT-REQ-14 | #235 | Shipped | After the first due date is set, a passing event on day D sets `last_done` = D and `next_due` = D + interval. | IT-4 |
| IT-REQ-15 | #225 | Shipped | PATCHing the interval on an overdue schedule leaves `next_due` unchanged, and eligibility stays `instrument_overdue`. | IT-13 |
| IT-REQ-16 | #235 | Shipped | Voiding the only passing event sets both dates to null, and eligibility returns `instrument_awaiting_first_due`. | IT-23 |
| IT-REQ-17 | #235 | Shipped | A single API PATCH turns tracking off. A single agent apply confirm applies the off, with no second confirm. In Admin → Instruments, turning the switch off and pressing Save is the only confirm: there is no second dialog, and Cancel writes nothing. | IT-21 |
| IT-REQ-18 | #235 | Shipped | Lab Technician and configuration editor get 403 on schedule POST, schedule PATCH, and first due. A second Lab Manager gets 201. Inserting a schedule as a non-manager `lims_app` session is refused by RLS. | IT-8 |
| IT-REQ-19 | #223 | Shipped | Lab Technician gets 201 on event, downtime, and use when the instrument is eligible. A configuration editor gets 403 on those. | IT-8 |
| IT-REQ-20 | #229, #231, #233, #234 | Shipped | Cancel after a stored import is 422 `run_has_imported_data`. Fail with an empty reason is 422. Fail keeps every import row and sets `failed_by`. A concurrent cancel and import never both succeed. | — (covered in `uat-elisa-run-gaps.md` EG-3, EG-5, EG-8, EG-9) |
| IT-REQ-21 | #225, #234 | Shipped | Retiring the instrument while a file is parsing makes that import 422 `instrument_retired`. A Lab Technician's unsourced JSON import is 422 `import_source_required`. The same import by an Administrator is 200 and is recorded as `admin_override`. | IT-15 |
| IT-REQ-22 | E2 #236 | In progress | Importing with an instrument of another type than the run's type is 422 `instrument_type_mismatch`, and no import row is written. | — |
| IT-REQ-23 | E2 #236 | In progress | The creator (`lims_runs.created_by`) substitutes with a reason and the call writes one `lims_run_type_substitutions` row (who, when, from, to, reason). The template's type is unchanged. A Lab Technician who did not create the run is refused. There is no `started_by` column. | — |
| IT-REQ-24 | E2 #236 | In progress | After `0115`, every LIMS run template without a typed `run_import` slot is inactive and still present. Creating a run on such a template is 422 `run_template_type_required`. | — |
| IT-REQ-25 | #235 | Shipped | One first-due call writes exactly one audit row with action `first_due`, `created_by`, `created_at`, a null previous value, and the date. | IT-22 |
| IT-REQ-26 | #235 for Active and interval; kind and vendor not built | Shipped in part | Flipping Active or changing the interval writes one row each, with the overdue-at-time flag. After the not-built part lands, a kind-only PATCH and a service-vendor-only PATCH each write one row with old and new. Until then, those PATCH calls write none, and that is a gap against this rule. | — |
| IT-REQ-27 | #235 | Shipped | Voiding an event writes one `event_void` row with the event id and `next_due` before and after. | IT-23 |
| IT-REQ-27b | #238 | Shipped | A Lab Technician create is 201. Every technician update (void last, void non-last, void failed, restore attempt, field edit) is 403. A Lab Manager or Administrator update is 200. Void of the only passing event still returns the schedule to awaiting first due. | IT-23 |
| IT-REQ-27c | #245 | Shipped | Manager/admin `PATCH` `{active: true}` on a voided event is 422 `voided_event_stays_voided`. `POST`/`PATCH` `.../restore` is 404/405. No new `event_restore` row is written. | IT-35 |
| IT-REQ-28 | #225, #235 | Shipped | Each on/off change writes one `instrument_maintenance_audits` row with previous and new values. Creating with false writes one row. Creating with true writes none. | IT-21 |
| IT-REQ-29 | #235 (+E2) | Shipped (E2 part in progress) | `has_table_privilege('lims_app', t, 'UPDATE')` and `'DELETE'` are false for both audit tables. | — |
| IT-REQ-30 | #225, #235, D2 | Shipped | An agent instrument POST or PATCH that includes `maintenance_tracked` is a stop. The agent does not ask the yes/no question. Any proposed schedule, first-due, event, downtime, use, status, or active step stops. | IT-9, IT-14 |

OQ-IT-1 through OQ-IT-5 and OQ-IT-7 are Decided in the [PRD](../../prd/instrument-tracking/PRD.md). The only open question is OQ-IT-6 (Deferred, no decision) in [PRD §11](../../prd/instrument-tracking/PRD.md#11-open-questions).
