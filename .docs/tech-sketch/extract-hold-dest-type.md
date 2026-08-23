# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN.** Land S3 + L2 + seeds (Blood×aliquot→DNA, DNA×pool→pooled DNA). Security/CSO Accept ([PR 55](https://github.com/Marc02130/nimblelims/pull/55)).  
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

**Goals (locked — Marc implement order 2026-08-23)**

- Sample type can change through a process (gate, not extract-by-rename).
- Optional dest `sample_type` on **aliquot and pool** beside Method. Blank = “Same as parent.” — always allowed.
- **Catalog = many-to-many:** separate rows per dest. Multi-hop = process steps.
- **L2:** dest type only on the **plan entry**. Execute does **not** re-prompt type.
- Pool: all sources share one `sample_type` or refuse; then catalog lookup.
- Execute: write `samples.sample_type`, `parent_sample_id`; **L1/S1** join execute-minted dest onto this instance after start; append 403.
- Start-time entry gate: `template_definition.accepted_sample_types`.
- **C2:** eligibility / Qubit key off `sample_type`, not matrix.
- **S3:** `sample_type_transitions` mutate is **`config:edit` only**.
- **Seed with implement:** Blood × aliquot → DNA **and** DNA × pool → pooled DNA.

**Non-goals / bounce bars (Heidi + Marc)**

- No new Sample / `material_class` column.
- No matrix drop.
- No receive / mid-entry type gate.
- No if-blood-then.
- No transitions on `template_definition`.
- **No new experiment-plan object** — extend existing aliquot/pool plan entry only.
- TruSeq; SOP+AI Apply; IC50; mixed container contents as pool.

## 3. Data model

```
samples.sample_type                       ← existing
samples.parent_sample_id                  ← existing
samples.matrix                            ← unchanged
eln_process_samples                       ← L1/S1 execute-minted join
template_definition.accepted_sample_types ← step ENTRY allow-list only
sample_type_transitions                   ← NEW system-wide client catalog (many-to-many)
```

### Catalog table (many-to-many)

| Column | Notes |
|--------|--------|
| `source_sample_type` | FK |
| `operation` | `aliquot` \| `pool` |
| `allowed_dest_sample_type` | FK — one dest per row |

Unique `(client_id, source, operation, dest)`.

**Seed with implement:**

| source | operation | allowed dest |
|--------|-----------|--------------|
| Blood | aliquot | DNA |
| DNA | pool | pooled DNA |

### AuthZ

| Surface | Who |
|---------|-----|
| Catalog mutate | **`config:edit` only** (S3) |
| Execute-minted process-sample join | This instance, same client, `experiment:manage` (S1) |
| Arbitrary append | 403/404 |

## 4. Contracts

### Plan entry (L2)

Dest type beside Method on existing aliquot/pool plan lines (no new experiment-plan object). Options = catalog dests for source × op (+ Same as parent). No execute re-prompt.

### Execute

```text
if pool and sources do not share one sample_type: refuse
type_id = dest_sample_type or source_type
if type_id != source_type and no catalog_row(source, op, type_id): refuse
create dest; L1/S1 join if under process
```

## 5. Entry setup UX

| Rule | Detail |
|------|--------|
| Dest type | Existing plan entry only, beside Method |
| Options | Catalog rows for source × op |
| Blank | Same as parent |
| Pool | One shared source type or refuse |
| Bounce | Free-text; execute re-prompt; receive/mid-entry gate; sample-ID box |

## 6. Locked vs parked

| Locked | Parked |
|--------|--------|
| Seeds Blood×aliquot→DNA + DNA×pool→pooled DNA | Full fraction catalog |
| Existing aliquot/pool entry only | New experiment-plan object |
| L1/S1; L2; S3; start allow-list | Matrix drop; TruSeq |

## 7. Tests

| Case | Expect |
|------|--------|
| Blood×aliquot→DNA (seeded) | OK |
| DNA×pool→pooled DNA (seeded) | OK |
| Off-table dest | Refuse |
| Execute type prompt | Absent (L2) |
| Pool mixed source types | Refuse |
| Catalog mutate without config:edit | 403 (S3) |
| New experiment-plan object | Bounce |

## 8. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — implement order 2026-08-23 |
| Architecture | **Accept** — bounce bars stand |
| UI | **Accept (U6)** — entry setup as sketched |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) — PR 55 |

**Implement gate:** **OPEN.** Land S3 + L2 + both seeds. Compose up only while implementing/testing, then down. Not IC50.

## 9. Relationship to Hold

Lifts Extract-then-Qubit Hold once implemented. Not SOP+AI → live process (PR 51).
