# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN.** Architecture Accept + UI Accept on A + line override. Pending: concrete method (implies one mint op) when Deiter cut list lands. Land S3 + L2 + seeds + `dest_sample_type`.  
**Stem:** `extract-hold-dest-type`  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 / §0.9  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest that inherits parent identity and does not join `eln_process_samples`. Dest type must be chosen on the **plan entry** before execute. Main today: no `dest_sample_type` on plan lines; execute copies `parent.sample_type` — Heidi bounce.

## 2. Two entries (no plan object)

| Role | `predefined_entry_key` | Kind | When | Owns |
|------|------------------------|------|------|------|
| **Plan entry** | `aliquot_pool_plan` | `experiment_data` | Before / at execute | Entry config + plan lines (below) |
| **Dest sample entry** | `aliquots_pools` | `experiment_sample_data` | **AFTER execute only** | Lists minted daughters. No method/type picker. |

**Flow:** Execute reads `aliquot_pool_plan` → mints dests → L1/S1 join → `aliquots_pools` lists them. **No re-prompt.**

## 3. A + line override (Marc lock 2026-08-23)

### Entry config (`aliquot_pool_plan`)

| Field | Rule |
|-------|------|
| **Method** | Exactly **one** op for the whole entry: **aliquot OR pool**. Drives columns + mint. Set at template or add-time prompt. |
| **Default dest type** | Optional. Template pre-fill OK or prompt at add-time. Catalog limits. Blank/clear = Same as parent. |

**No mid-flight method change.** Once the entry exists with lines, changing method is **not** warn/wipe — **cancel the experiment**. Ops do not rewind.

**Pending tighten (Heidi):** entry `method` is the concrete method (by volume, …), which implies exactly one mint op — not only `Literal["aliquot"\|"pool"]`, or columns cannot shift. Fold when Deiter’s cut list lands.

### Plan lines

| Field | Rule |
|-------|------|
| `dest_sample_type` | Optional **line override**. May clear (= Same as parent) or set another catalog-allowed dest for this source × entry op. |

**Resolve at execute:**

```text
type_id =
  line.dest_sample_type if set
  else entry.default_dest_sample_type if set
  else source.sample_type   # Same as parent
if type_id != source.sample_type and no catalog_row(source, entry.op, type_id): refuse
```

### Bounce bars (Marc + Heidi + Mathilda)

- One entry minting **both** aliquot and pool (dual mint).
- **Silent reshape** of columns/mint after lines already exist (method change mid-flight).
- Warn/wipe instead of cancel.
- Method/type picker on `aliquots_pools`.
- New experiment-plan object.
- Sample/`material_class` column; matrix drop; receive/mid-entry type gate; if-blood-then; transitions on `template_definition`.

## 4. Goals (remainder)

- Catalog many-to-many; multi-hop = process steps.
- Pool: one shared source `sample_type` or refuse; then catalog lookup for entry op.
- L1/S1 join; L2 no execute re-prompt; S3 `config:edit` on catalog; C2 key off `sample_type`.
- **Seed:** Blood × aliquot → DNA; DNA × pool → pooled DNA.

## 5. Data model

```
samples.sample_type / parent_sample_id / matrix   ← existing (matrix unchanged)
eln_process_samples                               ← L1/S1 join
template_definition.accepted_sample_types         ← start entry allow-list
sample_type_transitions                           ← NEW catalog (many-to-many)
aliquot_pool_plan entry config:
  method                                          ← exactly one of aliquot|pool
  default_dest_sample_type                        ← optional
AliquotPlanLine.dest_sample_type                  ← optional line override (MUST land)
```

```python
# entry config on aliquot_pool_plan
class AliquotPoolPlanConfig(BaseModel):
    method: Literal["aliquot", "pool"]  # one op; drives columns + mint
    # PENDING Heidi: concrete method (by volume, …) implies one mint op — fold with Deiter cut list
    default_dest_sample_type: UUID | None = None  # blank = Same as parent

class AliquotPlanLine(BaseModel):
    source_sample_id: UUID
    # … amount / dest container fields (shape from entry.method) …
    dest_sample_type: UUID | None = None  # override or clear → Same as parent
```

## 6. Execute

```text
op = entry.method  # never dual mint
Read aliquot_pool_plan lines
for each line:
  if op is pool and sources do not share one sample_type: refuse
  type_id = line.dest_sample_type or entry.default_dest_sample_type or source.sample_type
  if type_id != source.sample_type and no catalog_row(source, op, type_id): refuse
  mint dest; L1/S1 join if under process
Populate aliquots_pools
# never prompt for dest type at execute
# never change entry.method mid-flight — cancel experiment instead
```

## 7. Entry setup UX

| Surface | Rule |
|---------|------|
| Entry add / template | Method (one op) + default dest type; catalog limits |
| Plan lines | May clear/override dest type within catalog |
| After lines exist | Method locked — change requires cancel experiment (no warn/wipe reshape) |
| `aliquots_pools` | After-execute daughters only |

## 8. Tests

| Case | Expect |
|------|--------|
| Entry method aliquot; default DNA; line blank | Dest DNA |
| Entry default DNA; line clears | Dest = parent (Same as parent) |
| Line overrides to catalog-allowed type | That type |
| Line overrides off-catalog | Refuse |
| Dual mint (aliquot+pool one entry) | Bounce |
| Mid-flight method change | Refuse / cancel path — no silent reshape |
| Seeds Blood×aliquot→DNA; DNA×pool→pooled DNA | OK |
| Catalog mutate without config:edit | 403 |

## 9. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — A + line override lock |
| Architecture | **Accept** (Heidi re-read 2026-08-23 on A + line override) — one op per entry; line clear/override; mid-flight method = cancel; bounce dual mint / silent reshape. Pending: concrete method fold with Deiter cut list |
| UI | **Accept** (Mathilda re-read 2026-08-23 on A + line override) |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN.** Not IC50.

## 10. Relationship to Hold

Lifts Extract-then-Qubit Hold once implemented. Not SOP+AI → live process (PR 51).
