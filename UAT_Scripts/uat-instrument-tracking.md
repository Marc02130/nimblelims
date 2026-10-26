# UAT: Instrument tracking

**Stem:** `instrument-tracking`
**Bars:** IT-1..IT-32
**UI:** Admin → **Instruments** (`/admin/instruments`) · **Instrument maintenance** (`/instrument-maintenance`, Administrator or Lab Manager) · LIMS run detail → **Instruments used** · Experiment template **Type → Instruments** · experiment entry instrument picker
**API:** `/v1/instrument-types`, `/v1/instruments`, `/v1/cro-sources`, `/v1/instrument-maintenance-schedules`, `/v1/instrument-maintenance-events`, `/v1/instrument-downtime`, `/v1/instrument-uses`, `/v1/experiments/{id}/instruments` (see `manuals/api-endpoints.md`)
**Actors:** `config-editor` (config:edit; does not author templates), `lab-manager` and `admin` (experiment:manage; author templates), `lab-tech` (experiment:manage), `client` (client user)
**Env:** local docker compose (`lims-*`), http://localhost:3000 + :8000
**Last run:** not yet run on this branch.

Record per row: Pass / Fail / Incomplete, commit SHA, evidence path.

---

## Setup

Lab timezone must already be set (`lab_settings.timezone`). Run as `config-editor` unless noted.

Seeded lists (do not recreate; add only if a name is missing):

| List | Seeded entries |
|------|----------------|
| `instrument_types` | Plate reader, qPCR, LC-MS, Liquid handler, Balance, Centrifuge |
| `maintenance_types` | PM, calibration, qualification |
| `downtime_reasons` | Breakdown, Preventive maintenance, Calibration, Qualification, Facility, Other |

Create vendor **Agilent** if it is not already in `/v1/vendors`. Create instrument **GC-UAT-1** (type LC-MS or a newly added Custom GC, vendor Agilent, model 8890, serial UAT-SN-1, status in_service). Create one LIMS run (`RUN`) on an analysis that has an active parser for that instrument (or create the parser in IT-9).

---

