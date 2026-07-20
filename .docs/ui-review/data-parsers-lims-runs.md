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
| **Version / Active** | Saved definition of a parser; only the active version is used for new imports | Edit creates new version; prompt to activate |
| **Examples vs tests** | Teach the format vs prove the format | Parser setup |
| **Template** | Protocol / lifecycle / worklist | Run setup (unchanged) |

**Risk:** “Parser” vs “template” vs “analysis” confusion—UI must keep labels distinct.

## Primary flows

### A. Setup (admin / lab manager) — once

1. Instrument **types** — e.g. vendor Agilent, model 6495C  
2. Instrument **instances** — e.g. name LCMS-1, type above, serial optional (no location yet)  
3. CRO sources list — create “Eurofins metals”  
4. Parsers — create for Instrument **instance** ICP-1; multi-select **analyses** (e.g. RCRA-8 + RCRA-13); map all metal columns  

5. **Upload example file(s)** (1+) and **test file(s)** (1+); **Run tests** → pass/fail panel  
6. **Save** creates a **new version** (never overwrites an existing version’s config)  
7. Dialog: **“Make this version active?”** — Yes → deactivate previous active; No → leave as draft version  
8. (P2) “Draft config from examples” + “Suggest edge tests” → accept → re-run tests → save / activate  

### A2. Parser test panel (required UX)

- Lists each test file: status, rows parsed, warnings, errors  
- “Add edge test” (manual) / “Suggest edges” (AI, P2)  
- Version list / history on the logical parser; badge **Active** on current production version  
- **Activate** after save (prompt); ideally disabled until test gate met (show why)

### B. Run (lab tech) — every time

1. Create/open LimsRun (template as today)  
2. Overview: set **Analysis** (run is tied to this assay)  
3. **Import:** pick **Instrument** *or* **CRO** (only those with a parser for this analysis)  
4. **Parser** defaults to **active** version for (analysis, that source); **Change** only among **active** parsers for that pair  
5. File → preview → commit; may repeat with **another** instrument/parser on the same run  
6. Import history: instrument/CRO + parser **name + version** per batch  
7. Publish → existing promotion preview (analysis-scoped)

### C. Troubleshooting

- Run detail shows instrument/CRO + parser name **and version**  
- Link opens **that version’s** definition (immutable history), not necessarily the current active

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
| Admin: Instrument types | CRUD (vendor/model) |
| Admin: Instruments (instances) | CRUD (type, serial, name) |
| Admin: CRO sources | CRUD grid |
| Admin: **Data parsers** | List active; version history; editor; multi-file tests; **activate prompt** on save |
| LimsRun Overview | Analysis, Instrument/CRO, Parser (name + version) |
| LimsRun Import | Upload bound to stored **version** `parser_id` on import event |

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
