# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN.** UI Accept (re-read). Architecture re-read pending on two-entry fold. Land S3 + L2 + seeds + `dest_sample_type` on `AliquotPlanLine`.  
**Stem:** `extract-hold-dest-type`  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 / §0.9  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest that inherits parent identity and does not join `eln_process_samples`. Extract-then-Qubit cannot run. Dest type must be chosen on the **plan entry** before execute — not on the after-execute daughter list.

**Heidi bounce (main today):** plan lines have no `dest_sample_type`; execute still copies `parent.sample_type`. That field must land on `AliquotPlanLine` / plan config — not a new plan object, not on `aliquots_pools`.

## 2. Two entries (Marc + Heidi map — no plan object)

Aliquot/pool is **two predefined entries**, not a new experiment-plan object.

| Role | `predefined_entry_key` | Kind | When | Owns |
|------|------------------------|------|------|------|
| **Plan entry** | `aliquot_pool_plan` | `experiment_data` | Before / at execute | **Method** + **dest sample_type** beside each other on each plan line. Template pre-fill OK. Clear = Same as parent. Catalog limits options. Method drives default columns and aliquot vs pool (incl. pool count). |
| **Dest sample entry** | `aliquots_pools` | `experiment_sample_data` | **AFTER execute only** | Lists minted daughter samples. **Not** where method/type are chosen. No method/type picker. |

**Flow:** Execute reads `aliquot_pool_plan` → mints dests (type from plan line or parent if blank) → L1/S1 join → `aliquots_pools` lists them. **No re-prompt.**

## 3. Goals and non-goals

**Goals (locked)**

- Optional `dest_sample_type` on each **`AliquotPlanLine`** (plan entry), beside Method.
- Blank / clear = Same as parent — always allowed.
- Catalog many-to-many limits the select; multi-hop = process steps.
- Pool: one shared source `sample_type` or refuse; then catalog lookup.
- Execute: write `samples.sample_type`, `parent_sample_id`; L1 join; no type re-prompt (**L2**).
- Start-time `template_definition.accepted_sample_types`; **C2** key off `sample_type`.
- **S3:** catalog mutate = `config:edit` only.
- **Seed:** Blood × aliquot → DNA; DNA × pool → pooled DNA.

**Non-goals / bounce bars**

- No new experiment-plan object.
- No Method / dest-type picker on `aliquots_pools`.
- No Sample / `material_class` column; no matrix drop; no receive/mid-entry type gate; no if-blood-then; no transitions on `template_definition`.
- TruSeq; SOP+AI Apply; IC50.

## 4. Data model

```
samples.sample_type                       ← existing; dest write target
samples.parent_sample_id                  ← existing
samples.matrix                            ← unchanged
eln_process_samples                       ← L1/S1 execute-minted join
template_definition.accepted_sample_types ← step ENTRY allow-list only
sample_type_transitions                   ← NEW catalog (many-to-many)
AliquotPlanLine.dest_sample_type          ← NEW optional field on plan line (Heidi bounce)
```

### Plan line contract

```python
class AliquotPlanLine(BaseModel):  # on aliquot_pool_plan experiment_data
    method: str                         # existing — drives aliquot vs pool + columns
    source_sample_id: UUID
    # … existing amount / dest container fields …
    dest_sample_type: UUID | None = None  # MUST land here — blank = parent
```

### Catalog (many-to-many)

| Column | Notes |
|--------|--------|
| `source_sample_type` | FK |
| `operation` | `aliquot` \| `pool` (from Method / line) |
| `allowed_dest_sample_type` | FK — one dest per row |

**Seed:** Blood×aliquot→DNA; DNA×pool→pooled DNA.

### AuthZ

| Surface | Who |
|---------|-----|
| Catalog mutate | `config:edit` only (S3) |
| Execute-minted process-sample join | This instance, same client, `experiment:manage` (S1) |
| Arbitrary append | 403/404 |

## 5. Execute

```text
Read aliquot_pool_plan lines (not aliquots_pools)
for each line:
  if pool and sources do not share one sample_type: refuse
  type_id = line.dest_sample_type or source.sample_type
  if type_id != source.sample_type and no catalog_row(...): refuse
  mint dest; L1/S1 join if under process
Refresh / populate aliquots_pools with minted daughters
# never prompt for dest type at execute
```

## 6. Entry setup UX (Mathilda)

| Surface | Rule |
|---------|------|
| `aliquot_pool_plan` | Method + dest type beside each other; catalog options; clear = Same as parent; template pre-fill OK |
| `aliquots_pools` | After-execute daughters only — no method/type picker |
| Bounce | Method/type on daughters; new plan object; free-text; execute re-prompt; receive/mid-entry gate; sample-ID box |

**UI Accept (re-read 2026-08-23):** Method + dest type only on `aliquot_pool_plan`; `aliquots_pools` after-execute only; clear = Same as parent. Bounce method/type on daughters or a new plan object.

## 7. Tests

| Case | Expect |
|------|--------|
| Plan line has `dest_sample_type` field | Present on AliquotPlanLine / plan config |
| Blood×aliquot→DNA (seeded) | Dest type DNA after execute |
| DNA×pool→pooled DNA (seeded) | OK |
| Blank dest type | Dest = parent type |
| Execute still copies parent only (no field) | **Fail** — Heidi bounce |
| Method/type on aliquots_pools | Bounce / absent |
| Catalog mutate without config:edit | 403 |
| New experiment-plan object | Bounce |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — two-entry lock |
| Architecture | Map + bounce issued; **re-read** of this fold |
| UI | **Accept** (Mathilda re-read 2026-08-23) — Method + dest type on `aliquot_pool_plan` only; `aliquots_pools` after-execute only; clear = Same as parent; bounce method/type on daughters or new plan object |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN.** Land `dest_sample_type` on plan line, S3, L2, both seeds. Compose up only while implementing/testing, then down. Not IC50.

## 9. Relationship to Hold

Lifts Extract-then-Qubit Hold once implemented. Not SOP+AI → live process (PR 51).
