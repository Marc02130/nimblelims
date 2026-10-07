# PRD: Experiment entries and event rules

**Domain:** Sapio-style experiment entries and event rules inside a startup biotech/pharma LIMS  
**Date:** 2026-10-07  
**Status:** **Provisional** Spec fold. Spec freeze waits on Marc. **Implement CLOSED.**  
**Spec:** [../../specs/experiment-entries/SPEC.md](../../specs/experiment-entries/SPEC.md)  
**Design:** [../../design/experiment-entries.md](../../design/experiment-entries.md)  
**Separate packet:** [configuring agent](../configuring-agent/PRD.md) — not this work. This fold does not open it.  
**History (leave standing):** [experiment processes and entries requirements](../../../review/requirements/experiment-processes-entries.md) · [experiments open questions](../../../review/open-questions/experiments.md) · [experiment entries gap](../../../review/tech-sketch/experiment-entries-gap.md) · [E-10 aliquot/pool dogfood](../../../review/development-process/dogfood/e10-aliquot-atomic-pair.md)

No Accept, Confirm, or UAT Pass is recorded in this packet. Aliquot/Pool **E-10 Met** is an earlier stamp cited below. This packet does not re-ceremony it and does not invent a new Pass.

## 0. Gate

| Field | Value |
|-------|--------|
| Packet | Provisional Spec. Freeze waits on Marc. |
| Implement | **CLOSED** until Marc green-lights. |
| UAT | None. Tobias bars below are review bars for a later tip. |
| Not in this packet | IC50. Chat. Lab-analysis assistant. CRM. ERP. A second workflow engine. |

Startup biotech/pharma LIMS only (Rolf). Execute stays on Process / Experiment / LimsRun ([framework stamps](../../../decision-logs/framework-stamps-2026-08-26.md), FW-0). Event rules are a built-in action catalog on a named trigger. They are not a workflow engine beside that substrate.

---

## 1. Why this exists

Bench work inside an experiment needs a small set of entry types and a small set of event rules. The entry records the run or performs a sample or material step through APIs that already exist. The rule fires a named built-in when a named event happens, logs the attempt, and leaves no partial apply.

Marc has not frozen where those entries live, whether scripts join the catalog later, whether plates are in P1, or how this packet ranks against schema-cleanup and the configuring agent. Those questions stay open in §8.

---

## 2. Who it is for

