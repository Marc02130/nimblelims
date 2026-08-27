# Tech sketch: Sample vs container in the experiment queue

**Date:** 2026-08-24  
**Status:** **Draft for Design Group** — discussion; **no winner**  
**Audience:** Design Group — Heidi (Architecture), Hans (Scientific CSO), Deiter (Lab Ops); CEO Rolf  
**Stem:** `sample-container-queue`  
**This PR:** docs only. No application/product code. **Not IC50.**  
**Coding:** stays Grok Build / paused unless Marc instructs.

**Ask of this review:** discuss the problem and the **open options**. Do **not** stamp a queue model until Design Group agrees. This sketch does **not** pick A, B, or C.

---

## Related (reference; do not contradict)

| Doc | Role |
|-----|------|
| [`.docs/review/open-questions/experiments.md`](../open-questions/experiments.md) **Decision #24** | Cohort is **samples** selected at start (dual-list); gates; cohort **fixed** after start; `ExperimentSampleExecution` links sample ↔ experiment |
| [`.docs/review/open-questions/containers.md`](../open-questions/containers.md) | Nesting; Contents only on **1×1**; amount Option A; plate/rack = structure |
| [`.docs/review/tech-sketch/atomic-receive.md`](atomic-receive.md) · [`.docs/review/open-questions/sop-sample-identity-audit.md`](../open-questions/sop-sample-identity-audit.md) **Q3** | **Identity lock:** Sample ID ≠ container barcode |
| [`.docs/review/tech-sketch/mass-concentration-contents.md`](mass-concentration-contents.md) | Mass/conc on **Contents** + 1×1 Container; **Sample has no mass/conc** |
| [`.docs/review/tech-sketch/extract-hold-dest-type.md`](extract-hold-dest-type.md) | Aliquot/pool **plan lines think in source samples**; execute mints dest Sample + Contents on a dest 1×1 |
| [`.docs/review/open-questions/extract-then-qubit-testdata-gap.md`](../open-questions/extract-then-qubit-testdata-gap.md) | Same DNA identity can later enter a Qubit **LIMS Run** (path lock; Hold holes elsewhere) |
| [`.docs/review/manuals/experiments.md`](../manuals/experiments.md) · [`.docs/review/manuals/lims-runs.md`](../manuals/lims-runs.md) | Experiment cohort vs LIMS Run sample linking |

This document **does not invent** past those locks. It states **why** “what is queued” is now ambiguous, and lays **options** for when the operator must pick a **vessel**.

---

## 0. Why this sketch exists

A **Sample** is identity. A **Container** is a physical vessel (tube, well, vial) with a barcode. **Contents** is “this Sample occupies this 1×1 vessel, with this inventory.” One Sample may occupy **many** 1×1 containers (true aliquots — same Sample ID, different barcodes). The same Sample may also sit in **many experiments** over its life (different plates/tubes, different steps).

**Today the product queue thinks in Samples.** Decision #24: at experiment start, the operator selects **samples**; `ExperimentSampleExecution` is sample ↔ experiment; process membership is `eln_process_samples`. Aliquot/pool **plan lines** name source **samples**. Execute, however, pipettes from a **physical vessel**. Mass and concentration live on Contents, not on Sample.

**The open question:** What is queued for an experiment — the **Sample**, or a **Container (via Contents)** that holds the Sample? **When** does the operator pick the vessel?

Until that is agreed, start UX, scan UX, plan-line shape, concurrent experiments, and “wrong tube” risk will fight each other.

---

## 1. Locked spine (fold — do not reopen here)

