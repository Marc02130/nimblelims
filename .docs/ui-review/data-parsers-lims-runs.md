# UI / UX Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Resubmitted for review** (tech sketch ready)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Mental model users must learn

| Concept | User language | When |
|---------|---------------|------|
| **Analysis** | What assay / panel | Reportable results on publish |
| **Instrument / CRO** | Where the file came from | Lineage + which parser family |
| **Parser** | How we read this file format | Import only |
| **Examples vs tests** | Teach the format vs prove the format | Parser setup |
| **Template** | Protocol / lifecycle / worklist | Run setup (unchanged) |

**Risk:** “Parser” vs “template” vs “analysis” confusion—UI must keep labels distinct.

## Primary flows

### A. Setup (admin / lab manager) — once

1. Instruments list — create “LCMS-1”  
2. CRO sources list — create “Eurofins metals”  
3. Parsers — create for Analysis=Metals + Instrument=LCMS-1; edit column map  
4. **Upload example file(s)** (1+) and **test file(s)** (1+); **Run tests** → pass/fail panel  
5. (P2) “Draft config from examples” + “Suggest edge tests” → accept → re-run tests → **Activate** / save  

### A2. Parser test panel (required UX)

- Lists each test file: status, rows parsed, warnings, errors  
- “Add edge test” (manual) / “Suggest edges” (AI, P2)  
- **Activate** disabled until gate met (show why)  

### B. Run (lab tech) — every time

1. Create/open LimsRun (template as today)  
2. Overview: set **Analysis**, set **Instrument** *or* **CRO**  
3. **Parser** fills to default; chip “Default” / **Change** (override stored)  
4. Import file → preview → commit (no AI)  
5. Publish → existing promotion preview  

### C. Troubleshooting

- Run detail shows instrument/CRO + parser name  
- Link to parser definition if user can view config  

## UI principles

1. **Default then override** — don’t force parser pick when one default exists.  
2. **Stored choice visible** — never silently re-pick parser after override.  
3. **Import errors plain language** — missing columns, bad delimiter.  
4. **Examples vs tests** labeled clearly; encourage independent test file.  
5. **AI is setup-only**, never on Import button.  
6. **Fill-height tables** for admin lists (project standard).  
7. Empty states: “No parser for this analysis + instrument — create one.”  

## Surfaces (from tech sketch)

| Surface | Content |
|---------|---------|
| Admin: Instruments | CRUD grid |
| Admin: CRO sources | CRUD grid |
| Admin: Parsers | List + editor + multi-file test panel |
| LimsRun Overview | Analysis, Instrument/CRO, Parser (default/override) |
| LimsRun Import | Upload bound to `run.parser_id` |

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
