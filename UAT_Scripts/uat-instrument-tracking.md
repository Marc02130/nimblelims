# UAT: Instrument tracking

**Stem:** `instrument-tracking`
**Bars:** IT-1..IT-12
**UI:** Admin → **Instruments** (`/admin/instruments`) · LIMS run detail → **Instruments used** · Experiment template **Type → Instruments** · experiment entry instrument picker
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
| IT-4 | Next due advance and void | Schedule PM, interval 10 days, no last done. POST a passing event (performed_on T-20, performed_by = current user). POST a later passing event (T-5). PATCH the later event `{"active":false}`. | After first event: last_done = T-20, next_due = T-10. After second: last_done = T-5, next_due = T+5. After void: last_done = T-20, next_due = T-10. |
| IT-5 | Import auto-use and block | Start `RUN`. Import a file with `instrument_id=GC-UAT-1` while it is in service. GET `/v1/instrument-uses?lims_run_id=RUN`. Then retire the instrument and import again. | First import **200** and one `instrument_uses` row (note "Recorded automatically from import", used_on = lab today). Second import **422** `instrument_retired`. `lims_runs` has no instrument column. |
| IT-6 | Parser matching | Create parser A on GC-UAT-1. Create parser B on that instrument's type. Resolve import for GC-UAT-1. Resolve import for a second instrument of the same type with no exact parser. POST a parser with both `instrument_id` and `instrument_type_id`. | GC-UAT-1 matches A. The second instrument matches B. Dual source **422**. Existing per-instrument parsers still match first. |
| IT-7 | Instruments entry type | As `lab-manager` or `admin`, on Experiment templates add **Type → Instruments** (or **+ Instruments**) and select GC-UAT-1. Create an experiment. As `lab-tech`, open the Instruments entry, **Record use**. Add a second eligible instrument, then record its use. POST a use of an instrument that is not on the list. DELETE `/v1/experiments/{id}/instruments`. | Template save **200**. Experiment reloads with `allowed_instrument_ids` = [GC-UAT-1]. Record use **201**. Off-list use **422** `instrument_not_on_experiment`. DELETE **405**. |
| IT-8 | Privileges | `lab-tech` POST instrument / POST schedule / POST event / POST downtime / POST use. `config-editor` POST event / downtime / use. `client` GET instruments and POST use. | lab-tech: instrument and schedule **403**; event, downtime, use **201** when eligible. config-editor: event/downtime/use **403**. client: catalog GET returns 0 or 403; writes **403**. |
| IT-9 | Configuring agent allow list | As `config-editor`, start a configuring-agent run whose excerpts name an instrument and a PM interval. Confirm the proposal includes POST/PATCH instruments and schedules. Confirm it does **not** propose maintenance events, downtime, or uses. Confirm-before-apply. Apply as the confirming user. | Instruments and schedules may be included. Events, downtime, uses are stopped as bench work (same gap as reagent lots). Apply writes nothing until confirm. No DROP, no GRANT. |
| IT-10 | Schema catalog | Open Admin → Schema. | Lab tables include `instrument_maintenance_schedules`, `instrument_maintenance_events`, `instrument_downtime`, `instrument_uses`. `instrument_types` is not a Schema table (it is a list). `instrument_types_legacy` is not shown. |
| IT-11 | Audit | SQL: `created_by` / `modified_by` and timestamptz `created_at` / `modified_at` on the IT-4 event, the schedule, GC-UAT-1, and the IT-5 use. | All four rows have both user stamps and timestamptz clocks. |
| IT-12 | Docs | Open `manuals/HOWTO.md` (instruments section), `manuals/experiments.md` (Instruments used), and this script. | The lab path covers setup, maintenance, downtime, the run/import block, and recording use. No operator doc tells the lab to delete an instrument. |

---

## Notes

- Locations on an instrument are optional FKs to the existing `locations` table (client sites). Do not treat them as lab rooms.
- `lims_runs` must not gain an `instrument_id` column. Fail this script if a run create/edit form asks for an instrument.
- Downtime reasons **Calibration** and maintenance kind **calibration** are different list entries (global `list_entries.name` is unique).