| # | Lock | Source |
|---|------|--------|
| 1 | **Sample ID ≠ container barcode.** `samples.name` = system lab ID; `containers.name` = scanned barcode. | atomic-receive; sop-sample-identity-audit Q3 |
| 2 | Same Sample may occupy **many 1×1 containers** via **Contents** (true aliquots). Not a new Sample. | atomic-receive; containers.md |
| 3 | **Derivative** (Blood → DNA) = **new Sample** + `parent_sample_id`. New identity. | atomic-receive; extract-hold |
| 4 | **Experiment cohort today:** samples selected at start (Decision #24 dual-list); eligibility = Sample.status **Available for Testing** + `eln_process_samples` when under a process; **cohort fixed after start**; `ExperimentSampleExecution` = sample ↔ experiment. Scan is optional accelerator, not required. | experiments.md Decision #24 |
| 5 | Process: samples on `eln_process_samples`; gates at experiment / LIMS Run start. | Decision #24; extract-then-Qubit path lock |
| 6 | **Mass/conc** on Contents + 1×1 Container. **Sample has no mass/conc.** Volume is not stored SoT (Option A). | mass-concentration-contents; containers.md |
| 7 | Contents only on **1×1** parent Container. Plate/rack/box = structure; liquid lives in child wells/tubes. | containers.md |
| 8 | Aliquot/pool **plan lines today think in source samples**; **execute needs a physical vessel** (mutate source Contents; mint dest Sample + dest Contents). Dest FieldDefinitions must not duplicate barcode / container identity. | extract-hold; configurable-entries-framework |
| 9 | Not IC50. Coding paused / Grok Build unless Marc instructs. | This packet |

---

## 2. Problem

### 2.1 Two identities, many vessels, one queue

The lab says “queue SAMPLE-0042 for extract” and also “pull tube T-8891.” Those are not the same object.

| Layer | Answers | Does not answer |
|-------|---------|-----------------|
| **Sample** | What material is this? Type, lineage, process membership, cohort eligibility | Which tube is in the tech’s hand; which well has remaining mass |
| **1×1 Container** | Where is the liquid? Barcode, well coordinate, parent plate | Identity of the material (comes from Contents → Sample) |
| **Contents** | This Sample is in this vessel **now**, with this mass/conc | Process queue by itself; experiment cohort as shipped today |

If the queue is **only Sample**, start can succeed while two tubes of that Sample sit in the fridge — and execute (or the first pipette) still does not know which Contents row to debit. If the queue is **only Container**, Decision #24’s sample dual-list, process assignment, and sample-centric journey all have to be re-explained as “vessels that happen to carry samples.”

### 2.2 BioTech / Pharma examples (same identity, different vessels)

**Blood tube + aliquot tube, same Sample ID.** Whole blood is received into EDTA tube `T-BLOOD-01`. A true aliquot is later split into `T-ALIQUOT-01`. Both Contents rows point at **the same Sample**. Process queue shows one Sample. Extract should consume the working aliquot, not the archive blood tube. Scanning the Sample ID does not tell the tech which tube. Scanning a barcode does.

**DNA on a plate well + backup tube.** After extract, Genomic DNA (new Sample, `parent_sample_id` = blood) lives in plate well `P96-A01` (1×1 child) **and** a backup cryovial `T-DNA-BAK`. Same DNA Sample ID. Library prep or Qubit on the plate well must not debit the backup tube’s Contents. The plate barcode is the **parent** multi-element container; Contents hang on the **well**, not the plate.

**Same DNA in extract experiment, then Qubit LIMS Run.** Extract experiment cohort is the **blood Sample** (parent). Execute mints the DNA daughter. Later the Qubit LIMS Run starts on the **daughter Sample** (path lock: Tests on daughters at LIMS Run start, never on the parent). The daughter may already occupy well + backup. The LIMS Run still has the same vessel-binding question: which Contents instance is on the Qubit plate?

**Concurrent work on one identity.** PK plasma Sample has a freezer aliquot and a bench working tube. One experiment is a freeze-thaw stability study (needs the freezer vial). Another is an ELISA plate (needs the working tube). If both experiments are **in progress** on the **same Sample** with **no vessel bind**, both techs can believe they own “the sample” while only one tube is in hand.

**Wrong-tube failure mode.** Tech searches Sample ID, sees one row, grabs the nearest barcode that “is that sample.” Archive tube is opened; working stock is untouched; Contents mass on the wrong vessel goes to zero; the intended well still shows inventory. Identity was correct. **Vessel was wrong.**

### 2.3 What is already decided vs what is not

**Decided (do not use this sketch to unwind):**

- Queue **eligibility** and process membership are **Sample**-scoped today (#24).
- Cohort after start is **fixed** (no mid-flight add UI).
- True aliquot ≠ derivative.
- Inventory SoT is Contents on a 1×1, not Sample.

**Not decided (this sketch):**

- Whether the **queued unit of work** for an experiment (and LIMS Run) is Sample, Contents/container, or Sample plus a captured `source_container_id`.
- **When** the operator is forced to pick a vessel (start vs first vessel-touching entry vs execute).
- Whether two **in-progress** experiments may share one Sample, and whether **vessel exclusivity** is required if they may.
- Whether aliquot **plan lines** stay sample-shaped and bind vessel only at execute.

---

## 3. Open options (do not pick a winner)

Present tradeoffs for Design Group. **No recommendation in this PR.**

Shared assumptions for all three (already locked): 1×1 only for Contents; Sample ID ≠ barcode; auto-bind, if any, only to Contents with **Available** inventory on that Sample; refuse operating on a vessel with no Contents for that Sample.

### Option A — Queue **Samples** only; bind vessel late

**Shape:** Start dialog stays Decision #24 dual-list of **Samples**. `ExperimentSampleExecution` stays sample ↔ experiment. No container on the cohort row at start.

**Vessel pick:** At experiment start **or** at the first vessel-touching entry (pipette, aliquot execute, plate load):

| Contents for that Sample with Available inventory | Behavior |
|-----------------------------------------------------|----------|
| **Exactly one** | **Auto-bind** that 1×1 container |
| **Many** | **Forced vessel picker** (scan or choose); cannot proceed without a bind |
| **Zero** | **Refuse** (no physical inventory) |

**Lab Ops under time pressure:** Fast when every queued Sample has exactly one live tube (common at receive). Painful when true aliquots exist: start looks done, then the first entry stops the bench for a picker. Dual-list muscle memory is unchanged.

**Scan UX:** Start can stay mouse/keyboard (#24: barcode not required). Scan at start is still “resolve Sample” (or resolve barcode → Sample). The **forced** scan/pick is deferred to first touch — two different moments, two different errors (“not eligible” vs “which tube”).

**Aliquot plan line shape:** Lines can keep **source sample**. Execute (or first touch) supplies `source_container_id`. Plan can be written before anyone knows which tube will be on the bench.

**Concurrent experiments on the same Sample:** Easy to start two experiments on the same identity. Auto-bind to the **same** single tube if only one Contents exists → both experiments share one vessel unless a later exclusivity rule exists (open, §4). Many-contents: each experiment might pick a different tube, or both pick the same — A does not define exclusivity.

**Wrong-tube risk:** High if auto-bind is wrong (stale “only one Available” while a second tube was just created), or if the picker is skipped in a busy UI. Low if forced picker is unavoidable and scan-verified at first touch. Zero-contents refuse is the safe miss.

### Option B — Queue **Container-contents** (vessel instances); sample comes along

**Shape:** The queued unit is a **Contents row** (Sample in a specific 1×1). Scan-first: barcode → container → Contents → Sample. Dual-list Available/Selected is **vessels** (or Contents), not Samples. `ExperimentSampleExecution` would need a vessel (or contents) key, or a sibling bind table — **schema is not chosen here**.

**Vessel pick:** At **queue/start**. There is no “sample without a tube” in the selected set. Sample identity is a **projection** of the scanned Contents.

**Lab Ops under time pressure:** Fast when the tech already has tubes in a rack and scans down the row. Slow for early labs without barcodes (#24 rejected scan-only as the sole start path). Selecting “the sample” from a process list without knowing which aliquot exists becomes: pick a vessel or you cannot start.

**Scan UX:** Native. Paste/scan barcode is the primary add. Keyboard search by Sample ID is a **disambiguation** helper (“this Sample has three tubes — pick one”), not the cohort key. Decision #24 “barcode not required to start” is in tension with B unless a non-scan vessel picker still lists every Contents row.

**Aliquot plan line shape:** Natural key is **source container / Contents**. Plan lines that today name only `source_sample_id` would be incomplete for execute. Pool of many sources = many vessels. Sample still mints dest identity; source debit is unambiguous.

**Concurrent experiments on the same Sample:** Natural if each experiment queues a **different** vessel. Same vessel in two in-progress experiments is a first-class conflict (or a deliberate share) — visible at start, not at first pipette.

**Wrong-tube risk:** Lowest **if** the tech scans the tube in hand at queue time. Residual risk: scanning the **plate** barcode (multi-element, no Contents) and binding the wrong well; or queuing the backup cryovial because it was on top of the box. Sample-level eligibility gates still apply **through** Contents → Sample.

### Option C — Hybrid: queue stays Sample-centric; start always captures `source_container_id`

**Shape:** Process assignment, dual-list, and `ExperimentSampleExecution` stay **Sample**-centric (honors #24). At **Start**, for **each** selected Sample, the system captures **`source_container_id`** (the 1×1 whose Contents is that Sample).

| Contents with Available inventory | UX at Start |
|-----------------------------------|-------------|
| **Exactly one** | Bind **hidden** (no extra click) |
| **Many** | Forced picker **in the start dialog** (before Start succeeds) |
| **Zero** | Refuse that Sample (cannot Start with it selected) |

Cohort remains samples; vessel bind is **mandatory at start**, not deferred to first entry.

**Lab Ops under time pressure:** One dialog, one decision. Unique-tube samples feel like today’s sample list (hidden bind). Multi-aliquot samples pay the picker **before** the experiment is “in progress,” not halfway through an entry. Slightly heavier than A’s happy path; lighter than B’s full vessel queue for process-first labs.

**Scan UX:** Dual-list can stay Sample-primary. Optional scan at start can mean: scan barcode → select that Sample **and** bind that container in one gesture. Keyboard-only labs still work: unique tube auto-binds; many tubes → picker without hardware.

**Aliquot plan line shape:** Plan may still list source **samples** (cohort). Execute **must** use the captured `source_container_id` (or a later explicit override — **not specified**; would be a follow-on). Tension: plan written against Sample inventory language vs execute debiting one Contents row. If bind is at start, plan lines might **display** the bound barcode as RO projection without becoming dest FieldDefinitions (identity lock: barcode is not a dest field).

**Concurrent experiments on the same Sample:** Allowed at Sample level (two `ExperimentSampleExecution` rows). Vessel exclusivity is still open (§4): two experiments might capture the **same** `source_container_id` or different ones. C makes the collision **visible** at start (same container id on two cohorts) without deciding the policy.

**Wrong-tube risk:** Medium. Hidden auto-bind can still choose the only Available Contents while the tech intended a tube that is Quarantine/empty (not in the Available set) — refuse vs wrong bind depends on status of Contents/container (**not locked** beyond “Available inventory”). Forced picker at start + scan confirmation lowers risk vs A’s deferred pick. Not as scan-anchored as B.

---

## 4. Comparison (discussion aid — not a verdict)

| Concern | A. Samples; bind at start or first touch | B. Queue Contents / vessels | C. Sample queue + mandatory `source_container_id` at start |
|---------|------------------------------------------|-----------------------------|-------------------------------------------------------------|
| Honors #24 sample dual-list | Strongest | Weakest (redefines queued unit) | Strong (adds bind column) |
| Labs without scanners | Strong | Weak unless vessel list is fully keyboard | Strong (hidden if unique) |
| Scan-down-a-rack | Weak / late | Strongest | Mixed (scan can bind) |
| Plan lines as source samples | Fits; vessel at execute | Poor fit; lines want source container | Fits display; execute needs captured id |
| Concurrent experiments | Easy to over-share one tube | Vessel-level conflict is obvious | Collision visible; policy still open |
| Wrong tube | Highest if bind is late or auto | Lowest if scan-in-hand | Medium (hidden unique bind) |
| Zero inventory | Refuse at bind time (maybe after start) | Cannot queue | Refuse at Start |
| Schema / journey change | Smallest if bind is on first touch only | Largest | Medium (`source_container_id` on execution or sibling) |

---

## 5. Additional open questions (do not close in this PR)

### 5.1 Can the same Sample be in two **in-progress** experiments at once?

| If **no** | Sample-level exclusive lock while `ExperimentSampleExecution` is in progress. Second start refuses. Vessel pick is only about **which** tube, not **who else** is using the identity. Backup tube cannot be in a second experiment until the first completes — even if it is a different Contents row. |
| If **yes** | Identity can be in extract (or ELISA) and a parallel QC experiment. Then **vessel exclusivity** is a separate switch: (i) same Sample, different containers, both in progress — OK; (ii) same `source_container_id` in two in-progress experiments — OK, warn, or refuse. |

Design Group should not assume today’s UI prevents (i) or (ii). Decision #24 locked **cohort membership**, not cross-experiment Sample or vessel locks.

### 5.2 LIMS Run start: same vessel-binding rules?

Extract-then-Qubit: experiment start (blood Sample) and LIMS Run start (DNA daughter Sample) are **different** start surfaces. Options:

- **Same rule** as experiments (A, B, or C applied to Run sample linking).
- **Stricter** on Runs (instrument worklists are plate/well-native → closer to B).
- **Looser** on Runs (import rows already name wells; bind from file).

Do not silently apply an experiment decision to LIMS Runs. Call it out when stamping.

### 5.3 Plan lines: is `source_container_id` required at **execute** even if cohort is Samples?

Even if A or C keeps the cohort as Samples:

- Execute of aliquot/pool **must** debit a Contents row (mass-concentration lock).
- Is `source_container_id` **required** on the plan line before execute, **copied from** start bind, or **re-picked** at execute (scan the tube you actually opened)?
- If the tech opened a different true-aliquot than the start bind: refuse, warn, or overwrite bind?

This is independent of “what appears in the Available list,” but it is the same wrong-tube class of error.

### 5.4 What is “Available inventory” for auto-bind / refuse?

Not specified here. Candidates (for a later agree): Contents.amount > 0; container not disposed; Sample.status still Available for Testing; Contents/container status list. Do not invent a new status model in this discussion.

### 5.5 Multi-element scan

Scanning a **plate** barcode must not invent Contents on the plate (containers.md). Picker would be: which **child 1×1** (well) for this Sample? Open for UX when stamping B or C.

---

## 6. Bounce bars (this discussion)

| Bounce | Why |
|--------|-----|
| Picking A, B, or C in this PR | Design Group discussion; no winner |
| Equating Sample ID with container barcode | Identity lock |
| Putting mass/conc on Sample so “the queued sample” has a volume | mass-concentration-contents |
| Contents on the plate parent | containers.md; wells are 1×1 |
| Treating true aliquot as a new Sample | Identity lock; derivative is the new Sample |
| Unwinding Decision #24 (dual-list, gates, locked cohort) **in this PR** | #24 stays; options describe **tension**, not a silent override |
| Dest FieldDefinitions for barcode / container identity | extract-hold / framework |
| IC50 / application coding this packet | Docs only; Grok Build unless Marc instructs |
| Closing §5 (concurrent experiments, LIMS Run parity, execute bind) | Stay OPEN |

---

## 7. Status and coding gate

| Item | Value |
|------|--------|
| Status | **Draft for Design Group** |
| Status line | **Design Group discussion — no winner** |
| IC50 | **Not IC50** |
| Code in this PR | **None** (docs only) |
| Application coding | **Grok Build / paused** unless Marc instructs |

Implement of start/execute vessel bind stays **paused** until Design Group stamps a direction (and related §5 questions that that direction needs).

---

## 8. Reviews

Empty stamps for Design Group + CEO to fill later. Do not treat this table as Accept until stamped. **Do not infer a winner from notes.**

| Review | Reviewer | Verdict | Date | Notes |
|--------|----------|---------|------|-------|
| **CEO** | Rolf | _pending_ | | |
| **Architecture** | Heidi | _pending_ | | Queue unit vs `ExperimentSampleExecution`; LIMS Run parity |
| **Lab Ops** | Deiter | _pending_ | | Time pressure; scan; wrong tube; concurrent experiments |
| **CSO** | Hans | _pending_ | | Inventory debit vs identity; Qubit vs extract vessels |

**Implement gate for this discussion:** closed. This PR does not unpause application coding.
