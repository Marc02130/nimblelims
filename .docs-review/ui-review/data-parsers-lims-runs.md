# UI / UX Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19  
**Verdict date:** 2026-07-19  
**Status:** **Accepted with conditions**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Schema:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Must-fix before build** | **None blocking design** — U1–U4 are implementation requirements, not redesigns |
| **Nice-to-have** | U5–U7 |
| **Reviewer** | UI / UX |
| **Date completed** | 2026-07-19 |

## Mental model (accepted)

| Concept | User language | Risk if confused |
|---------|---------------|------------------|
| Analysis | Assay on the run | Required — never optional empty |
| Instrument type vs instance | Kind of box vs this unit | Import lists **instances** |
| CRO source | External export | XOR with instrument |
| Data parser | How file is read | Not “template” |
| Version / Active | Definition history / production | Activate prompt is critical |

## Flows (accepted)

- Setup: type → instance → CRO → data parser (M2M analyses) → examples/tests → save version → activate if all clean  
- Run: analysis required → import instrument\|CRO → active parser default/override → multi-import history with version  
- Caps: 10 files / 10 MB with clear messaging  

## Implementation requirements (conditions)

| # | Condition |
|---|-----------|
| U1 | **Copy:** nav and page title **“Data parsers”** (not instrument parsers). |
| U2 | **Activate:** button/dialog disabled until **all** test/edge files hard-error-free; list failing files by name. |
| U3 | **Run create/edit:** analysis **required** control; remove “None / non-reportable” option (align with product lock). |
| U4 | **Import:** instrument XOR CRO control; parser picker filtered to active + linked to run analysis; show **name + version**. |
| U5 | (Nice) Version history panel with Active badge; open historical version read-only from import history. |
| U6 | (Nice) Empty state CTA: “No active data parser for this analysis + instrument — create one.” |
| U7 | (Nice) Upload dropzone shows remaining file count and 10 MB limit. |

## Principles checklist

| Principle | Verdict |
|-----------|---------|
| Default then override among valid only | **OK** |
| Stored version visible | **OK** |
| Plain-language errors | **OK** — implement on import + setup |
| Examples vs tests labeled | **OK** |
| AI never on Import button | **OK** (P2 later) |
| Fill-height admin grids | **OK** — project standard |

## Notes

Flows match product locks. Primary UX risk is concept overload (type/instance/parser/version/analysis); keep labels consistent and separate admin setup from run import. No wireframe blockers — proceed to build with U1–U4.
