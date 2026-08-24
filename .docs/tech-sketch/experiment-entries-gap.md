# Experiment entries gap: get an experiment running

**Date:** 2026-08-24
**Status:** **Draft Design Group**
**Audience:** Design Group; future Grok Build implementation
**Stem:** `experiment-entries-gap`
**This PR:** docs only. No application/product code. **Not IC50.**
**Coding:** remains **Grok Build / paused unless Marc instructs**.

## 1. Purpose / goal

Define the shortest coherent MVP path from the code and documentation source of truth to a laboratory operator running an experiment:

1. instantiate a template and its entries;
2. start an explicit, fixed sample cohort;
3. capture and submit process data;
4. execute an aliquot or pool when the template includes that operation; and
5. expose the minted destinations without creating a parallel inventory or lineage design.

This is a gap map and implementation order, not a new requirements catalog. The standing order is **one coherent system**, not independent checklist implementations.

## 2. Current state

### 2.1 Models and entry storage

- `backend/models/experiment.py` stores `ExperimentTemplate.template_definition`, `Experiment`, and the sample-centric `ExperimentSampleExecution` cohort.
- `backend/models/entry.py` implements typed `Entry`, `EntryFieldDefinition`, and `EntryFieldValue` storage. Runtime accepts the canonical kinds `experiment_sample_data` and `experiment_data`, plus legacy/action strings.
- The same model defines four implemented `predefined_entry_key` values: `experiment_header`, `samples`, `aliquot_pool_plan`, and `aliquots_pools`.
- `ELNProcessDefinition`, typed process steps, process instances, and `ELNProcessSample` provide the reusable process and sample-journey substrate.

### 2.2 `EntryService`

`backend/app/services/entry_service.py` already provides:

- template-entry instantiation from `template_definition.entries`;
- typed value upsert;
- dependency checks and entry submit;
- the wide entry grid and long export contracts; and
- submit-time, allowlisted Sample write-back (`due_date` and `report_date` in current code).

The grid service can project configured read-only Sample columns and can restrict `aliquots_pools` to execute-minted sample IDs. The current capture UI does not consume that grid contract, so those projections are not the operator-facing source yet.

### 2.3 `EntryCapturePanel`

`frontend/src/components/experiments/EntryCapturePanel.tsx` lists instantiated entries and supports:

- cohort-shaped `experiment_sample_data`;
- free-row `experiment_data`;
- save and submit; and
- embedded `AliquotPlanEditor` for `aliquot_pool_plan`.

It currently builds rows from `sampleExecutions` and field links rather than `GET /v1/entries/{id}/grid`. As a result, configured read-only Sample columns and the execute-only destination row policy are not rendered from the canonical grid response.

### 2.4 `AliquotPlanEditor` and execute

`frontend/src/components/experiments/AliquotPlanEditor.tsx` exposes the eight concrete IN methods and the plan/execute flow. `backend/app/schemas/aliquot_plan.py` has the corresponding `METHOD_PROFILES`; `backend/app/services/aliquot_plan_service.py` validates, resolves, and atomically executes plans.

Execute currently:

- validates sources against the experiment cohort;
- debits source `Contents.amount`;
- creates destination Sample, Container, and Contents records;
- sets single-parent lineage;
- joins minted destinations to the experiment and, when applicable, `eln_process_samples`; and
- updates the `aliquots_pools` entry with minted sample IDs.

`source_container_id` exists on a plan line, but the editor does not provide vessel binding. When it is absent, the service selects the first matching Contents row. That is unsafe for a Sample held in multiple vessels and is the open PR 65 queue/vessel problem.

### 2.5 Template entries

`frontend/src/pages/ExperimentTemplatesManagement.tsx` authors `template_definition.entries` and has four separate presets matching the model keys. New templates begin with Header and Samples.

The template editor does **not** create the aliquot plan and destination entries as an atomic pair. Method selection stores a method ID only; it does not attach the documented plan-column and destination-FieldDefinition maps.

### 2.6 What is proof versus framework

The code contains a working **mint proof**: template → cohort → entries → plan → execute → minted destinations. It does not yet implement the general wrapper framework described in the sketches:

- no runtime `METHOD_CATALOG` dual-map;
- no atomic-pair authoring;
- no non-mint wrapper catalog for Header, instrument-used, reagent-used, or review;
- no complete experiment-level “all required entries submitted” gate; and
- no agreed multi-source pool lineage or vessel-binding model.