## Bars

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| IT-1 | Catalog create, no delete | As `config-editor`, open Admin → Instruments. Types tab lists the six seeded names and has no vendor/model fields. Instruments tab: **Add Instrument** uses a **Vendor** picker (not free text) and a **Status** control. Create GC-UAT-1. DELETE `/v1/instrument-types/{id}`, `/v1/instruments/{id}`, `/v1/cro-sources/{id}`. There is no Delete button on Types, Instruments, CRO sources, Maintenance, or Downtime. | 201 for the instrument. DELETE → **405**. Rows remain. UI has no Delete. |
| IT-2 | Retire flags | PATCH GC-UAT-1 `{"status":"retired"}`. GET it. PATCH `{"status":"in_service","active":true}`. PATCH a type and a CRO source `{"active":false}`, then `{"active":true}`. | Retired instrument is `status=retired` and `active=false`. Reactivate works. Types and CRO sources retire with `active` only. |
| IT-3 | Eligibility 422s | For each: inactive; retired; out of service; open downtime (reason Breakdown, no `ended_at`); overdue schedule (`next_due` yesterday, kind calibration). GET `/v1/instruments/{id}/eligibility`. POST `/v1/instrument-uses` on `RUN`. End the downtime. Clear or deactivate the overdue schedule. Restore in_service. | Each GET `allowed=false` with codes `instrument_inactive`, `instrument_retired`, `instrument_out_of_service`, `instrument_down`, `instrument_overdue`. Each use is **422** with the same code. After restore, eligibility `allowed=true`. |
| IT-4 | Next due advance and void | As `admin` or `lab-manager`, schedule PM, interval 10 days. Next due is empty (**Awaiting first due date**). POST `/first-due` with today. POST a passing event (performed_on T-20, performed_by = current user). POST a later passing event (T-5). PATCH the later event `{"active":false}`. | After create: `next_due` null. After first-due + first event: last_done = T-20, next_due = T-10. After second: last_done = T-5, next_due = T+5. After void: last_done = T-20, next_due = T-10. |
| IT-5 | Import auto-use and block | Start `RUN` from a typed LIMS run template. Import a file with `instrument_id=GC-UAT-1` while it is in service and of the run's type. GET `/v1/instrument-uses?lims_run_id=RUN`. Then retire the instrument and import again. | First import **200** and one `instrument_uses` row (note "Recorded automatically from import", used_on = lab today). Second import **422** `instrument_retired`. `lims_runs` has `instrument_type_id` (snapshot) and no `instrument_id`. |
| IT-6 | Parser matching | Create parser A on GC-UAT-1. Create parser B on that instrument's type. Resolve import for GC-UAT-1. Resolve import for a second instrument of the same type with no exact parser. POST a parser with both `instrument_id` and `instrument_type_id`. | GC-UAT-1 matches A. The second instrument matches B. Dual source **422**. Existing per-instrument parsers still match first. |
| IT-7 | Instruments entry slots | As `lab-manager` or `admin`, on Experiment templates add **Type → Instruments** (or **+ Instruments**). Add a `run_import` slot, pick type **LC-MS** (or the type of GC-UAT-1) from the active types list. Create the template. Create an experiment. As `lab-tech`, open the Instruments entry, pick that slot, **Record use**. POST a use with a missing `slot_key` or a different type. DELETE `/v1/experiments/{id}/instruments`. | Template save **200/201**. `run_import` without a type is **422** `instrument_entry_invalid`. Record use **201**. Missing slot **422** `instrument_slot_not_found`. Type mismatch **422** `instrument_type_mismatch`. DELETE **405**. |
| IT-8 | Privileges | `lab-tech` POST instrument / POST schedule / POST first-due / POST event / POST downtime / POST use. `config-editor` POST schedule / first-due / event / downtime / use. `lab-manager` POST schedule and first-due. `client` GET instruments and POST use. | lab-tech: instrument, schedule, first-due **403**; event, downtime, use **201** when eligible. config-editor: schedule, first-due, event, downtime, use **403**. lab-manager: schedule and first-due **201**. client: catalog GET returns 0 or 403; writes **403**. |
| IT-9 | Configuring agent allow list | As `config-editor`, start a configuring-agent run whose excerpts name an instrument and a PM interval. Confirm the proposal asks whether the lab tracks maintenance and includes POST/PATCH instruments with an explicit `maintenance_tracked`. Confirm it does **not** propose schedules, first-due, events, downtime, or uses. Confirm-before-apply. Apply as the confirming user. | Instruments may be included when the yes/no is answered. Schedules, first-due, events, downtime, uses are stopped. Apply writes nothing until confirm. No DROP, no GRANT. |
| IT-10 | Schema catalog | Open Admin → Schema. | Lab tables include `instrument_maintenance_schedules`, `instrument_maintenance_events`, `instrument_downtime`, `instrument_uses`. `instrument_types` is not a Schema table (it is a list). `instrument_types_legacy` is not shown. |
| IT-11 | Audit | SQL: `created_by` / `modified_by` and timestamptz `created_at` / `modified_at` on the IT-4 event, the schedule, GC-UAT-1, and the IT-5 use. | All four rows have both user stamps and timestamptz clocks. |
| IT-12 | Docs | Open `manuals/HOWTO.md` (instruments section), `manuals/experiments.md` (Instruments used), and this script. | The lab path covers setup, optional maintenance tracking, downtime, the run/import block, and recording use. No operator doc tells the lab to delete an instrument. |
| IT-13 | Interval does not clear overdue | Track maintenance on GC-UAT-1. Add a calibration schedule (interval 1). Log a passing event dated two days ago so it is overdue. PATCH the schedule `{"interval_days": 365}`. GET eligibility. As configuring-agent, propose PATCH interval_days. | Human PATCH **200**, `next_due` unchanged, eligibility still `instrument_overdue`. Agent row is stopped: interval does not clear overdue. |
| IT-14 | Agent cannot set status/active | Confirm-before-apply a PATCH of GC-UAT-1 `{"status":"retired"}` or `{"active":false}`. | Stopped. Status and active are not set by the configuration run. |
| IT-15 | JSON import source | As `lab-tech`, POST `/v1/lims-runs/{RUN}/import` with rows and no instrument/CRO/parser. As `admin`, the same body. | lab-tech **422** `import_source_required`. admin **200** and the server log has `json_import_without_instrument`. |
| IT-16 | Dates, certificate, used_on, inactive type | Event with `performed_on` tomorrow. Downtime with `ended_at` tomorrow. Event certificate `ftp://x`. Use with a client `used_on` of yesterday. Create an instrument on an inactive type. | Event **422** `performed_on_in_future`. Downtime **422** `ended_at_in_future`. Certificate **422** `certificate_url_invalid`. Use `used_on` is lab today. Type **422** `instrument_type_inactive`. |
| IT-17 | Un-void re-checks eligibility | Record a use. Void it. Retire the instrument. PATCH the use `{"active":true}`. Restore in_service and PATCH again. | Retired un-void **422** `instrument_retired`. After restore, un-void **200**. |
| IT-18 | Admin form has no last_done/next_due inputs | Open Admin → Instruments → Maintenance → Add / Edit, or Instrument maintenance. | Interval and kind only. Last done and next due show on the grid. Next due empty shows **Awaiting first due date**. First due is a separate action. |
| IT-19 | Track maintenance off | Leave GC-UAT-1 untracked. Add an overdue schedule (or none). POST a use. Open downtime. Retire. | Untracked overdue/no-schedule still allows use. Open downtime **422** `instrument_down`. Retired **422** `instrument_retired`. |
| IT-20 | Track maintenance on | Turn tracking on with no schedule. POST a use. Add a schedule (no first due). Set the first due date in the past. Log a passing event today. Open downtime. | No schedule **422** `instrument_no_schedule`. Schedule without first due **422** `instrument_awaiting_first_due`. After first-due + event, allowed. Open downtime **422** `instrument_down`. |
| IT-21 | Type default refused and agent OFF | POST a type with `maintenance_tracked`. Create an instrument without sending the flag. Confirm-before-apply PATCH `maintenance_tracked` false on a tracked instrument. | Type **422**. New instrument is untracked. Apply writes the OFF. `instrument_maintenance_audits.previous_value` is true. |
| IT-22 | First due date | As `lab-manager`, open Instrument maintenance. Set first due on GC-UAT-1's schedule. Repeat the same POST. As `lab-tech`, the same POST. | First call **200**. Second **422** `first_due_already_set`. lab-tech **403**. |
| IT-23 | Voided-only event | After IT-4, as `lab-tech` void the remaining passing event. As `lab-manager`, void it. GET eligibility. As admin, set first due again. | Tech **403** `only_passing_event_void_forbidden`. Manager **200**. Eligibility `instrument_awaiting_first_due`. First-due **200** and the item is eligible again. |
| IT-24 | Add and retire a type | As `config-editor`, add type **Pipette**. Create an instrument of that type. PATCH the type `{"active":false}`. There is no Delete. | Type create **201**. Retire is Active off. DELETE **405**. A run template still requires a typed `run_import` slot; labs retire types with Active off, they do not delete them. |
| IT-25 | Typed run_import slot | Create a LIMS run template with a `run_import` slot and no type. Create one with two `run_import` slots. Create one with a typed `run_import` slot and an untyped extra slot. | No type **422** `instrument_entry_invalid`. Two run_import **422**. Typed + optional extra **201**. |
| IT-26 | create_run requires typed slot | `POST /v1/lims-runs` with a template that has no `run_import` slot. Then with a typed template. | Untyped **422** `run_template_type_required`. Typed **201**. |
| IT-27 | Start snapshots type | Start the typed-template run. GET the run. | `instrument_type_id` equals the template `run_import` type. Overview shows **Instrument type**. |
| IT-28 | Type mismatch on import | Start `RUN`. Import with an instrument whose type is not the snapshot. Then import with a matching type. | First **422** `instrument_type_mismatch` and no `lims_run_imports` row. Second **200**. |
| IT-29 | Creator substitutes own run | As `lab-tech` who created `RUN` (`lims_runs.created_by`), **Substitute instrument type** with a reason. As the same tech on a run created by someone else. As `lab-manager` on that other run. | Own run **200** and an audit row (who, when, from, to, reason). Other run **403**. Manager **200**. Template unchanged. |
| IT-30 | Import after substitution | After IT-29, import with an instrument of the old type, then the new type. | Old type **422** `instrument_type_mismatch`. New type **200**. |
| IT-31 | Ad hoc type required | Create a run with no template. Start it without `instrument_type_id`. Start again with an active type. | First start **422** `run_type_required`. Second **200** and `instrument_type_id` is set. |
| IT-32 | Entry slot type change | On an experiment Instruments entry, change a slot type. | Old `instrument_uses` row is voided (`active` false). Template slots are unchanged. |

---

## Notes

- Locations on an instrument are optional FKs to the existing `locations` table (client sites). Do not treat them as lab rooms.
- `lims_runs` must not gain an `instrument_id` column. Fail this script if a run create/edit form asks for an instrument.
- Downtime reasons **Calibration** and maintenance kind **calibration** are different list entries (global `list_entries.name` is unique).
