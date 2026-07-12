# UI / UX Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Awaiting review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Mental model users must learn

| Concept | User language | When |
|---------|---------------|------|
| **Analysis** | What assay / panel | Reportable results on publish |
| **Instrument / CRO** | Where the file came from | Lineage + which parser family |
| **Parser** | How we read this file format | Import only |
| **Template** | Protocol / lifecycle / worklist | Run setup (unchanged) |

**Risk:** “Parser” vs “template” vs “analysis” confusion—UI must keep labels distinct.

## Primary flows (for review)

### A. Setup (admin / lab manager) — once

1. Instruments list — create “LCMS-1”  
2. CRO sources list — create “Eurofins metals”  
3. Parsers — create for Analysis=Metals + Instrument=LCMS-1; edit column map  
4. (Later) “Draft from sample file” → review → save  

### B. Run (lab tech) — every time

1. Create/open LimsRun (template as today)  
2. Overview: set **Analysis**, set **Instrument** *or* **CRO**  
3. **Parser** fills to default; show chip “Default” / allow **Change** (override stored)  
4. Import file → preview → commit  
5. Publish → existing promotion preview  

### C. Troubleshooting

- Run detail shows instrument/CRO + parser name/id used  
- Link to parser definition (if user can view config)

## UI principles

1. **Default then override** — don’t force parser pick when one default exists.  
2. **Stored choice visible** — never silently re-pick parser after override.  
3. **Import errors plain language** — missing columns, bad delimiter.  
4. **AI is a setup wizard**, labeled optional; never on Import button.  
5. **Fill-height tables** for admin lists (project standard).  
6. Empty states: “No parser for this analysis + instrument — create one.”

## Surfaces (proposed)

| Surface | Content |
|---------|---------|
| Admin: Instruments | CRUD grid |
| Admin: CRO sources | CRUD grid |
| Admin: Parsers (or under Analysis) | List + editor for parser_config |
| LimsRun Overview | Analysis, Instrument/CRO, Parser (default/override) |
| LimsRun Data / Import | File upload bound to run.parser_id |

## Wireframe notes (optional)

_Add mock links or sketches during review._

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ |
| **Must-fix before build** | |
| **Nice-to-have** | |
| **Reviewer** | |
| **Date completed** | |

## Notes

_Add UX findings during review._
