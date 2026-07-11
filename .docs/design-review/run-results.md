# Design Review: LimsRun → Results (structured promotion)

**Date:** 2026-07-11  
**Branch:** `run-results`  
**Reviewer:** Design / UX  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)

## Executive Summary

Users should understand two stages:

1. **Import** — flexible table on the run (instrument/CRO).  
2. **Publish** — that table becomes **official structured results** (per sample/test/analyte).

Publish is already a high-intent action. Bundling structure creation there reduces a separate “Promote” concept for v1, as long as **preview and errors** are excellent.

**Strengths:** Clear mental model; reuses Results UI for reporting; multi-analyte = multi-row is natural.  
**Risks:** Surprise result creation on publish; silent mapping failures; no visibility into aliases.

## User jobs

| Persona | Job | Success |
|---------|-----|---------|
| Lab tech / analyst | Import file, finish run, publish | Results appear under samples/tests without retyping |
| Lab manager | Configure assay once | Template map + analyte aliases work for next CRO file |
| Lab client | View results (later portal) | Sees structured results for their projects only—not JSONB |

## Principles

1. **Publish writes structure** — results created/updated when run becomes `published`.  
2. **Preview before commit** — show “N results will be created/updated” on the publish confirmation.  
3. **Mapping is setup, not improvisation** — defaults from template; advanced override only if needed.  
4. **Failures are visible** — unmapped columns listed; missing tests block with actionable links.  
5. **Raw is the v1 target** — don’t invent calculated UX yet.  
6. **Aliases are user-facing** — manage on Analyte; show “matched via alias Pb → Lead”.

## Primary flows

### A. Assay setup (once)

1. Analytes catalog + **aliases** (CRO/instrument names).  
2. Experiment template: **Result promotion map**  
   - Which JSONB keys participate (or “auto by analyte/alias”)  
   - Optional explicit key → analyte  
3. Custom fields on results if extra meta is required (already in Field Management).

### B. Run execution

1. Draft → … → import data (`running` / `results_received`).  
2. Complete run.  
3. **Publish**  
   - Modal: summary of promotion plan  
   - Errors: block publish until fixed (or allow “publish without promote” only if product allows—default **no** if map configured)  
4. Results appear on sample/test; run remains source of instrument data.

### C. After publish

- Results list/detail show lineage: “From run *X*” (link).  
- Re-publish policy (product): update vs locked—surface clearly in UI.

## UI surfaces

| Surface | Content |
|---------|---------|
| Run detail → Publish | Preview table: sample, analyte, raw value, match method (name/alias/map) |
| Template settings | Promotion map section next to parser config |
| Analyte form | Aliases multi-value field |
| Results | Unchanged entry UX; badge “imported from run” |

## Empty / error states

| State | UX |
|-------|-----|
| No sample_id on rows | Block; link to fix import/mapping |
| No tests on sample | Block with “add tests” CTA |
| Column unmatched | List skipped columns; optional force map |
| Alias conflict | Two analytes claim same alias—admin error |
| Zero rows to promote | Warn; allow publish-only if intentional |

## Anti-patterns

| Reject | Why |
|--------|-----|
| Promote on every import | Draft pollution |
| Hide mapping failures | Silent bad data |
| Dump unmapped keys to custom_attributes | Opaque reporting |
| Client-user publish/promote | Lab data integrity |

## Success metrics

- Preview accuracy vs post-publish result count  
- % publishes blocked by setup (should fall as templates mature)  
- Alias usage rate  
- Manual result edits after promote (high = bad maps)

## Design recommendations

1. **Publish confirmation = promotion preview** for templates with a map.  
2. **First-class analyte aliases** in Analyte admin.  
3. **Lineage chip** on results back to run.  
4. Keep dose-response UX separate—don’t mix IC50 tables into this flow.  

**Design score: 8/10** if preview + aliases are solid; **5/10** if publish silently creates wrong rows.

---

Related: [ceo](../ceo-review/run-results.md) · [tech](../design/run-results.md) · [security](../security-review/run-results.md)
