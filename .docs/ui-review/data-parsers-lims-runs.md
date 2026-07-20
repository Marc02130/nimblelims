# UI / UX Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19  
**Status:** **Resubmitted for UI review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Schema:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)

## Ask of UI review

Confirm flows and copy are acceptable for **P0+P1** build. Focus areas below reflect **product locks since first draft**.

## Mental model users must learn

| Concept | User language | When |
|---------|---------------|------|
| **Analysis** | What assay / panel | **Required on every run** from create |
| **Instrument type / instance** | What kind of box / which unit | Catalog setup; import picks **instance** |
| **CRO source** | External lab export source | Import alternative to instrument |
| **Data parser** | How we read this file format | Setup + import (not “instrument parser” only) |
| **Version / Active** | Saved definition; only active used for new imports | Edit → new version; activate prompt |
| **Examples vs tests** | Teach format vs prove format | Parser setup (max 10 files, 10 MB each) |
| **Template** | Protocol / lifecycle / worklist | Run setup (unchanged; **not** parser scope) |

**Risks:** parser vs template vs analysis; “version” vs “active”; CRO vs instrument pickers.

## Primary flows

### A. Setup (admin / lab manager) — once

1. **Instrument types** — vendor, model  
2. **Instrument instances** — name, type, serial optional  
3. **CRO sources**  
4. **Data parsers** — instrument **or** CRO; multi-select **analyses** (e.g. RCRA-8 + RCRA-13); map columns (may include all metals)  
5. Upload **example** (1+) and **test** (1+) files — **max 10 files, 10 MB each**  
6. **Run tests** → per-file pass/fail (hard errors vs warnings)  
7. **Save** → **new version** (never overwrite prior version config)  
8. Dialog: **“Make this version active?”**  
   - Enabled only if **all** tests/edges are **hard-error-free**  
   - Yes → this version active; previous active deactivated  
   - No → draft version; old active remains for imports  
9. (P2) AI draft config + suggest edges → human accept → re-test → save/activate  

### B. Run (lab tech) — every time

1. Create run with **Analysis required** (no “none / non-reportable”)  
2. **Import:** pick **Instrument** *or* **CRO** (only if an **active** parser links that source to the run’s analysis)  
3. **Parser** defaults to active default for (analysis, source); override only among valid active parsers  
4. File → preview → commit; may **repeat** with another instrument/parser on the same run  
5. Import history: source + parser **name + version**  
6. Publish → promotion preview (always has analysis)

### C. Troubleshooting

- History links open **that version’s** definition (immutable), not only current active  

## UI principles

1. **Default then override** among valid parsers only.  
2. **Stored version visible** — never silent re-resolve.  
3. **Plain-language** import/setup errors.  
4. **Examples vs tests** labeled; caps shown on upload.  
5. **AI setup-only** (P2) — never on Import.  
6. **Fill-height** admin grids.  
7. Empty: “No active data parser for this analysis + instrument — create one.”  
8. Labels: **Data parsers** (not “instrument parsers”).  

## Surfaces

| Surface | Content |
|---------|---------|
| Admin: Instrument types | CRUD |
| Admin: Instruments (instances) | CRUD |
| Admin: CRO sources | CRUD |
| Admin: **Data parsers** | Active list; version history; editor; tests; activate prompt |
| LimsRun Overview | Analysis **required**; last import chips optional |
| LimsRun Import | Multi-import; version lineage |

## Review checklist (UI)

- [ ] Analysis-required run create/edit (no non-reportable empty option)  
- [ ] Version + activate dialog clarity  
- [ ] Activate disabled until all tests clean; show which file failed  
- [ ] 10 file / 10 MB messaging  
- [ ] Multi-select analyses on parser  
- [ ] Import: instrument XOR CRO; filtered parsers  
- [ ] Import history name + version  

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ (Accept / Accept with conditions / Reject) |
| **Must-fix before build** | |
| **Nice-to-have** | |
| **Reviewer** | |
| **Date completed** | |

## Notes

_Resubmitted 2026-07-19 with product locks: data_parsers naming, versioning, analysis required, M2M analyses, 10/10MB, all-clean activate._
