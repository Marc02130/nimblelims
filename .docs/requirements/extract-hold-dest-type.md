# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** — two predefined entries; `dest_sample_type` on plan line  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest `sample_type` chosen on the **aliquot/pool plan entry** before execute; daughters appear on the **dest sample entry** after execute. Catalog + L1 join + start allow-list. No new plan object.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Two entries, no plan object: (1) plan = Method + dest type; (2) dest sample entry = after-execute daughters only | Marc Leadership 2026-08-23 |
| Plan = `predefined_entry_key=aliquot_pool_plan` (`experiment_data`); dest list = `aliquots_pools` (`experiment_sample_data`) | Heidi Architecture map |
| **Bounce:** today no `dest_sample_type` on plan lines; execute copies parent — field must land on `AliquotPlanLine` / plan config | Heidi |
| Clear = Same as parent; catalog limits; template pre-fill OK; Method drives aliquot vs pool | Marc + Mathilda |
| Seeds Blood×aliquot→DNA and DNA×pool→pooled DNA; S3 config:edit; L1; start allow-list | Prior implement order |
| No Sample/`material_class`; no matrix drop; no receive/mid-entry gate; no if-blood-then; no transitions on `template_definition` | Heidi bounce |
| Not IC50 | Marc |

## 3. Goals

- `dest_sample_type` on each plan line beside Method (`aliquot_pool_plan` only).
- `aliquots_pools` lists minted dests after execute — no method/type picker.
- Execute reads plan → mints → L1 join → dest entry lists them; no re-prompt.
- Catalog many-to-many; pool same-type; S3; both seeds.

## 4. Non-goals

No new experiment-plan object; no method/type on `aliquots_pools`; no Sample/`material_class`; no matrix drop; no if-blood-then; no IC50.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Plan entry key `aliquot_pool_plan`; dest sample entry key `aliquots_pools`. |
| AC2 | `AliquotPlanLine` (or plan config) has optional `dest_sample_type` beside Method. |
| AC3 | Blank/clear = Same as parent; catalog limits select; template pre-fill OK. |
| AC4 | Execute does not re-prompt type; does not copy parent blindly when dest type is set. |
| AC5 | `aliquots_pools` shows minted daughters after execute only — no method/type controls. |
| AC6 | L1/S1 join; pool same-type refuse; off-table refuse. |
| AC7 | Seed Blood×aliquot→DNA and DNA×pool→pooled DNA. |
| AC8 | Catalog mutate = `config:edit` only (S3). |
| AC9 | No new experiment-plan object. |
| AC10 | Start `accepted_sample_types`; C2 key off `sample_type`. |

## 6. Path exercised

Plan on `aliquot_pool_plan` (Blood→DNA) → execute → daughters on `aliquots_pools` → optional pool plan (DNA→pooled DNA).

## 7. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — two-entry lock |
| Architecture | **Accept** + map + bounce |
| UI | **Accept** — locked to Heidi map |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN.** Not IC50.
