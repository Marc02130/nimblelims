# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Architecture Accept + UI Accept (conditions, U6 stamped). Implement gate CLOSED until Lab Ops + CSO.**  
**Stem:** `extract-hold-dest-type`  
**Supersedes on main:** PR 52 docs (merged without Marc fold)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.1b / §0.8  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest sample that inherits parent identity fields and **does not** join `eln_process_samples`. Extract-then-Qubit cannot run. Allowed dest-type transitions must be **system-wide configuration**, not hardcoded if-blood-then, not per-entry, not on `template_definition`.

## 2. Goals and non-goals

**Goals (locked — Marc + Heidi 2026-08-23)**

- **Sample type can change through a process** (gate, not extract-by-rename).
- Optional dest `sample_type` on **aliquot and pool** beside **method**. Blank = “Same as parent.” — **always allowed**; no same-type catalog row.
- **C3 retracted:** Pool may set dest type ≠ parent when the catalog allows it.
- **Transitions = system-wide / client catalog table** (not per entry, not on `template_definition`):
  - `source_sample_type` × `operation` (`aliquot` | `pool`) × `allowed_dest_sample_type`
  - Entry setup offers only matching dests for that source × operation
  - Execute refuses off-table dest types
  - Seed examples (config rows, not code): Blood × aliquot → DNA; DNA × pool → pooled DNA
- **Pool same-type rule (Marc; supersedes every-source-has-a-row for mixed types):**
  - All source samples on a pool plan must share **one** `sample_type`
  - Mixed source types → **refuse**
  - Then **one** catalog row: that type × `pool` → dest
- Execute:
  1. Pool: assert single shared source type (else refuse).
  2. Resolve dest type (blank → parent).
  3. If dest ≠ parent: require catalog row `(source_type, op, dest_type)`; else refuse.
  4. Create dest (`parent_sample_id`, `samples.sample_type`).
  5. **L1/C1/S1:** under process → insert execute-minted dest into `eln_process_samples` for **this** instance after start.
- **Start-time entry gate:** `template_definition.accepted_sample_types` at experiment + LimsRun start only. Not receive. Not mid-entry. Separate from the transition catalog.
- **C2:** Eligibility / Qubit key off `sample_type`, not matrix.
- Existing `samples.sample_type` only. No Sample / `material_class` column.

**Non-goals**

- Matrix drop; TruSeq; SOP+AI Apply; IC50; product UI code.
- Transition rules on entries or as JSON on `template_definition`.
- Hardcoded if-blood-then.
- **Mixed container contents** (cells, compound, buffer) — that is experiment contents, **not** pool. Out of this packet.
- Receive / mid-entry type gates; free-text dest type; arbitrary process append (403).

## 3. Data model

```
samples.sample_type                          ← existing; dest write; eligibility / Qubit (C2)
samples.parent_sample_id                     ← existing
samples.matrix                               ← unchanged
eln_process_samples                          ← L1 execute-minted join
entries                                      ← optional dest_sample_type on aliquot|pool lines
template_definition.accepted_sample_types    ← step ENTRY allow-list only
sample_type_transitions                      ← NEW system-wide client catalog table
```

### Catalog table (system-wide client catalog)

| Column | Type | Notes |
|--------|------|--------|
| `source_sample_type` | FK → sample_type list | |
| `operation` | `aliquot` \| `pool` | |
| `allowed_dest_sample_type` | FK → sample_type list | |

Unique `(client_id, source_sample_type, operation, allowed_dest_sample_type)`. Not on Sample. Not on entries. Not on `template_definition`.

### `template_definition.accepted_sample_types`

Step **entry** allow-list at start only. Empty/absent → no entry-type refuse.

Heidi bounces: Sample/`material_class` column; template JSON transitions; if-blood-then; mixed source types on pool without refuse.

## 4. Contracts

### Plan line

```python
class AliquotPoolPlanLine(BaseModel):
    method: str
    source_sample_id: UUID
    dest_sample_type: UUID | None = None  # blank = parent (always allowed)
```

### Entry setup

```text
# Aliquot: source = that line's parent type
# Pool: only after sources share one type; options for that type × pool
options = catalog rows WHERE source = shared_source_type AND operation = this_op
UI: beside Method; Blank = "Same as parent."; options only — no free-text
```

### Execute

```text
In one DB transaction:
  if op is pool:
    source_types = distinct sample_type of all pool sources
    if len(source_types) != 1:
      refuse  # mixed source types — Marc same-type rule
    source_type = that one type
  else:
    source_type = parent.sample_type

  type_id = line.dest_sample_type or source_type
  if type_id != source_type:
    if not catalog_row(source_type, op, type_id):
      refuse

  create dest Sample(parent_sample_id=…, sample_type=type_id, …)
  if under process: upsert eln_process_samples(this_instance, dest, queued)  # L1
```

### L1 AuthZ

| Path | Verdict |
|------|--------|
| Execute-minted dest joins this instance after start | Allowed |
| Arbitrary append | **403** |
| AuthZ | This instance, same client, `experiment:manage` |

### Start-time entry gate

```text
if accepted_sample_types non-empty and sample.sample_type not in list: refuse start
```

## 5. Entry setup UX (review only)

| Surface | Rule |
|---------|------|
| Dest type | Beside Method; catalog options for source × aliquot\|pool; Blank = Same as parent |
| Pool | Enable dest select only when all sources share one type; else block / refuse |
| Bounce | Free-text; receive gate; mid-entry type check; sample-ID box; wizard; detail hop |

**Mathilda UI Accept conditions (U6 stamped 2026-08-23)**

- Pool needs one shared source type; mixed types refuse; then one catalog row.
- Dest type beside Method; catalog options only; blank = Same as parent.
- Bounce free-text, receive gate, mid-entry type check.

## 6. Locked vs parked

| Locked | Parked |
|--------|--------|
| System-wide config table | Full CSO seed beyond examples |
| Blank always allowed | TruSeq; matrix drop |
| Pool: one shared source type or refuse; one catalog row | Mixed container contents (cells/compound/buffer) |
| L1; C2; entry allow-list on template | Product UI code; template JSON transitions |
| C3 retracted | Sample/`material_class` column |

## 7. Tests

| Case | Expect |
|------|--------|
| Aliquot blank | OK → parent type |
| Aliquot Blood→DNA with row | OK |
| Aliquot Blood→DNA without row | Refuse |
| Pool all DNA → pooled DNA with row | OK |
| Pool mixed Blood+DNA sources | **Refuse** (same-type rule) |
| Pool Blood→DNA (no pool row) | Refuse |
| Entry select | Catalog dests only + Same as parent |
| Free-text / receive / mid-entry gate | Bounce / absent |
| Append | 403 |
| Migration | Catalog table OK; no Sample/`material_class` column |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** + same-type pool fold (Marc 2026-08-23) |
| Architecture | **Accept (re-stamp)** (Heidi 2026-08-23) — system-wide config table; blank always allowed; pool one shared source type; bounce Sample/`material_class`, template JSON transitions, if-blood-then |
| UI | **Accept with conditions** (Mathilda 2026-08-23, **U6 stamped**) — pool one shared source type; mixed refuse; one catalog row; dest type beside Method; catalog options only; blank = Same as parent; bounce free-text / receive / mid-entry |
| Lab Ops | Open |
| CSO | Open |

**Implement gate:** CLOSED until Lab Ops + CSO sign.

## 9. Relationship to Hold

Minimum to lift Extract-then-Qubit Hold for dest type + process membership + start entry gate, with transitions as system-wide config. Not SOP+AI → live process (PR 51). Matrix and TruSeq out.
