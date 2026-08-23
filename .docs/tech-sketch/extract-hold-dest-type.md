# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN.** Land S3 (`config:edit` on catalog mutate) + Lab Ops L2 + Blood×aliquot→DNA seed. Security/CSO Accept with conditions ([PR 55](https://github.com/Marc02130/nimblelims/pull/55)).  
**Stem:** `extract-hold-dest-type`  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.1b / §0.8  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest that inherits parent identity and does not join `eln_process_samples`. Extract-then-Qubit cannot run. Allowed dest-type transitions are **system-wide configuration** (many-to-many rows), not hardcoded if-blood-then.

## 2. Goals and non-goals

**Goals (locked)**

- Sample type can change through a process (gate, not extract-by-rename).
- Optional dest `sample_type` on **aliquot and pool** beside Method. Blank = “Same as parent.” — always allowed.
- **Catalog = many-to-many:** one source × operation → many dests via **separate rows** (e.g. Blood × aliquot → plasma | DNA | RBC | WBC | buffy coat). Not a chained single row.
- **Multi-hop = process steps** (Blood → plasma, then plasma → cfDNA), not one catalog edge that skips intermediates.
- **L2 (Lab Ops):** dest type only on the **plan entry**. Execute does **not** re-prompt type.
- Pool: all sources share one `sample_type` or refuse; then catalog lookup for that type × pool → dest.
- Execute: write `samples.sample_type`, `parent_sample_id`; **L1 / S1** join execute-minted dest onto this instance after start; append 403.
- Start-time entry gate: `template_definition.accepted_sample_types` (not the transition catalog).
- **C2:** eligibility / Qubit key off `sample_type`, not matrix.
- **S3:** `sample_type_transitions` mutate is **`config:edit` only** — not Client, not `experiment:manage` alone.
- **Seed with implement:** Blood × aliquot → DNA.

**Non-goals**

- Matrix drop; TruSeq; SOP+AI Apply; IC50.
- Transition rules on entries or template JSON.
- Hardcoded if-blood-then.
- Mixed container contents as pool.
- Receive / mid-entry type gates; execute re-prompt for dest type.

## 3. Data model

```
samples.sample_type                       ← existing
samples.parent_sample_id                  ← existing
samples.matrix                            ← unchanged
eln_process_samples                       ← L1/S1 execute-minted join
template_definition.accepted_sample_types ← step ENTRY allow-list only
sample_type_transitions                   ← NEW system-wide client catalog (many-to-many rows)
```

### Catalog table (many-to-many)

| Column | Notes |
|--------|--------|
| `source_sample_type` | FK |
| `operation` | `aliquot` \| `pool` |
| `allowed_dest_sample_type` | FK — one dest per row |

Unique `(client_id, source, operation, dest)`. One source may have many rows for the same operation.

**Seed with implement:** Blood × aliquot → DNA.  
**Multi-hop:** Blood→plasma then plasma→cfDNA = two process steps + catalog rows — not one chained edge unless CSO adds a direct row.

### AuthZ

| Surface | Who |
|---------|-----|
| Transition catalog mutate (create/update/delete) | **`config:edit` only** (**S3**) — not Client, not `experiment:manage` alone |
| Execute-minted process-sample join | This instance, same client, `experiment:manage` (**S1** Met) |
| Arbitrary append | 403/404 |

## 4. Contracts

### Plan entry (L2)

Dest type select beside Method on aliquot/pool plan. Options = all catalog dests for source × op (+ Same as parent). **No execute re-prompt.**

### Execute

```text
if pool and sources do not share one sample_type: refuse
type_id = dest_sample_type or source_type
if type_id != source_type and no catalog_row(source, op, type_id): refuse
create dest; L1/S1 join if under process
# never prompt for dest type at execute
```

## 5. Entry setup UX

| Rule | Detail |
|------|--------|
| Dest type | Plan entry only, beside Method |
| Options | Many-to-many catalog rows for that source × op |
| Blank | Same as parent (always) |
| Execute | No type re-prompt (L2) |
| Bounce | Free-text; receive/mid-entry gate; sample-ID box; wizard; detail hop |

## 6. Locked vs parked

| Locked | Parked |
|--------|--------|
| Many-to-many catalog rows | Full fraction seed beyond Blood→DNA |
| Multi-hop = process steps | TruSeq; matrix drop |
| L1/S1 Met; L2; S3 config:edit | |
| Seed Blood×aliquot→DNA with implement | |
| Gate OPEN | |

## 7. Tests

| Case | Expect |
|------|--------|
| Blood×aliquot→DNA (seeded) | OK |
| Off-table dest | Refuse |
| Execute type prompt | Absent (L2) |
| Pool mixed source types | Refuse |
| L1/S1 join after start | Dest on process samples |
| Catalog mutate without config:edit | **403** (S3) |
| Catalog mutate with experiment:manage only | **403** (S3) |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** |
| Architecture | **Accept** |
| UI | **Accept (U6)** |
| Lab Ops | **Accept with conditions** (L1 Met; L2) |
| Security / CSO | **Accept with conditions** (S1 Met; S3) — [PR 55](https://github.com/Marc02130/nimblelims/pull/55) |

**Implement gate:** **OPEN.** Implement must land **S3** + **L2** + Blood×aliquot→DNA seed. Not IC50.

## 9. Relationship to Hold

Lifts Extract-then-Qubit Hold for dest type + process membership once implemented. Not SOP+AI → live process (PR 51).