## 3. Locked design spine

1. **Two kinds only:** `experiment_sample_data` and `experiment_data`. Legacy strings normalize to these. A wrapper is not a third kind.
2. **Predefined wrappers:** functionality is keyed by `predefined_entry_key` on one of the two kinds.
3. **Aliquot/pool is one atomic pair:** one Add action creates `aliquot_pool_plan` (`experiment_data`) and empty `aliquots_pools` (`experiment_sample_data`). Execute alone populates destinations.
4. **`METHOD_CATALOG` owns both maps:** a concrete method implies exactly one mint operation and immediately attaches plan-line columns plus destination FieldDefinitions.
5. **Process capture is not Sample:** writable entry fields capture process data. Sample identity, container identity, and inventory may appear only as read-only projections or explicit write-throughs to their owner.
6. **Four write targets, no fifth ledger:** Sample, Contents, 1×1 Container, and Entry cells. Mass/concentration never write back to Sample.
7. **Inventory ownership:** `Contents.amount` is per-sample mass/count in a vessel; 1×1 `Container.amount` is the compatible-unit sum of its Contents rows; 1×1 `Container.concentration` is vessel inventory concentration.
8. **Non-mint wrappers stay simple:** Header, instrument-used, reagent-used, and review use a kind plus FieldDefinitions. They do **not** use `METHOD_CATALOG`. Instrument primary data remains on a LIMS Run.

Canonical details:

- [configurable entry framework](configurable-entries-framework.md)
- [extract/hold destination type](extract-hold-dest-type.md)
- [mass/concentration ownership](mass-concentration-contents.md)
- [container decisions](../open-questions/containers.md)

## 4. Gap matrix

| Area | Current | Needed to run | Blocking? | Doc pointer |
|------|---------|---------------|-----------|-------------|
| Template → instance | Entries instantiate from `template_definition.entries`. | Preserve; make authored declarations follow the locked pair/wrapper rules. | No for generic capture | [experiment-template-entries.md](experiment-template-entries.md) |
| Cohort start | Explicit sample dual-list, eligibility gates, fixed cohort, process status update are implemented. | Preserve the sample-centric queue while resolving which physical vessel execute debits. | **Yes for safe multi-vessel execute** | [sample-container-queue.md](sample-container-queue.md) / merged PR 65 |
| Entry capture | Sample and experiment tables save/submit. UI bypasses the grid response. | Render the canonical grid so Sample RO columns and execute-minted destination rows are accurate. | **Yes for usable sample/destination display** | [experiment-template-entries.md](experiment-template-entries.md) §0.3 |
| Entry completion | Per-entry dependencies and submit exist. | Decide/enforce the experiment completion gate for required entries. | Later for a first run; required before governed completion | [open questions](../open-questions/experiments.md) Q20 |
| Aliquot/pool add | Plan and destination are separate presets. | One Add creates both; no plan-only or destination-only authoring. | **Yes for coherent mint templates** | [extract-hold-dest-type.md](extract-hold-dest-type.md) §2 |
| Method catalog | Backend `METHOD_PROFILES` and a duplicated frontend list provide method IDs and input shapes. | One `METHOD_CATALOG` supplies mint op, plan columns, and destination FieldDefinitions; method select attaches both maps. | **Yes for the documented mint proof** | [extract-hold-dest-type.md](extract-hold-dest-type.md) §4 |
| Destination inventory | Execute creates Sample/Container/Contents and debits source `Contents.amount`. | Project or same-transaction write through each quantitative destination field to its owner; never Sample and never a second ledger. | **Yes for quantitative correctness** | [mass-concentration-contents.md](mass-concentration-contents.md) |
| Normalization | Service searches a prior numeric concentration Result. | Use the locked Result selection, refuse unit mismatch, publish Result → 1×1 `Container.concentration`, and offer Results only for normalization. | **Yes for normalization** | [mass-concentration-contents.md](mass-concentration-contents.md) §10 |
| Vessel binding | Optional `source_container_id`; no editor control; absent ID can choose the first Contents row. | Design Group chooses the PR 65 queue/vessel option and makes source vessel selection unambiguous. | **Yes when one Sample has multiple vessels** | [sample-container-queue.md](sample-container-queue.md) |
| Pool lineage | One destination `parent_sample_id`; plan retains source lines. | Agree a multi-source lineage/composition model before claiming complete pool lineage. | No for single-parent aliquot; **yes for complete pool lineage** | [open questions](../open-questions/experiments.md) Q18 |
| Header | Implemented key, but generic rendering and no enforced top pin. | Kind + FieldDefinitions wrapper; enforce the existing pin rule when that UX slice lands. | No | [configurable framework](configurable-entries-framework.md) §4 |
| Instrument/reagent/review | No ELN wrapper keys. Instrument primary data uses LIMS Run. | Add non-mint wrappers as kind + FieldDefinitions only, without `METHOD_CATALOG`; keep files/results on LIMS Run. | Later | [experiment-template-entries.md](experiment-template-entries.md) §0.9 |
| Storage | Container management exists outside experiments. | Keep browse/move/storage workflows outside experiment entries; an entry may request one-shot put-away write-through only. | No for run | [mass-concentration-contents.md](mass-concentration-contents.md) |
| SOP → AI | Apply is held from writing live process/parser definitions. | Consume the same wrapper/catalog/execute substrate only after it runs coherently. | Later | [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md) |

