# Decision log: Atomic receive CORE closed

**Date:** 2026-08-27  
**Status:** Decided  
**Stem:** `atomic-receive`

## Decision

Atomic receive **CORE is closed**: implemented, dogfooded, full browse+API UAT **Pass**, merged to `main` (`ebac94e` feature; UAT stamp `618fbbf`).

## Close-out fixes (same day)

- `SampleBase.client_sample_id` so GET/list responses retain the field.
- `require_project_for_receive`: inaccessible/RLS-hidden project → **403** (not 404).
- Manual + sketch + UAT concerns updated; PR **#73** superseded (close without merge). PR **#71** already closed after main merge.

## What is next (accessioning)

1. **NR-AR-1 / results-entry slice** (recommended next packet) — persist lock only; separate requirements + Leadership reviews.  
2. **A-15 asked-for / work-plan** — remains parked until product unlocks.  
3. **Work orders / WO-*** — processing domain after receive (+ results).  

Do **not** reopen CORE receive scope (no analysis picker, no Test mint at receive, no aliquot UI, no IC50).
