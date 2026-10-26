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
- **R-2 Instrument types.** Types come from the existing list. A type has no metadata and no type-level maintenance default. Labs can add and remove types. A LIMS run template must specify the type, and the type is locked to the template. An ad hoc run locks the type at start.
- **R-3 Maintenance.** `maintenance_tracked` is per instrument and off by default. When it is off, only use is recorded. When it is on, `next_due` is **never** auto-seeded. The item stays in status **Awaiting first due date** until a Lab Manager or Administrator sets it. Overdue items are blocked from import and use. Voiding the only passing event returns the item to **Awaiting first due date**. The configuring agent asks whether the lab tracks maintenance and sets the flag. It never sets schedules or due dates. Turning the flag off needs one confirm and is audited.
- **R-4 Roles.** Schedule create and edit, and the first due date, belong to Lab Manager and Administrator, with a backup. The backup mechanism is not in the repo (see OQ-IT-1).
- **R-5 Runs.** Once data is imported, a run cannot be canceled. It can only be failed. The instrument used at run or import must be of the template's type. The person running the experiment (tech or manager) can substitute an instrument type on a run. The substitution needs a **required** reason and writes an audit row. Legacy untyped templates are removed with no backward compatibility, because the product is not live.
- **R-6 Audit.** These are all audited: setting the first due date, schedule changes, event voids, and changes to `maintenance_tracked`.
- **R-7 Status.** #231, #232, #233, #234, and #235 are merged. E2 (migration `0115_instrument_type_slots`, typed templates and substitution) is **in progress** (Dieter). E2 is not shipped.

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
| Type on LIMS run templates and a type lock on runs (E2, in progress) | Configurable labels (later; see OQ-IT-6) |

**Instrument vs equipment.** The product label is **Instrument** everywhere, including on experiments. In this file, "equipment" means an instrument used on an experiment, such as a pipette or an incubator. It is recorded as a use. It does not feed results. Only a LIMS run ties an instrument to results, through its imports.

**Multiple instruments per run.** Data-parsers Decision #16 stands: one run may use more than one instrument over its life. After E2, each of those instruments must be of the run's type, unless the type was substituted (R-5).

---

## 2. Who

| Role | May |
|------|-----|
| Administrator | Everything below. Unsourced JSON import (logged as `admin_override`). |
| Lab Manager | Create and edit maintenance schedules. Set the first due date. Bench work. |
| Lab Technician (`experiment:manage`) | Bench work: log maintenance events, void events, record downtime, record uses, import. Substitute a run's type (E2, subject to OQ-IT-3). |
| Configuration editor (`config:edit`) | Catalog: types, instruments, vendors, CRO sources. Turn **Track maintenance** on or off. Cannot create schedules or set due dates. |
| Configuring agent (as the confirming user) | Propose instruments with an explicit yes/no on maintenance tracking. Never schedules, due dates, events, downtime, uses, status, or active. |
| Client | No instrument writes (403). Catalog reads follow the existing RLS. |

**Backup (R-4).** The ruling says Lab Manager and Administrator, "with a backup". Today the check is the role name: either role passes (`require_lab_manager`, and `is_lab_manager_or_admin()` in the database). There is no named delegate, no backup permission, and no backup role in the repo. The backup mechanism is **OQ-IT-1**. This file does not invent one.

---

## 3. Instrument types

- A type is an entry in the `instrument_types` list. It has a name, an optional description, and **Active**. It has no vendor, model, or maintenance setting. Vendor and model belong on the instrument.
- Seeded types are Plate reader, qPCR, LC-MS, Liquid handler, Balance, and Centrifuge. Labs add more types, such as Pipette or Incubator.
- **Remove means retire.** Under L-B (no delete), a type is removed by turning **Active** off. A retired type cannot be assigned to an instrument or, after E2, to a template slot or a substitution.
- **No type-level maintenance default.** A type cannot carry `maintenance_tracked`. The earlier side table `instrument_type_defaults` is kept read-only as history.
- **Template type (E2, in progress).** A LIMS run template must name the type its imports use. After a run references that template, the type is locked.
- **Ad hoc runs (no template)** lock the type at start (R-2). The E2 description leaves an ad hoc type optional instead. That gap is **OQ-IT-2**.

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
7. Voiding the only remaining passing event returns the schedule to **Awaiting first due date**. Only a Lab Manager or Administrator can set it again.
8. Overdue (next due before today on the lab clock) blocks new imports and new uses.
9. Turning **Track maintenance** off takes one confirm and is audited (§7). Turning it off is a legitimate choice for a lab with its own system, so it is not refused when the instrument is overdue.

---

## 6. Runs and instruments

- **Instrument choice is at import, not at run create.** `lims_runs` has no instrument column. The instrument is recorded on each import (`lims_run_imports`) and on `instrument_uses`. A file import writes the use row automatically.
- **Eligibility.** An import or a use is refused when the instrument is down, inactive, retired, out of service, or (when tracked) has no schedule, is awaiting its first due date, or is overdue. File import parses first. It then locks the run and checks eligibility again, so a retire or downtime that lands during the parse still refuses the import.
- **Import source.** A JSON import needs an instrument, a CRO source, or a parser. The one exception is an Administrator, whose import is recorded as `admin_override`.
- **Cancel vs fail (R-5).** A run with any imported data cannot be canceled. It can be failed, with a required reason. Every imported row stays. Nothing is deleted. Every status change takes the run's row lock, so a cancel cannot race an import.
- **Type rule (E2, in progress).** The instrument used at run or import must be of the template's type. A mismatch is refused.
- **Substitution (E2, in progress).** The person running the experiment (tech or manager) may substitute the run's instrument type. A reason is required. One audit row records who, when, the old type, the new type, and the reason. The template does not change. Earlier imports keep the type they were checked against.
- **Legacy untyped templates (E2, in progress).** These are removed with no backward compatibility. Under L-B, removal is the status flag: the E2 migration sets them inactive and keeps the rows.

