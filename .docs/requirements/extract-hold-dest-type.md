# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** — A + line override locked; Architecture + UI Accept (re-read)  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest type on `aliquot_pool_plan` (entry default + line override); daughters on `aliquots_pools` after execute. One method/op per plan entry. Catalog + L1 + start allow-list.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| **A + line override:** entry config = method + default dest type; lines may clear/override within catalog | Marc 2026-08-23 |
| Method = exactly one op (aliquot OR pool); drives columns + mint | Marc + Heidi |
| **No mid-flight method change** — cancel experiment, not warn/wipe | Marc + Heidi + Mathilda |
| Bounce: dual mint (one entry both ops); silent reshape after lines exist | Marc + Heidi |
| Two keys: `aliquot_pool_plan` / `aliquots_pools`; no new plan object | Prior map |
| `dest_sample_type` must land on plan line/config (Heidi bounce vs main copy-parent) | Heidi |
| Seeds Blood×aliquot→DNA, DNA×pool→pooled DNA; S3; L1; L2; start allow-list | Prior |
| UI Accept on A + line override | Mathilda re-read 2026-08-23 |
| Not IC50 | Marc |

## 3. Goals

- Entry: method (one op) + optional default dest type (template or add-time).
- Lines: optional dest type clear/override if catalog allows.
- Execute resolve: line → entry default → parent; no re-prompt.
- Cancel experiment to change method; never silent reshape.

## 4. Non-goals

Dual mint; mid-flight method warn/wipe; method/type on `aliquots_pools`; new experiment-plan object; Sample/`material_class`; matrix drop; if-blood-then; IC50.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | `aliquot_pool_plan` + `aliquots_pools` only; no new plan object. |
| AC2 | Entry config has method (aliquot\|pool exactly one) + optional default dest type. |
| AC3 | Plan line optional `dest_sample_type` clear/override within catalog. |
| AC4 | Execute resolve line → default → parent; catalog enforce; no re-prompt. |
| AC5 | Mid-flight method change refused — cancel experiment path only (no warn/wipe reshape). |
| AC6 | Dual mint (aliquot+pool one entry) refused / not offered. |
| AC7 | `aliquots_pools` after-execute daughters only — no method/type controls. |
| AC8 | L1/S1 join; pool same-type; S3 config:edit; both seeds. |
| AC9 | Start `accepted_sample_types`; C2 key off `sample_type`. |
| AC10 | No Sample/`material_class` column. |

## 6. Path exercised

Plan entry method=aliquot, default DNA → execute → daughters on `aliquots_pools` → separate plan entry method=pool for DNA→pooled DNA.

## 7. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — A + line override |
| Architecture | **Accept** (PR 58) + agree A + line override |
| UI | **Accept** (Mathilda re-read on A + line override 2026-08-23) |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN.** Not IC50.
