# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Follow-up fold after PR 52 merge. Architecture Revise + UI Hold until this lands. Implement gate CLOSED until Lab Ops + CSO + Architecture/UI re-Accept.**  
**Stem:** `extract-hold-dest-type`  
**Supersedes on main:** PR 52 docs (merged without Marc 2026-08-23 fold)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.1b / §0.8  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest sample that inherits parent identity fields and **does not** join `eln_process_samples`. Extract-then-Qubit (blood → DNA → Qubit on DNA) cannot run: the daughter looks like blood and is not on the process instance. PR 52 on main unlocked dest type on plan lines but **missed** the Marc fold (L1/C2/C3 + start-time type gate + allow-list on `template_definition`).

## 2. Goals and non-goals

**Goals (locked — Marc CEO Accept + 2026-08-23 fold)**

- **Sample type can change through a process** (dest type on aliquot execute is the wedge).
- Optional dest `sample_type` on **aliquot** plan lines only, beside **method**. Blank / omitted → parent type.
- **C3:** Dest type ≠ parent is **aliquot-only**. **Pool** stays blank = parent (no dest-type override on pool lines).
- Execute (one transaction with existing aliquot/pool execute):
  1. Create dest sample with `parent_sample_id` = source.
  2. Set `samples.sample_type` from the aliquot plan line (or parent if blank). Pool dest always parent type.
  3. **L1/C1/S1:** If the experiment is under an ELN process step, insert **execute-minted** dest into `eln_process_samples` for **this process instance** (product of the step, **after start**). Status `queued` / waiting for next step — match existing assign semantics.
- **Start-time type gate:** At **experiment start** and **LimsRun start**, if the step template’s allow-list does not include this sample’s `sample_type`, start refuses. **Not** a receive gate. **Not** mid-entry.
- Allow-list lives on the step template as **`template_definition.accepted_sample_types`** (list of sample_type list-entry UUIDs). Existing JSONB key on template — **no new Sample column**.
- **C2:** While `samples.matrix` still copies parent, eligibility and Qubit key off **`sample_type`**, not matrix.
- Existing `samples.sample_type` (list FK) only.

**Non-goals**

- Dropping or rewriting `samples.matrix`.
- TruSeq / library dest-type (same rule later).
- SOP+AI Apply → process / parser.
- New tables. New Sample columns. IC50.
- Receive-time type gate. Mid-entry type check.
- Arbitrary append of samples onto a running process instance (stays refuse / 403).
- Product UI code in this PR (docs only).

## 3. Data model (existing only)

```
samples.sample_type                          ← existing list FK; dest write target; eligibility / Qubit key (C2)
samples.parent_sample_id                     ← existing; set on dest
samples.matrix                               ← unchanged this packet (still copies parent / current execute)
eln_process_samples                          ← existing; insert execute-minted dest for this instance only (L1)
entries / entry config                       ← aliquot plan line gains optional dest_sample_type; pool does not
experiment_templates.template_definition     ← existing JSONB; add accepted_sample_types[] allow-list
```

### `template_definition.accepted_sample_types` (Heidi)

```json
{
  "entries": [ /* existing */ ],
  "accepted_sample_types": ["<sample_type list_entry uuid>", "…"]
}
```

| Rule | Detail |
|------|--------|
| Where | On the **experiment / LimsRun template** used by the process step (`template_definition`) |
| Shape | Array of sample_type list-entry UUIDs |
| Empty / absent | No type gate (start does not refuse on type) |
| Non-empty | Start refuses any sample whose `sample_type` ∉ the list |
| Storage | JSONB key only — **no** new Sample / Process column |

Heidi bounces: new Sample column, matrix drop, receive gate, or dest type ≠ parent on pool.

## 4. Contracts

### Plan line — aliquot (optional dest type)

```python
class AliquotPlanLine(BaseModel):
    method: str                         # existing (by mass, by volume, …)
    source_sample_id: UUID
    # … existing amount / dest container fields …
    dest_sample_type: UUID | None = None  # optional list entry id; blank = parent
```

UI: control beside Method. Blank label **“Same as parent.”**

### Plan line — pool (C3)

Pool lines **do not** accept a dest type override. Dest always inherits parent `sample_type`. No dest-type control on the pool plan row.

### Execute + L1 join-after-start

```text
In one DB transaction (existing aliquot/pool execute):
  for each plan line:
    parent = source sample
    if line is aliquot:
      type_id = line.dest_sample_type or parent.sample_type
    else:  # pool — C3
      type_id = parent.sample_type
    dest = Sample(
      parent_sample_id=parent.id,
      sample_type=type_id,
      # matrix / project / other fields: existing execute rules (matrix NOT in scope to change)
    )
    create dest 1×1 container + contents (existing)
    if experiment has process_id / process step:  # L1/C1/S1 — after start, product of step
      upsert eln_process_samples(
        process_id=this_instance,
        sample_id=dest.id,
        status=queued,
        # do not mark removed
      )
```

