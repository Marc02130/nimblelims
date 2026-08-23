# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **In review. Implement gate CLOSED until Leadership Accept.**  
**Stem:** `extract-hold-dest-type`  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 aliquot/pool  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest sample that inherits parent identity fields and **does not** join `eln_process_samples`. Extract-then-Qubit (blood → DNA → Qubit on DNA) cannot run: the daughter looks like blood and is not on the process instance.

## 2. Goals and non-goals

**Goals (locked)**

- Optional dest `sample_type` on **aliquot and pool** plan lines, same control cluster as **method**.
- Blank / omitted → dest `sample_type` = parent `sample_type`.
- Execute (one transaction with existing aliquot/pool execute):
  1. Create dest sample with `parent_sample_id` = source.
  2. Set `samples.sample_type` from the plan line (or parent if blank).
  3. If the experiment is under an ELN process step, insert dest into `eln_process_samples` for **that process instance** (status `queued` / waiting for next step — match existing assign semantics).
- Use existing `samples.sample_type` (list FK). **No new Sample column.**

**Non-goals**

- Dropping or rewriting `samples.matrix`.
- TruSeq / library dest-type (same rule later).
- SOP+AI Apply → process / parser.
- New tables. New Sample columns. IC50.
- Product UI code in this PR (docs only). Entry-setup UX called out for Mathilda review.

## 3. Data model (existing only)

```
samples.sample_type       ← existing list FK; dest write target
samples.parent_sample_id  ← existing; set on dest
samples.matrix            ← unchanged this packet (still copies parent / current execute)
eln_process_samples       ← existing; insert dest for current process instance
entries / entry config    ← aliquot|pool plan line gains optional dest_sample_type
```

Heidi bounces: any migration that adds a Sample column, or any change that drops `samples.matrix` in this packet.

## 4. Contracts

### Plan line (aliquot and pool)

Extend the existing aliquot/pool plan row shape (entry `experiment_data` / predefined aliquot-pool plan):

```python
class AliquotPoolPlanLine(BaseModel):
    method: str                         # existing (by mass, by volume, …)
    source_sample_id: UUID
    # … existing amount / dest container fields …
    dest_sample_type: UUID | None = None  # optional list entry id; blank = parent
```

Same field on **pool** lines. UI: control sits next to method (Mathilda: entry setup only).

### Execute

```text
In one DB transaction (existing aliquot/pool execute):
  for each plan line:
    parent = source sample
    type_id = line.dest_sample_type or parent.sample_type
    dest = Sample(
      parent_sample_id=parent.id,
      sample_type=type_id,
      # matrix / project / other fields: existing execute rules (matrix NOT in scope to change)
    )
    create dest 1×1 container + contents (existing)
    if experiment has process_id / process step:
      upsert eln_process_samples(
        process_id=current,
        sample_id=dest.id,
        status=queued,           # waiting for next step start
        # do not mark removed
      )
```

Ad hoc experiment (no process): skip the process-sample insert.

### Lookup after execute

Next step (e.g. Qubit LimsRun / experiment) uses Decision #24 eligibility: Available for Testing + on `eln_process_samples`. Dest must appear in the process queue after extract.

## 5. Entry setup UX (review only — no product code here)

| Surface | Change |
|---------|--------|
| Aliquot/pool plan entry | Optional “Dest sample type” select (sample_type list), beside Method |
| Blank | Placeholder “Same as parent” |
| Pool | Same control; one dest type per pool dest sample |

Mathilda reviews this sketch for entry setup. No product UI code until Leadership Accept + implement packet.

## 6. Locked vs parked

| Locked now | Later, not this packet |
|------------|------------------------|
| Optional dest `sample_type` on aliquot + pool | TruSeq / library dest-type UI |
| Execute → `samples.sample_type` + `parent_sample_id` | Drop / remodel `samples.matrix` |
| Dest on `eln_process_samples` for this instance | SOP+AI Apply → process definition |
| Existing columns only | New Sample columns |

## 7. Tests (when implement opens)

| Case | Expect |
|------|--------|
| Aliquot, dest type set | Dest `sample_type` = chosen; `parent_sample_id` set; on process samples |
| Aliquot, dest type blank | Dest `sample_type` = parent |
| Pool, dest type set | Same as aliquot for the pool dest |
| Ad hoc experiment | Dest created; no process-sample row |
| Migration scan | No new Sample column |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| Architecture | Open — bounce new Sample column or matrix drop |
| UI | Open — entry setup only if needed; no product UI code |
| Lab Ops | Open |
| CEO | Open — no implement until Accept |

## 9. Relationship to Hold

This packet is the **minimum** to lift Extract-then-Qubit Hold for dest **type** and process membership. It does **not** claim SOP+AI → live process (still a lie per PR 51). Matrix remainders and TruSeq stay out.