---

## 7. Audit

Every audited write records who and when. Audit rows are append-only: the application role cannot update or delete them.

| Event | Required | Today |
|-------|----------|-------|
| First due date set | Who, when, old (none), new date | Shipped (#235): `instrument_schedule_audits` action `first_due` |
| Schedule change | Who, when, old, new | Shipped (#235) for the Active flip and interval change, with "was it overdue". Kind and service-vendor changes write no row (OQ-IT-4). |
| Maintenance event void | Who, when, event, next due before and after | Shipped (#235): action `event_void` |
| `maintenance_tracked` change | Who, when, old, new | Shipped (#225, #235): `instrument_maintenance_audits` on every change, and on create with the flag off |
| Run type substitution | Who, when, from, to, reason | In progress (E2): `lims_run_type_substitutions` |
| Run fail | Who, when, reason | Shipped (#229, #231): `failed_by`, `rejected_at`, `status_reason` |
| Agent-applied change | Confirming user, flagged agent-assisted, run id, provider, model | Configuring-agent lock (Marc 2026-10-07) |

---

## 8. Configuring agent

- When an input names an instrument, the agent asks whether the lab tracks maintenance for it in NimbleLIMS. It proposes the instrument with that explicit yes/no. It does not guess.
- It may set **Track maintenance** through confirm-before-apply. Turning it off is one confirm and writes the same audit row as a human change.
- It never proposes or applies schedules, the first due date, last done, next due, events, downtime, uses, instrument status, or Active. It never sets `maintenance_tracked` on a type. Such a step is a stop with a reason.
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
| E2: typed template import slot, run type snapshot, import and parser type check, type substitution with reason and audit, untyped LIMS run templates set inactive | **In progress**, not merged | [#236](https://github.com/Marc02130/nimblelims/pull/236) (open; `0115_instrument_type_slots` exists only on `cursor/instrument-e2-type-slots-bfe5`) |
| Ad hoc run type locked at start | Not built. The E2 description leaves the ad hoc type optional (OQ-IT-2). | — |
| Backup for the Lab Manager and Administrator schedule role | Not built (OQ-IT-1) | — |
| Configurable labels | Not built (later, per R-1) | — |
| Audit of schedule kind and service-vendor changes | Not built (OQ-IT-4) | — |

---

## 11. Open questions

These questions could not be answered from the repo or the 2026-10-26 rulings. They are not decided here.

| ID | Question | What the repo shows | Blocks |
|----|----------|---------------------|--------|
| **OQ-IT-1** | What is the "backup" for the schedule and first-due role? Is it a named delegate per lab, a permission that can be granted to another role, or just "either role covers the other"? | A role-name check: Administrator or Lab Manager (`require_lab_manager`, `is_lab_manager_or_admin()`). No delegate or backup concept. | A change to who may set schedules |
| **OQ-IT-2** | How does an ad hoc run (no template) "lock the type at start"? Where does the type come from, and is it required? | `lims_runs.experiment_template_id` is nullable. The E2 description says an ad hoc run "may leave that type null, or set it on start", and an import with a null type is unchecked. | E2 ad hoc behavior |
| **OQ-IT-3** | Who is "the person running the experiment" for substitution? | `lims_runs` has `created_by` and no `started_by`. The E2 description lets a Lab Technician substitute on runs they created, and a Lab Manager or Administrator on any run. | E2 substitution permission |
| **OQ-IT-4** | Do "schedule changes" (R-6) include kind and service vendor? | The #235 audit covers the Active flip and interval changes only. | Audit completeness |
| **OQ-IT-5** | In the admin UI, is the instrument dialog's **Save** the "one confirm" for turning **Track maintenance** off, or does the UI need its own prompt? | The UI is a switch followed by Save, with no separate prompt. The agent path is one apply confirm. The API PATCH is the single write. | Copy and UI for R-3 |
| **OQ-IT-6** | When do labels become configurable, and through what? | Nothing in the repo. | Later label work |
| **OQ-IT-7** | Should a Lab Technician be able to void the only passing event? Doing so returns the instrument to **Awaiting first due date**, which only a Lab Manager or Administrator can clear. | Event void is `experiment:manage`. It is audited. | Role split for voids |

---

## 12. How this differs from older docs

- **Data-parsers Decision #2** (2026-07-19) put vendor and model on the type. #223 moved them onto the instrument, and types became a plain list (R-2).
- The **AI data import idea** said "light catalog, not full equipment ops" and deferred calibration and status. This packet adds maintenance, downtime, and status. Full asset management stays out.
- **#225** seeded `next_due` as today + interval. R-3 and #235 replace that: due dates are never auto-seeded.
- The #235 HOWTO copy says "a run is not locked to one type". That describes the shipped slice. R-2 and R-5 replace it once E2 merges: the template type plus a substitution with a reason.