Lab personnel who run an experiment. Clients do not edit lab entry data (experiments open question Decision #9, already Decided). Creating or editing an event rule is privileged (Tobias FB-R7). This packet does not name a new permission.

---

## 3. Rolf P1 overwrite (2026-10-07)

Authoritative product list for this provisional fold. NimbleLIMS Core.

### P1 entries in

| Entry | Rule |
|-------|------|
| Notes | Documentation around a run (Katinka). |
| Attachments | Documentation around a run. An image is an attachment. There is no separate Static Image entry. |
| Table | Documentation around a run. |
| Form | Documentation around a run. |
| Samples | Sample-touching only through existing sample APIs (FB-E6). |
| Aliquot/Pool | Already **Met**. Cite the shipped capability. Do not re-ceremony it as new work. |
| Material Tracking | In the P1 picker. Touches inventory only through existing APIs (FB-E6). |

### P1 entries out

| Entry | Rule |
|-------|------|
| Link Experiments | Out of P1. Out of the picker. **FB-E5 is dropped from P1 UAT entirely** (Tobias). |
| Receive Samples | Accession stays as built. No Receive Samples entry. Receive stays out of the entry drawer. |
| DNA / RNA / cloning | Parked (Katinka). Out of the drawer (Mathilda). |
| Gold+ instrument loaders | Parked. Instrument data stays on LimsRun. |
| OnlyOffice Document / Sheet / Slides | Not an out-of-the-box entry. |

### Rules P1

Built-in action catalog only. Code and script actions are later, and any script or code action path **in this packet** fails FB-R3 and FB-R9 (Tobias). No silent partial apply (Rolf, FB-R4).

Rolf’s lean is built-ins only for P1. Whether scripts are ever in scope remains Marc’s freeze (§8). This packet’s P1 bar is already locked: a script or code path here fails.

---

## 4. Mathilda (UI)

Provisional. Sketch waits on Spec freeze. She does not Accept this packet.

P1 picker shows only:

- Notes
- Attachments (including image)
- Table
- Form
- Samples
- Aliquot/Pool
- Material Tracking

Out of the drawer: Link Experiments, Receive-as-entry, molecular (DNA/RNA/cloning), Gold+.

Rules P1 are a built-in action gallery. No script IDE chrome.

Submit, lock, and the unlock challenge remain the lab path once Marc freezes the track. Experiments open question 20 (entry complete/submit and unlock reason) stays open in [experiments.md](../../../review/open-questions/experiments.md). This packet does not close it.

Detail: [design note](../../design/experiment-entries.md).

---

## 5. Katinka (SOP)

Provisional. Folded into the Spec bars. Not a UAT stamp.

| Bench meaning | Types |
|---------------|--------|
| Real bench steps | Aliquot/Pool (shipped) and Material Tracking (picker; existing APIs only) |
| Documentation around a run | Notes, Attachments, Table, Form |

Receive stays out of the entry drawer. Accession is built. Receive is identity plus the first vessel. Receive does not create Tests (atomic receive CORE; WO-7: Test at LimsRun start).

DNA/RNA/cloning and Gold+ stay parked.

Rules P1 built-ins may set status or set amount to 0. They refuse hard delete. They refuse any rule whose effect is on-receive → create Tests. Not IC50.

Public method names already listed on the [configuring-agent PRD](../configuring-agent/PRD.md) §8 stay there. This packet does not copy SOP bodies into git.

---

## 6. Aliquot/Pool is already Met

E-10 is Met. Cite it. Do not re-ceremony it.

Living record: [e10-aliquot-atomic-pair.md](../../../review/development-process/dogfood/e10-aliquot-atomic-pair.md). Formal §7 Result: Pass (Tobias QA, 2026-09-14, `dc7ee92`). Deiter double-Add Met. Rolf Confirm: hold merge lifted. Product on `main` (PR 129, `e56a89f`). Living uniqueness: **409** `wrapper_at_capacity`.

Shipped shape, already in code and in [sample-processing spec](../../specs/sample-processing/SPEC.md) §5:

- Wrapper `aliquot_pool` in `backend/models/wrappers.py`: keys `aliquot_pool_plan` and `aliquots_pools`, cardinality 1, atomic pair, mint.
- Save: `PUT /v1/entries/{entry_id}/aliquot-plan`.
- Execute: `POST /v1/entries/{entry_id}/execute` (debits source `Contents.amount`, mints destination Sample / Container / Contents).

This Spec does not ask for an Aliquot/Pool regression. A regression runs only if a later Spec asks for one. This packet records no new Pass.

---

## 7. What a later build still owes

When Marc freezes and Implement opens, a later build matches this draft only if:

- The picker offers the seven P1 types and keeps Link Experiments, Receive, molecular, and Gold+ out of the drawer.
- An image is stored as an attachment.
- Samples and Material Tracking call existing APIs, or they stop when no existing API can express the change.
- Aliquot/Pool remains the shipped pair. This packet does not add a second ceremony.
- A rule names a trigger, runs built-ins only, logs every attempt, refuses hard delete, refuses on-receive → create Tests, and does not leave a partial apply.
- A missing privilege is a visible refusal.
- Disable keeps rule history.

This draft does not claim that behavior ships.

---

## 8. Open — do not invent answers

### Marc (freeze still open)

| # | Question | State |
|---|----------|--------|
| 1 | Entries inside the current Experiment / ELN `entries[]` model, or a separate ELN track? | **Open.** Marc. |
| 2 | Built-ins versus scripts? | **Open** as a freeze. Rolf’s lean is built-ins only for P1. Tobias FB-R3 and FB-R9 already fail any script or code action path in this packet. Marc still freezes the longer answer. |
| 3 | Plates in P1 or out of P1? | **Open.** Marc. Experiments open question 19 is also open. This packet does not add Plates to the picker. |
| 4 | Priority against schema-cleanup and configuring-agent work? | **Open.** Marc. Configuring agent is a [separate packet](../configuring-agent/PRD.md). |

### Earlier BA notes (not answered in this repo)

| Question | State |
|----------|--------|
| Sync versus async rule execution, with a guaranteed log | **Open.** FB-R5 still requires every action attempt to be logged. How sync or async execution guarantees that log is not decided. |
| Audit actor is the user or the system | **Open.** FB-E9 still requires an actor on entry audit. Which identity is stored is not decided. |

### Explicitly not frozen here

- **OQ-1** (Schema Tables allow-list) and **OQ-5b** (on-delete) in [ui-schema-tables-cleanup](../../../review/open-questions/ui-schema-tables-cleanup.md). This packet does not restamp them. Lists stay off Schema. The packet does not choose CASCADE.
- Asked-for and routing locks. They stay as built.
- Experiments open question 20 (submit / lock / unlock reason). Mathilda keeps that as the lab path after the track freeze. The question stays open.
- JSONB-as-config. New configuration for entries or rules is not a JSONB bag. Existing `template_definition` declaration is shipped history. Whether new entry types live in that declaration is question 1, still open.
- A materials lot schema. [materials-and-lot-tracking](../../ideas/materials-and-lot-tracking.md) is a placeholder and said Material Tracking was out of an earlier v1. Rolf’s overwrite puts the type in the P1 picker. No lot API exists in the repo (`container_types.material` is vessel composition). This packet does not invent the store.

---

## 9. Configuring agent

The configuring agent is a separate packet. This fold does not extend it, does not assign ELN or event-rule authoring to it, and does not green-light implement of either body of work. Priority between them is Marc’s question 4.
