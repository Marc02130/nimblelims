# Decision log: Extract-hold dual-map kick-back

**Date:** 2026-08-24  
**Status:** **Open — kick-back** (implement paused for FD dual-map)  
**Domain:** Sample processing (aliquot/pool)  
**Related:** [prd/sample-processing/PRD.md](../prd/sample-processing/PRD.md) · [specs/sample-processing/SPEC.md](../specs/sample-processing/SPEC.md) · `.docs-review/tech-sketch/extract-hold-dest-type.md`

## Stamps from OQ walk (2026-08-23)

| ID | Stamp |
|----|--------|
| OQ-1 | Dest vol/amount/conc on **entry FieldDefinitions** until entry **submitted**; then update Sample (source volume/status + dest info) |
| OQ-2 | **No** entry-level sample-type gate; gate on **experiment / LimsRun** |
| OQ-3 | S3 catalog = API + thin admin UI, `config:edit` |
| OQ-4 | Atomic pair on **template and ad hoc** |
| OQ-5 | **Kick-back** — fields are not Sample fields during capture; live on experiment_data / experiment_sample_data; Sample updates only after the action/submit gate |

## Questions for Heidi + Mathilda (± Lab Ops)

1. Which entry holds working qty values before Sample update — plan (`aliquot_pool_plan`), dest (`aliquots_pools`), or both?  
2. What unlocks Sample/Contents update — execute, plan submit, dest submit, or experiment complete?  
3. Exact write-back map for source (volume/status depleted) and dest (amount/vol/conc)?  
4. Confirm METHOD_CATALOG “attach immediately” = link FD **columns on the entry** only (no Sample touch until gate)?  
5. Rewrite AC12: remove entry `accepted_sample_types` as primary gate?

## Rule

Do **not** treat dual-map FieldDefinition attach as closed for coding until this log is **Decided**.
