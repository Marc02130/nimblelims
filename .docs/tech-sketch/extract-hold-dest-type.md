# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Config-table fold (Marc + Heidi). Architecture pick locked. UI re-read. Implement gate CLOSED until Lab Ops + CSO + UI re-Accept.**  
**Stem:** `extract-hold-dest-type`  
**Supersedes on main:** PR 52 docs (merged without Marc fold)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.1b / §0.8  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest sample that inherits parent identity fields and **does not** join `eln_process_samples`. Extract-then-Qubit (blood → DNA → Qubit on DNA) cannot run: the daughter looks like blood and is not on the process instance. Material-class / allowed-dest rules must be **configuration**, not hardcoded if-blood-then.

## 2. Goals and non-goals

**Goals (locked — Marc + Heidi 2026-08-23)**

- **Sample type can change through a process** so the step allow-list can refuse wrong material. That is a **gate**, not an extract-by-rename.
- Optional dest `sample_type` on **aliquot and pool** plan lines, beside **method**. Blank / omitted → parent type (“Same as parent.”) — **always allowed** (no-change); no same-type catalog row required.
- **C3 retracted:** Pool **may** set dest type ≠ parent when the **config table** allows it.
- **Material-class rules = config table** (lab-wide catalog), **not** JSON on the template, **not** code:
  - Columns: `source_sample_type` × `operation` (`aliquot` | `pool`) × `allowed_dest_sample_type`
  - Entry setup only offers dest types from rows matching that source × operation
  - Execute refuses any set dest type not in the table
  - Examples (two process steps, two rows — not hardcoded):
    - Blood → DNA = **aliquot** config row
    - DNA → pooled DNA = **pool** config row
- Execute (one transaction with existing aliquot/pool execute):
  1. Resolve dest type (blank → parent).
  2. If dest type ≠ parent: require a catalog row for `(source.sample_type, operation, dest_type)`; else refuse.
  3. Create dest with `parent_sample_id` + `samples.sample_type`.
  4. **L1/C1/S1:** If under an ELN process step, insert **execute-minted** dest into `eln_process_samples` for **this** instance (**after start**).
- **Start-time type gate:** At **experiment start** and **LimsRun start**, if `template_definition.accepted_sample_types` is non-empty and the sample’s type is not in it, start refuses. **Not** receive. **Not** mid-entry. This list is the step **entry** allow-list only — separate from the transition catalog.
- **C2:** Eligibility and Qubit key off **`sample_type`**, not matrix.
- Existing `samples.sample_type` only. **No Sample column** for material class.

**Non-goals**

- Dropping or rewriting `samples.matrix`.
- TruSeq / library dest-type (same rule later).
- SOP+AI Apply → process / parser.
- New **Sample** columns. `material_class` on Sample. IC50.
- Transition rules as JSON on `template_definition` (Heidi: **config table**).
- Hardcoded if-blood-then (or any hard-coded type pair) in execute.
- Receive-time type gate. Mid-entry type check.
- Arbitrary append onto a running process instance (403).
- Product UI code in this PR (docs only).

## 3. Data model

```
samples.sample_type                          ← existing list FK; dest write; eligibility / Qubit (C2)
samples.parent_sample_id                     ← existing; set on dest
samples.matrix                               ← unchanged this packet
eln_process_samples                          ← execute-minted dest join (L1)
entries / entry config                       ← aliquot AND pool: optional dest_sample_type
experiment_templates.template_definition     ← accepted_sample_types[] = step ENTRY allow-list only
sample_type_transitions (NEW catalog table)  ← source_sample_type × operation × allowed_dest_sample_type
```

### Catalog table (Heidi: config table, not template JSON)

Lab-wide, client-scoped as with other catalogs (same tenancy as list entries). Not a Sample column.

| Column | Type | Notes |
|--------|------|--------|
| `source_sample_type` | FK → sample_type list entry | Parent type |
| `operation` | enum `aliquot` \| `pool` | Which execute path |
| `allowed_dest_sample_type` | FK → sample_type list entry | Dest type the UI may offer / execute may write |

Unique on `(client_id, source_sample_type, operation, allowed_dest_sample_type)` (or equivalent).

**Seed / CSO examples (config rows, not code):**

| source | operation | allowed dest |
|--------|-----------|--------------|
| Blood | aliquot | DNA |
| DNA | pool | pooled DNA |

Two process steps use those rows. No if-blood-then in the engine.

### `template_definition.accepted_sample_types` (step entry only)

```json
{
  "entries": [ /* existing */ ],
  "accepted_sample_types": ["<sample_type list_entry uuid>", "…"]
}
```

| Rule | Detail |
|------|--------|
| Role | Which types may **enter** this step at start |
| Not | Transition / material-class catalog (that is the config table) |
| Empty / absent | No entry-type refuse at start |
| Non-empty | Start refuses sample whose `sample_type` ∉ list |

