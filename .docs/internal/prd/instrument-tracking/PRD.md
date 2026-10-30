# PRD: Instrument tracking

**Domain:** Instruments on LIMS runs, instrument maintenance, and equipment use on experiments  
**Date:** 2026-10-26  
**Status:** Working draft (requirements level). Marc's rulings relayed 2026-10-26 are folded below. This file has **no** review Accept, **no** Leadership Confirm, and **no** UAT Pass.  
**Branch:** `instrument-tracking` (feature branch; not merged to `main`). "Shipped" in this file means merged to `instrument-tracking`. It does not mean production.  
**Spec:** [../../specs/instrument-tracking/SPEC.md](../../specs/instrument-tracking/SPEC.md)  
**UAT:** [`UAT_Scripts/uat-instrument-tracking.md`](../../../../UAT_Scripts/uat-instrument-tracking.md) (IT-1 to IT-24, written against the shipped slices; not yet run)  
**How-to:** [`manuals/HOWTO.md`](../../../../manuals/HOWTO.md) → *Instruments, maintenance, and downtime*  
**History (leave standing):** [data parsers open questions](../../../review/open-questions/data-parsers-lims-runs.md) (Decisions #2, #3, #11, #16) · [AI data import idea](../../ideas/ai-data-import.md) ("Do we need instrument tracking?")

No Accept, Confirm, or UAT Pass is recorded here. Nothing in this file says a slice passed UAT.

## Rulings (Marc, relayed 2026-10-26)

- **R-1 Scope and label.** This packet is about instruments. The user-facing label is **Instrument**, not "Equipment". Labels become configurable later. Only LIMS runs are tied to instruments. Experiments use equipment (pipettes, incubators). That equipment is tracked but is not tied to results.
- **R-2 Instrument types.** Types come from the existing list. A type has no metadata and no type-level maintenance default. Labs can add and remove types. A LIMS run template must specify the type, and the type is locked to the template. Ad hoc runs are decided under OQ-IT-2 below: the instruments and the types are edited on the entry, and a LIMS run's type is required.
- **R-3 Maintenance.** `maintenance_tracked` is per instrument and off by default. When it is off, only use is recorded. When it is on, `next_due` is **never** auto-seeded. The item stays in status **Awaiting first due date** until a Lab Manager or Administrator sets the first due date. Overdue items are blocked from import and use. Voiding the only passing event returns the item to **Awaiting first due date**. Only an Administrator turns **Track maintenance** on or off (`403` `maintenance_tracked_admin_only` for every other role, including Configuration Editor). The configuring agent does not set the flag; it lacks the SOP information to decide. An Administrator can turn tracking on after the instrument is in the catalog. The agent never sets schedules or due dates. Turning the flag off needs one confirm and is audited. That confirm is the admin dialog's **Save** (OQ-IT-5).
- **R-4 Roles.** Schedule create and edit, and the first due date, belong to Lab Manager and Administrator. The backup is a second Lab Manager. There is no new role (OQ-IT-1).
- **R-5 Runs.** Once data is imported, a run cannot be canceled. It can only be failed. The instrument used at run or import must be of the template's type. The person running the experiment is whoever created it, so `created_by` is the field (OQ-IT-3). That person can substitute an instrument type on a run. The substitution needs a **required** reason (1–4000) and writes an audit row. Legacy untyped templates are removed with no backward compatibility, because the product is not live.
- **R-6 Audit.** These are all audited: setting the first due date, schedule changes (including kind and service vendor, OQ-IT-4), event voids, manager/admin event note and certificate edits, changes to `maintenance_tracked`, Administrator create with `maintenance_tracked=true` (`instrument_schedule_audits` action `maintenance_tracked`), and type deactivation. First-due, schedule changes, `maintenance_tracked` changes, type deactivation, void, and substitute-instrument-type require a reason (1–4000). All required reasons share that max (Marc 2026-10-29). A void is final (Marc 2026-10-28 via Edmund); existing `event_restore` audit rows stay.
- **R-7 Status.** #231, #232, #233, #234, and #235 are merged. E2 (migration `0115_instrument_type_slots`, typed templates and substitution) is **in progress** in [#236](https://github.com/Marc02130/nimblelims/pull/236). E2 is not shipped. OQ-IT-2 is a change to E2's scope that #236 does not implement.

## Decisions on the open questions (Marc, 2026-10-26)

- **OQ-IT-1 is Decided. Shipped.** The backup for schedules and the first due date is a second Lab Manager. No new role, no backup permission, and no named delegate. Any user with the Lab Manager role already passes `require_lab_manager` and `is_lab_manager_or_admin()`.
- **OQ-IT-2 is Decided. Not built, and it changes E2.** On an ad hoc run, the instruments used are edited on the entry itself, and instrument types can be added and removed on that entry. A LIMS run's type is required, because parsing and the rest of the run need it. [#236](https://github.com/Marc02130/nimblelims/pull/236) does not do this. On that branch an ad hoc run may leave `lims_runs.instrument_type_id` null, and a null snapshot is not type-checked (`instrument_slots.py`: "Null snapshot is unchecked (ad hoc runs only)"). This file does not claim #236 implements the ruling.
- **OQ-IT-3 is Decided. E2, in progress.** The person running the experiment is whoever created it: a lab tech, a lab manager, or another creator. `created_by` is the right field. There is no `started_by`. #236 keys substitution on `lims_runs.created_by`.
- **OQ-IT-4 is Decided. Not built.** A change to a schedule's kind and a change to its service vendor are audited, the same way an Active flip and an interval change already are. #235 writes no row for kind-only or vendor-only PATCH.
- **OQ-IT-5 is Decided. Shipped.** The admin instrument dialog's **Save** is the one confirm for turning **Track maintenance** off. `InstrumentCatalogManagement.tsx` offers Cancel and Save and no second prompt. Save sends `maintenance_tracked` on the instrument PATCH. Cancel writes nothing.
- **OQ-IT-6 is Deferred.** No decision. The open question is in §11.
- **OQ-IT-7 is Decided. Widened and shipped.** A Lab Technician may create a maintenance event and cannot edit one: not void, not any field. Edit and void are Lab Manager and Administrator only. A void is final at the API and the DB; the correction is a new event (`422` / `23514` `voided_event_stays_voided` on `PATCH` `{active: true}` or a manager `lims_app` UPDATE false→true). `update_event` uses `require_lab_manager` (**403** on every PATCH). The `refuse_void_only_passing_event` trigger raises `42501` `maintenance_event_update_forbidden` for a technician and `23514` `voided_event_stays_voided` on false→true. A downtime create or retarget to a voided event is **422** `maintenance_event_voided`; an existing link stays. INSERT stays allowed for a technician. This replaces the earlier "only the last passing event" limit.

The standing Marc locks still apply. There is no delete; removal is a status flag (L-B, 2026-10-04). Confirm-before-apply applies to the configuring agent (L-C). See the [configuring-agent PRD](../configuring-agent/PRD.md).

---

## 0. Why this exists

A result from a plate reader is only trustworthy if the lab can say which instrument produced it and that the instrument was fit to use that day. Before this work, the catalog only identified the box that produced a file, so a parser could be scoped to it (data-parsers Decision #2). It had no maintenance, no downtime, and no stop on a box that was down or overdue.

This packet adds four things. Each LIMS run import records the instrument that produced it. An instrument that is down, retired, out of service, or overdue is refused before its data is accepted. Equipment used on experiments is recorded. A lab that already uses its own metrology system is not forced to duplicate it in NimbleLIMS.

The packet stays sample-centric. A result stays on the sample's Test (WO-7: Test at LimsRun start). The instrument is lineage for how the result was produced. It is not a second key on the result.

---

## 1. Scope

| In | Out |
|----|-----|
| Instrument catalog: type, vendor, model, serial, asset tag, optional location, status | Full asset management (IQ/OQ/PQ packages, purchasing, depreciation) |
| Instrument types as a lab-editable list | Type metadata (vendor or model on the type) and type-level maintenance defaults |
| Per-instrument maintenance schedules, events, and the first due date | Auto-seeded due dates |
| Downtime records | Lab-room locations (the existing `locations` rows are client sites) |
| Instrument recorded on each LIMS run import and on each use | An `instrument_id` column on `lims_runs` |
| Equipment use on experiments (tracking only) | Tying experiment equipment to results |
| Type on LIMS run templates and a type lock on runs (E2, in progress) | Configurable labels (deferred, OQ-IT-6; no decision) |

**Instrument vs equipment.** The product label is **Instrument** everywhere, including on experiments. In this file, "equipment" means an instrument used on an experiment, such as a pipette or an incubator. It is recorded as a use. It does not feed results. Only a LIMS run ties an instrument to results, through its imports.

**Multiple instruments per run.** Data-parsers Decision #16 stands: one run may use more than one instrument over its life. After E2, each of those instruments must be of the run's type, unless the type was substituted (R-5).

---

## 2. Who

| Role | May |
|------|-----|
| Administrator | Everything below. Unsourced JSON import (logged as `admin_override`). |
| Lab Manager | Create and edit maintenance schedules. Set the first due date. Bench work. |
| Lab Technician (`experiment:manage`) | Bench work: log maintenance events, record downtime, record uses, import. Substitute a run's type when they created the run (E2, `lims_runs.created_by`). Cannot edit or void a maintenance event (OQ-IT-7, shipped). A void is final. |
| Configuration editor (`config:edit`) | Catalog: types, instruments, vendors, CRO sources. Turn **Track maintenance** on or off. Cannot create schedules or set due dates. |
| Configuring agent (as the confirming user) | Propose instruments with an explicit yes/no on maintenance tracking. Never schedules, due dates, events, downtime, uses, status, or active. |
| Client | No instrument writes (403). Catalog reads follow the existing RLS. |

**Backup (OQ-IT-1, Decided, shipped).** The backup is a second person with the Lab Manager role. There is no new role and no delegate record. Schedule create, schedule edit, and the first due date already accept every Administrator and every Lab Manager (`require_lab_manager`, and `is_lab_manager_or_admin()` in the database). A lab covers an absence by having two Lab Manager users.

---

## 3. Instrument types

- A type is an entry in the `instrument_types` list. It has a name, an optional description, and **Active**. It has no vendor, model, or maintenance setting. Vendor and model belong on the instrument.
- Seeded types are Plate reader, qPCR, LC-MS, Liquid handler, Balance, and Centrifuge. Labs add more types, such as Pipette or Incubator.
- **Remove means retire.** Under L-B (no delete), a type is removed by turning **Active** off. A retired type cannot be assigned to an instrument or, after E2, to a template slot or a substitution.
- **No type-level maintenance default.** A type cannot carry `maintenance_tracked`. The earlier side table `instrument_type_defaults` is kept read-only as history.
- **Template type (E2, in progress).** A LIMS run template must name the type its imports use. After a run references that template, the type is locked. A LIMS run's type is required (OQ-IT-2).
- **Ad hoc runs (OQ-IT-2, Decided, not built).** The instruments used are edited on the entry itself. Instrument types can be added and removed on that entry. This replaces the earlier "lock the type at start" reading of R-2. What is shipped today is adding and removing instruments on an experiment entry (`allowed_instrument_ids`), not types. [#236](https://github.com/Marc02130/nimblelims/pull/236) still lets an ad hoc run leave its type null and skips the type check. Requiring the type, and adding or removing types on the ad hoc entry, is an E2 scope change. It is not in #236.

---

## 4. Statuses

An instrument has three separate status dimensions. The UI shows each one as its own field.

| Dimension | Values | Blocks import and use? |
|-----------|--------|------------------------|
| Service status | **In service**, **Out of service**, **Retired** (retired also sets Active off) | Out of service and Retired block |
| Active | On / Off | Off blocks |
| Downtime | **Down** while an active downtime row has no end | Down blocks |
| Maintenance (only when **Track maintenance** is on) | **No schedule** · **Awaiting first due date** · **Current** · **Overdue** | No schedule, Awaiting first due date, and Overdue block |

When **Track maintenance** is off, maintenance states do not apply and do not block. Service status, Active, and Downtime still block.

**Awaiting first due date** is the label for an active schedule whose next due date has not been set. It is a stop state, not a default date.

---

## 5. Maintenance

1. **Track maintenance** is per instrument and defaults to off. An instrument created without the flag is untracked. Labs with their own metrology system leave it off. NimbleLIMS then records only use.
2. With tracking on, a Lab Manager or Administrator adds a schedule: a kind (PM, calibration, qualification, or another `maintenance_types` entry), an interval in days, and an optional service vendor.
3. A new schedule has no next due date. The system never seeds one, either from today plus the interval or from anywhere else. The instrument is **Awaiting first due date** and is blocked.
4. A Lab Manager or Administrator sets the first due date once. A second attempt is refused.
5. A passing event, logged on the bench, moves last done and next due forward. It does this only after the first due date has been set. An event logged before that does not set a date.
6. Changing the interval does not move next due and does not clear an overdue block. The new interval applies from the next passing event.
7. Voiding the only remaining passing event returns the schedule to **Awaiting first due date**. Only a Lab Manager or Administrator can set the first due date again. A void is final; the correction is a new event. A Lab Technician may create an event and cannot PATCH one — not the last passing event, not a non-last passing event, not a failed event, and not a field edit (OQ-IT-7, shipped).
8. Overdue (next due before today on the lab clock) blocks new imports and new uses.
9. Turning **Track maintenance** off takes one confirm and is audited (§7). That confirm is **Save** on the admin instrument dialog (OQ-IT-5, shipped): Cancel and Save, no second prompt, and Save sends the flag. The agent's one confirm is the apply confirm. Turning the flag off is a legitimate choice for a lab with its own system, so it is not refused when the instrument is overdue.

---

## 6. Runs and instruments

- **Instrument choice is at import, not at run create.** `lims_runs` has no instrument column. The instrument is recorded on each import (`lims_run_imports`) and on `instrument_uses`. A file import writes the use row automatically.
- **Eligibility.** An import or a use is refused when the instrument is down, inactive, retired, out of service, or (when tracked) has no schedule, is awaiting its first due date, or is overdue. File import parses first. It then locks the run and checks eligibility again, so a retire or downtime that lands during the parse still refuses the import.
- **Import source.** A JSON import needs an instrument, a CRO source, or a parser. The one exception is an Administrator, whose import is recorded as `admin_override`.
- **Cancel vs fail (R-5).** A run with any imported data cannot be canceled. It can be failed, with a required reason. Every imported row stays. Nothing is deleted. Every status change takes the run's row lock, so a cancel cannot race an import.
- **Type rule (E2, in progress).** The instrument used at run or import must be of the template's type. A mismatch is refused.
- **Ad hoc entry (OQ-IT-2, not built).** On an ad hoc run the instruments used are edited on the entry, and instrument types can be added and removed there. The type is still required on a LIMS run. #236 does not require it for an ad hoc run and does not put add-and-remove of types on that entry.
- **Substitution (E2, in progress).** Whoever created the run (`lims_runs.created_by`; there is no `started_by`) may substitute the run's instrument type (OQ-IT-3). A reason is required (1–4000). One audit row records who, when, the old type, the new type, and the reason. The template does not change. Earlier imports keep the type they were checked against. #236 also lets a Lab Manager or Administrator substitute a run they did not create.
- **Legacy untyped templates (E2, in progress).** These are removed with no backward compatibility. Under L-B, removal is the status flag: the E2 migration sets them inactive and keeps the rows.

---

## 7. Audit

Every audited write records who and when. Audit rows are append-only: the application role cannot update or delete them.

| Event | Required | Today |
|-------|----------|-------|
| First due date set | Who, when, old (none), new date | Shipped (#235): `instrument_schedule_audits` action `first_due` |
| Schedule change | Who, when, old, new, including kind and service vendor (OQ-IT-4) | Shipped (#235) for the Active flip and the interval change, with "was it overdue". Kind and service-vendor rows are **not built**. |
| Maintenance event void | Who, when, event, next due before and after | Shipped (#235): action `event_void` |
| Maintenance event note / certificate | Who, when, old, new | Shipped (#246): actions `event_note` / `event_certificate`. No extra reason. |
| `maintenance_tracked` change | Who, when, old, new, reason | Shipped: `instrument_maintenance_audits` on every change (reason required, 1–4000). Create with the flag off still writes False→False with no reason. Administrator create with the flag on writes `instrument_schedule_audits` action `maintenance_tracked` (old null, new `true`, no reason). |
| Run type substitution | Who, when, from, to, reason (1–4000) | In progress (E2): `lims_run_type_substitutions` |
| Run fail | Who, when, reason | Shipped (#229, #231): `failed_by`, `rejected_at`, `status_reason` |
| Agent-applied change | Confirming user, flagged agent-assisted, run id, provider, model | Configuring-agent lock (Marc 2026-10-07) |

---

## 8. Configuring agent

- When an input names an instrument, the agent proposes the catalog row (name, type, vendor). It does **not** ask about maintenance and does **not** set `maintenance_tracked`. A payload that includes the flag is a stop. An Administrator can turn tracking on later.
- It never proposes or applies schedules, the first due date, last done, next due, events, downtime, uses, instrument status, Active, or `maintenance_tracked`. It never sets `maintenance_tracked` on a type. Such a step is a stop with a reason.
- E2 (in progress) lets it set a template's import-slot type through confirm-before-apply. It cannot substitute a run's type.

---

## 9. What it does not do

- Delete anything (L-B). Types, instruments, schedules, events, downtime, and uses retire with Active or status.
- Seed a due date.
- Put an instrument on the run row.
- Tie experiment equipment to results.
- Default maintenance from the type.
- Let the agent touch schedules, due dates, or bench records.
- Rename the label to "Equipment".

---

## 10. Shipped vs in progress vs not built

"Shipped" means merged to `instrument-tracking`. Production is `main`, and only #229, #231, and #233 are on `main`.

| Item | State | Where |
|------|-------|-------|
| Catalog: types as a list, vendor and model on the instrument, status, no DELETE routes; schedules, events, downtime, uses; eligibility 422s; parser by instrument, CRO, or type; Instruments entry on experiments | Shipped | [#223](https://github.com/Marc02130/nimblelims/pull/223) (`0111_instrument_tracking` after rechains) |
| Optional maintenance (`maintenance_tracked`), legacy type table locked, JSON import source rule, interval does not clear overdue | Shipped | [#225](https://github.com/Marc02130/nimblelims/pull/225) (`0112`, `0113`). Its "seed next_due as today + interval" rule was superseded by #235. |
| Fail instead of cancel after import | Shipped (`main`, then `instrument-tracking`) | [#229](https://github.com/Marc02130/nimblelims/pull/229), carried in by [#230](https://github.com/Marc02130/nimblelims/pull/230) |
| Cancel and import serialize under a run row lock; `failed_by`; name-only match refused when the client ID is off-run | Shipped (`main`, then `instrument-tracking`) | [#231](https://github.com/Marc02130/nimblelims/pull/231) (`0110_lims_run_failed_by`) |
| Alembic re-chain after #231 (single head `0113_maintenance_tracked`) | Shipped | [#232](https://github.com/Marc02130/nimblelims/pull/232) |
| Every run status change locks the run; lock timeout is 409 `run_busy`; file import parses before the lock | Shipped (`main`, then `instrument-tracking`) | [#233](https://github.com/Marc02130/nimblelims/pull/233) |
| Merge of #233; eligibility re-checked after the run lock; `update_status` refuses illegal transitions; fail validates before writing | Shipped | [#234](https://github.com/Marc02130/nimblelims/pull/234) |
| E1: no auto-seeded next due; **Awaiting first due date**; first due by Lab Manager or Administrator only; schedule roles in API and database; type default retired; schedule, first-due, and void audits; Lab Manager **Instrument maintenance** page | Shipped | [#235](https://github.com/Marc02130/nimblelims/pull/235) (`0114_instrument_hardening`, current head) |
| E2: typed template import slot, run type snapshot, import and parser type check, type substitution on `created_by` with reason and audit, untyped LIMS run templates set inactive | **In progress**, not merged. Ad hoc type stays optional on this branch. | [#236](https://github.com/Marc02130/nimblelims/pull/236) (open; `0115_instrument_type_slots` exists only on `cursor/instrument-e2-type-slots-bfe5`) |
| Backup is a second Lab Manager; no new role (OQ-IT-1) | Shipped. The existing Lab Manager role is the whole mechanism. | #235 |
| Admin dialog **Save** is the one confirm for turning tracking off (OQ-IT-5) | Shipped. Cancel and Save, no second prompt. | #235 UI |
| Ad hoc entry: edit the instruments used, add and remove types on the entry, and require a type on every LIMS run including ad hoc (OQ-IT-2) | **Not built.** E2 scope change. #236 leaves the ad hoc type null and unchecked. | — |
| Audit of schedule kind and service-vendor changes (OQ-IT-4) | **Not built.** Active and interval are audited. | — |
| Edit and void of any maintenance event limited to Lab Manager and Administrator (OQ-IT-7, widened) | Shipped. Technician create stays 201. Every technician PATCH is 403. A void is final; restore is removed. | #238, this PR |
| Configurable labels (OQ-IT-6) | **Deferred.** No decision. | — |

---

## 11. Open questions

OQ-IT-1, OQ-IT-2, OQ-IT-3, OQ-IT-4, OQ-IT-5, and OQ-IT-7 are **Decided** (Marc, 2026-10-26). The decisions are at the top of this file. One question stays open, and it has no decision.

| ID | State | Question |
|----|-------|----------|
| **OQ-IT-6** | **Deferred.** No decision. | Labels are not configurable in this packet (R-1). When that work starts, the open question is whether to recommend third-party label software (for example BarTender) and only create label files, or to print directly to a printer. Nothing in the repo chooses either one. |

---

## 12. How this differs from older docs

- **Data-parsers Decision #2** (2026-07-19) put vendor and model on the type. #223 moved them onto the instrument, and types became a plain list (R-2).
- The **AI data import idea** said "light catalog, not full equipment ops" and deferred calibration and status. This packet adds maintenance, downtime, and status. Full asset management stays out.
- **#225** seeded `next_due` as today + interval. R-3 and #235 replace that: due dates are never auto-seeded.
- The #235 HOWTO copy says "a run is not locked to one type". That describes the shipped slice. Once E2 merges, a template run carries the template type and a substitution needs a reason. An ad hoc run still needs the OQ-IT-2 change on top of #236: types edited on the entry, and a type required on every LIMS run.