Ad hoc experiment (no process): skip the process-sample insert.

### L1/C1/S1 — join AuthZ

| Path | Verdict |
|------|--------|
| Execute-minted dest joins **this** process instance **after start** | Allowed (product of the step) |
| Arbitrary append of an existing sample onto a running instance | **Refuse / 403** |
| AuthZ | This instance, same client, `experiment:manage` |

### Start-time type gate

At **experiment start** and **LimsRun start** (Decision #24 moment — start dialog only):

```text
allow = template_definition.accepted_sample_types  # may be empty/absent
if allow is non-empty:
  for each sample entering the step:
    if sample.sample_type not in allow:
      refuse start  # clear error: type not accepted for this step
```

- **Not** checked at receive.
- **Not** checked mid-entry (while filling the experiment / run).
- Uses `sample_type` only (**C2**), not matrix.

### Lookup after execute (C2)

Next step (e.g. Qubit LimsRun / experiment) eligibility: Available for Testing + on `eln_process_samples` + start-time type gate. Dest must appear in the process queue after extract. Qubit and eligibility key off **`sample_type`**, not matrix (matrix may still equal parent).

## 5. Entry setup UX (review only — no product code here)

| Surface | Change |
|---------|--------|
| **Aliquot** plan entry | Optional “Dest sample type” select, **beside Method** |
| Blank | Placeholder **“Same as parent.”** |
| **Pool** plan entry | **No** dest-type control (C3 — always parent) |
| Template authoring | Optional `accepted_sample_types` on step template (list multi-select) — docs only here |

**UI bounce bars (Mathilda)**

- Dest type control sits beside Method on **aliquot** only.
- Blank label is **“Same as parent.”**
- Dest type ≠ parent is **aliquot-only**; pool has no override.
- **No sample-ID box** on this surface.
- **No wizard** for dest type.
- **No hop** to sample detail to set type.
- **No receive gate** for type.
- **No mid-entry** type check (gate is start only).

No product UI code until Leadership Accept + implement packet.

## 6. Locked vs parked

| Locked now | Later, not this packet |
|------------|------------------------|
| Sample type may change through a process | TruSeq / library dest-type UI |
| Optional dest `sample_type` on **aliquot** only (C3) | Drop / remodel `samples.matrix` |
| Pool dest type = parent always | SOP+AI Apply → process definition |
| Execute → `samples.sample_type` + `parent_sample_id` | New Sample columns |
| Execute-minted dest joins this instance after start (L1); arbitrary append 403 | Receive-time or mid-entry type gate |
| `template_definition.accepted_sample_types` + start gate | Product UI code |
| Eligibility / Qubit key off `sample_type` (C2) | |
| Existing Sample columns only | |

## 7. Tests (when implement opens)

| Case | Expect |
|------|--------|
| Aliquot, dest type set | Dest `sample_type` = chosen; `parent_sample_id` set; on process samples |
| Aliquot, dest type blank | Dest `sample_type` = parent |
| Pool plan with dest type set | **Reject / ignore** — pool always parent type (C3) |
| Pool execute | Dest `sample_type` = parent; still joins process samples if under process |
| Ad hoc experiment | Dest created; no process-sample row |
| Arbitrary append to running instance | 403 (L1) |
| Start with `accepted_sample_types` non-empty, type not in list | Refuse start |
| Start with type in list | Allow |
| Start with allow-list empty/absent | No type refuse |
| Receive with mismatched type | **No** type gate |
| Mid-entry type check | **No** gate |
| Eligibility / Qubit | Keys off `sample_type`, not matrix (C2) |
| Migration scan | No new Sample column; only `template_definition` JSON key |
| Entry setup | Dest type beside Method on aliquot only; blank = “Same as parent.”; no sample-ID box / wizard / detail hop / receive gate |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** (Marc 2026-08-23) — fold required before implement; PR 52 merged without fold → this follow-up |
| Architecture | **Revise** (Heidi) — bounce until L1/C1/S1, C2, C3, and `template_definition.accepted_sample_types` land; bounce new Sample column, matrix drop, receive gate; dest ≠ parent aliquot-only |
| UI | **Hold** (Mathilda) — re-read when fold has C3, start-time gate, L1; bounce receive gate, sample-ID box, mid-entry type check |
| Lab Ops | Open — Leadership |
| CSO | Open — Leadership |

**Implement gate:** CLOSED until this follow-up is Accept’d and Lab Ops + CSO sign.

## 9. Relationship to Hold

This packet is the **minimum** to lift Extract-then-Qubit Hold for dest **type** and process membership, plus the start-time type gate so a DNA daughter can enter Qubit while blood cannot. It does **not** claim SOP+AI → live process (still a lie per PR 51). Matrix remainders and TruSeq stay out.