Heidi bounces: new Sample column, matrix drop, receive/mid-entry gates, transition rules as template JSON, hardcoded type pairs.

## 4. Contracts

### Plan line — aliquot and pool

```python
class AliquotPoolPlanLine(BaseModel):
    method: str
    source_sample_id: UUID
    # … existing amount / dest container fields …
    dest_sample_type: UUID | None = None  # blank = parent (always allowed)
```

### Entry setup (Mathilda)

```text
options = SELECT allowed_dest_sample_type
          FROM sample_type_transitions
          WHERE source_sample_type = parent.sample_type
            AND operation = aliquot|pool   # this plan row's operation
# UI: Dest sample type select beside Method
#     always includes Blank = "Same as parent."
#     plus options above only — no free-text type
```

### Execute + catalog check + L1

```text
In one DB transaction (existing aliquot/pool execute):
  for each plan line:
    parent = source sample
    op = aliquot|pool
    if line.dest_sample_type is blank:
      type_id = parent.sample_type          # always allowed (no-change)
    else:
      type_id = line.dest_sample_type
      if not exists catalog row (parent.sample_type, op, type_id):
        refuse execute                      # off-table
    dest = Sample(parent_sample_id=parent.id, sample_type=type_id, …)
    create dest 1×1 container + contents (existing)
    if experiment under process step:       # L1/C1/S1
      upsert eln_process_samples(this_instance, dest.id, status=queued)
```

Ad hoc (no process): skip process-sample insert.

### L1/C1/S1 — join AuthZ

| Path | Verdict |
|------|--------|
| Execute-minted dest joins **this** instance **after start** | Allowed |
| Arbitrary append to running instance | **403** |
| AuthZ | This instance, same client, `experiment:manage` |

### Start-time type gate (entry allow-list)

```text
allow = template_definition.accepted_sample_types
if allow is non-empty and sample.sample_type not in allow:
  refuse start
```

Not receive. Not mid-entry. Keys off `sample_type` only (**C2**).

## 5. Entry setup UX (review only — no product code)

| Surface | Change |
|---------|--------|
| Aliquot / pool plan | Dest type select **beside Method** |
| Blank | **“Same as parent.”** — always present / always allowed |
| Options | Only catalog rows for that source × this operation |
| Bounce | Free-text type; mid-entry type gate; receive gate; sample-ID box; wizard; hop to sample detail |

## 6. Locked vs parked

| Locked now | Later, not this packet |
|------------|------------------------|
| Config table source × aliquot\|pool × allowed dest | Full CSO seed beyond Blood→DNA / DNA→pooled DNA |
| Blank = Same as parent always allowed | TruSeq / library dest-type |
| Entry select filtered to catalog | Drop / remodel `samples.matrix` |
| Execute refuses off-table | SOP+AI Apply |
| L1 join-after-start; append 403 | Product UI code |
| `accepted_sample_types` = step entry only | Transition rules as template JSON |
| C2 key off `sample_type` | New Sample columns / `material_class` |
| C3 retracted (pool when config allows) | |

## 7. Tests (when implement opens)

| Case | Expect |
|------|--------|
| Aliquot blank | Dest type = parent; always OK |
| Aliquot Blood → DNA with catalog row | OK; dest type DNA; on process samples |
| Aliquot Blood → DNA without row | Refuse |
| Pool DNA → pooled DNA with catalog row | OK |
| Pool Blood → DNA (no row / wrong op) | Refuse |
| Entry select Blood + aliquot | Lists DNA (and other aliquot rows); plus Same as parent |
| Entry select DNA + pool | Lists pooled DNA; plus Same as parent |
| Free-text dest type | Bounce / not offered |
| Arbitrary append | 403 |
| Start allow-list miss | Refuse start |
| Receive / mid-entry type gate | **No** |
| Migration | Catalog table OK; **no** Sample column; **no** `material_class` |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** + config-table fold (Marc 2026-08-23) |
| Architecture | Prior Accept; **pick locked** — config table (not template JSON); `accepted_sample_types` = entry allow-list only; blank always allowed; re-stamp after this fold if needed |
| UI | Prior Accept (conditions); **re-read** after fold — select lists allowed dests only; bounce free-text / mid-entry gate |
| Lab Ops | Open |
| CSO | Open — owns catalog rows (Blood→DNA aliquot; DNA→pooled DNA pool) |

**Implement gate:** CLOSED until Lab Ops + CSO sign (and UI re-Accept after this fold).

## 9. Relationship to Hold

Minimum to lift Extract-then-Qubit Hold for dest **type** + process membership + start-time entry gate, with material transitions as **config**. Does **not** claim SOP+AI → live process (PR 51). Matrix and TruSeq stay out.
