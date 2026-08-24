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

1. **Analysis = opt-in** — selecting an **Analysis** on the run means “this publish will write tests/results.”  
2. **Publish writes structure** — when `analysis_id` set and run becomes `published`.  
3. **Preview before commit** — show “N results will be created/updated” on the publish confirmation.  
4. **Mapping is setup, not improvisation** — analyte aliases + optional column map; analysis defines assay.  
5. **Failures are visible** — unmapped columns listed; missing sample_id / map errors clear.  
6. **Raw is the v1 target** — don’t invent calculated UX yet.  
7. **Aliases are user-facing** — manage on Analyte; show “matched via alias Pb → Lead”.

## Primary flows

### A. Assay setup (once)

1. Analytes catalog + **aliases** (CRO/instrument names).  
2. Analysis defines which analytes belong to the assay.  
3. Optional template default analysis + column map.  
4. Custom fields on results if extra meta is required (Field Management).

### B. Run execution

1. Create/edit run: **select Analysis** (required — no “none / non-reportable”).  
2. **Start run** (`draft` → `running`, or CRO start path): analysis already set; block start if missing (should not happen if create enforces it).  
3. Import data (`running` / `results_received`) — analysis required (parsers scoped to analysis).  
4. Complete run.  
5. **Publish** → modal **preview = what would happen on publish** (creates / updates / conflicts / unresolved columns).  
6. Results appear on sample/test (identified by analyte/sample/replicate—**not** a result “name”); run remains instrument SoT.

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
| Zero rows to promote | Warn; user may still publish after confirm if intentional |
| Missing analysis on run | Block create/start/import/publish; force select analysis (no continue-without) |

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
