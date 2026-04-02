# QA Report — NimbleLIMS dose-response branch
**Date:** 2026-04-02  
**Branch:** dose-response  
**Tester:** /qa skill (Claude Sonnet 4.6)  
**URL:** http://localhost:3000  
**Duration:** ~25 minutes  
**Mode:** Diff-aware (feature branch)  

---

## Summary

| Metric | Value |
|--------|-------|
| Issues found | 2 |
| Fixed (verified) | 2 |
| Deferred | 0 |
| Health score (baseline) | 55/100 |
| Health score (final) | 85/100 |

**PR Summary:** QA found 2 issues, fixed 2, health score 55 → 85.

---

## Issues Found & Fixed

### ISSUE-001 — 500 on Dose Response summary endpoint [CRITICAL] ✅ FIXED

**File:** `backend/models/flexible_experiment.py`  
**Commit:** `5339eac`

**Description:** Every request to `GET /v1/experiment-runs/{id}/dose-response/summary` returned 500 Internal Server Error.

**Root cause:** Migration `0043_dose_response_tables.py` added `fit_in_progress BOOLEAN` column to `experiment_runs` table, but the SQLAlchemy `ExperimentRun` ORM model in `models/flexible_experiment.py` was never updated. `dose_response.py:314` accessed `run.fit_in_progress`, raising `AttributeError: 'ExperimentRun' object has no attribute 'fit_in_progress'`.

**Fix:** Added `fit_in_progress = Column(Boolean, nullable=False, server_default='false', default=False)` to `ExperimentRun` model and imported `Boolean` from sqlalchemy. Rebuilt and redeployed backend container.

**Before:** Dose Response tab showed error alert, 500 in console  
**After:** Tab loads cleanly, shows correct "No curves yet" empty state

---

### ISSUE-002 — Mobile tab truncation on ExperimentRunDetail [MEDIUM] ✅ FIXED

**File:** `frontend/src/pages/ExperimentRunDetail.tsx:190`  
**Commit:** `a7f1336`

**Description:** On 375px mobile viewport, the 3-tab row (Overview / Data / Dose Response) overflowed the container. "Overview" rendered as just "W" — completely illegible.

**Root cause:** Default MUI `Tabs` uses `variant="standard"` which compresses tab widths to fit the container, truncating labels. With 3 tabs at 375px, "Overview" got compressed to 1 character.

**Fix:** Added `variant="scrollable" scrollButtons="auto"` to the `<Tabs>` component. Now tabs render at their natural width and the row is horizontally scrollable.

**Before:** "W | DATA | DOSE RE" on mobile  
**After:** "OVERVIEW | DATA | DOSE RE..." (scrollable, all legible)

---

## Pages Tested

| Page | Status | Notes |
|------|--------|-------|
| Login | ✅ | Works correctly |
| Dashboard | ✅ | Loads, shows sample stats |
| Runs List (`/runs`) | ✅ | New page, shows runs with status badges |
| Run Detail — Overview tab | ✅ | Shows status, template ID, timestamps |
| Run Detail — Data tab | ✅ | Shows empty state correctly |
| Run Detail — Dose Response tab | ✅ (after fix) | Loads summary, shows Fit Curves button |
| Fit Curves (no data) | ✅ | Correctly returns 422 with "No data found" message |
| Experiment Templates | ✅ | List and edit work |
| All Experiments | ✅ | List loads, existing experiments visible |
| Samples Management | ✅ | No regression |
| Admin / Name Templates | ✅ | No regression |

---

## Health Score Breakdown

### Baseline (before fixes)
| Category | Score | Notes |
|----------|-------|-------|
| Console | 40 | 500 error on dose-response tab |
| Functional | 40 | Core new feature broken (500) |
| UX | 60 | Mobile tab truncation |
| Visual | 90 | Clean UI |
| Accessibility | 85 | Good semantic markup |
| Content | 90 | Clear error messages |
| Performance | 90 | Fast loads |
| Links | 100 | No broken links |

**Baseline: ~55/100**

### Final (after fixes)
| Category | Score | Notes |
|----------|-------|-------|
| Console | 100 | No new errors |
| Functional | 90 | Dose response loads; full flow needs test data |
| UX | 90 | Scrollable tabs on mobile |
| Visual | 90 | Clean |
| Accessibility | 85 | Good |
| Content | 90 | Clear messaging |
| Performance | 90 | Fast |
| Links | 100 | None broken |

**Final: ~85/100**

---

## Deferred / Out of Scope

- **Full dose-response curve fitting flow**: Requires test data (samples with qc_type, template well definitions with concentrations). The backend service and R calculator are set up but untested end-to-end with real data. This is expected at this stage — the feature is new.
- **Template ID vs Template Name in run Overview**: The Overview tab shows raw UUID for "Template ID". Low priority, pre-existing.