## 5. Priority for “experiment running”

### Must land first

1. Make the template authoring path create the aliquot/pool pair atomically.
2. Replace the split `METHOD_PROFILES`/frontend method shape with the documented dual-map `METHOD_CATALOG`, including immediate FieldDefinition attachment.
3. Make `EntryCapturePanel` consume the grid contract for readable cohort and destination rows.
4. Apply the locked mass/concentration ownership and Result normalization rules.
5. Resolve the merged PR 65 queue/vessel decision before treating multi-vessel execute as safe.

### Can land after the first coherent run

1. Multi-source pool lineage beyond the current plan record and single `parent_sample_id`.
2. Non-mint wrappers: Header refinement, instrument-used, reagent-used, and review.
3. Experiment completion/lock UX beyond existing entry dependency and submit behavior.
4. Storage browse and move UX, which remains outside experiments.
5. SOP→AI configuration, which is a consumer after the hand-authored framework works.

## 6. Inconsistencies found across docs

1. [configurable-entries-framework.md](configurable-entries-framework.md) claimed **Design Group + CEO Agree (locked)** for the general framework, while the code and adjacent sketches show only a mint proof plus open queue, inventory, pool-lineage, and wrapper holes.
2. [mass-concentration-contents.md](mass-concentration-contents.md) called Contents the concentration SoT. This conflicts with [open-questions/containers.md](../open-questions/containers.md), where `Contents.amount` is per row and 1×1 `Container.concentration` is vessel inventory concentration.
3. The same mass/concentration sketch left Hans’s Result choice and publish behavior open, while the merged packet’s review record locks same-analysis Result selection, unit refusal, Result-publish write-through, and Result-only normalization.
4. [experiment-template-entries.md](experiment-template-entries.md) §0 uses the canonical two kinds, but later sections still use `sample_table`/`experiment_table`, show aliquot plan and results as two sample tables, and say rows can appear after mid-flight sample adds despite the fixed-cohort lock.
5. [experiment-template-entries.md](experiment-template-entries.md) opens the implement gate in its header but closes it in the stale GSTACK footer.
6. [open-questions/experiments.md](../open-questions/experiments.md) Decision #15 still describes aliquot plan/results as sample tables, superseded by the locked atomic wrapper pair.
7. [extract-hold-dest-type.md](extract-hold-dest-type.md) says destination quantitative FieldDefinitions live on the destination entry but did not state which inventory owner each field projects or writes through to.
8. [manuals/experiments.md](../manuals/experiments.md) listed `predefined_action` as a third entry kind, conflicting with the two-kind wrapper model.
9. [requirements/experiment-processes-entries.md](../requirements/experiment-processes-entries.md) still uses legacy entry kinds and gives Sample concentration/volume as write-back examples, conflicting with the inventory ownership lock.
10. [manuals/containers.md](../manuals/containers.md) described per-Contents concentration and volume units for amount in several operational examples, conflicting with per-row amount plus vessel-level inventory concentration and Option A.

## 7. Status

**Draft Design Group.** Review stamps remain pending re-stamp after this coherence fold.

This is **Not IC50**. It contains no application/product code. Application coding remains **Grok Build / paused unless Marc instructs**. Its purpose is to make the later Grok Build order explicit, not to authorize coding or create a parallel design.
