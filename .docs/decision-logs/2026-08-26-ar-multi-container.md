# Atomic receive: 1..N containers

**Date:** 2026-08-26  
**Status:** **Decided**  
**Domain:** Sample accessioning (OOB AR profile)

## Decision

Atomic receive is **not** limited to one container. One sample may be received with **one or more** containers in the **same transaction**.

| Rule | Detail |
|------|--------|
| UX | **Primary barcode** required + **optional additional barcodes** |
| Data | Each barcode → Container + Contents → same Sample |
| Type | Default tube off-form for all vessels on the call |
| Uniqueness | Any barcode collision → **409**, full rollback |
| Later aliquot | Still distinct (process mint of dest vessel) — not a substitute for multi-tube receive |

Updated: `.docs/internal/prd/sample-accessioning/PRD.md` · SPEC · ISSUES · `.docs/review/tech-sketch/atomic-receive.md` · containers ISSUES **C-16**.
