# Idea: List page search & filters (all DataGrids)

**Status:** **In progress** — chips on Samples + Experiments (2026-08-13); full bar rollout pending  
**Date:** 2026-08-12 · **Updated:** 2026-08-13  
**Related:** Samples, Experiments, Processes, Clients, Projects, admin catalogs; [system-managed-status.md](system-managed-status.md); Decision #24 (Available for Testing)

## One-liner

A **shared filter pattern** for every list page: free-text search + structured filters (status chips, project, type, …), reusable across Samples and all management grids.

## Immediate need (addressed first)

**Samples ready for testing:** status chips on `/samples` including **Available for Testing** (server `?status=`).  
**Experiments:** status chips + My experiments chip (aligned UI).

---

## Recommended stack (locked direction)

| Layer | Choice | Why |
|-------|--------|-----|
| **UX shell** | **Toolbar filter bar** + **chips** for high-frequency values (status, Mine) | Familiar; works on every page; chips for speed |
| **State** | **URL query params** where the list is primary (`?status=`, `?mine=`) | Shareable, back button, deep links |
| **Data** | **Server filters** for status/project/mine; **client** text search until `q=` exists | Correct totals with pagination; text can start client-side |
| **Grid extras** | Optional MUI column filters **later** | Power users only; not the main chrome |
| **Saved views** | **Later** | After bar + chips are consistent |

**Locked stack summary:** **A** (toolbar) + **C** (chips) + **D** (URL) + **E** (server for structured filters). **B** and **F** deferred.

### Not chosen as sole path

| Option | Verdict |
|--------|---------|
| DataGrid-only column filters | Inconsistent; weak for FK lists without valueOptions |
| Separate “ready samples” page | Prefer one list + chip |
| Client-only status filter for Samples | Wrong once API paginates / incomplete page load |

---

## Options catalog (reference)

| Option | What | Role in stack |
|--------|------|----------------|
| **A. Toolbar filter bar** | Search + selects above grid | Baseline shell |
| **B. DataGrid column filters** | Built-in operators | Optional later |
| **C. Preset / status chips** | One-click filters | **Shipped pattern** (`ListFilterChips`) |
| **D. URL-synced filters** | `?status=&mine=` | **Samples + Experiments** |
| **E. Client vs server** | Loaded rows vs API | Status/mine = server; name search = client until `q=` |
| **F. Saved views** | Named filter sets | Deferred |

---

## Implementation status

| Piece | Status |
|-------|--------|
| Shared component `ListFilterChips` | **Done** — `frontend/src/components/common/ListFilterChips.tsx` |
| Samples: status chips → `?status=<uuid>` → `GET /samples?status=` | **Done** |
| Experiments: status chips → `?status=` + My experiments `?mine=true` | **Done** (server filters; name search client) |
| Experiments: template still Select (not chips) | Intentional — many templates |
| Processes / Clients / Projects / admin | **Todo** |
| Server `q=` free-text | **Todo** |
| Full `ListPageFilters` (text + selects wrapper) | **Todo** |

### Samples chips

- **All** + each `sample_status` list entry (e.g. Received, **Available for Testing**, Testing Complete, …)
- Click sets/clears `status` query param and reloads from API

### Experiments chips

- **All** + each `experiment_status` entry (`?status=<uuid>` → `status_id` on API)  
- **My experiments** toggle chip (`?mine=true`)  
- Name search + template dropdown remain in the toolbar row  

---

## Rollout order (remaining)

1. ~~Samples status chips~~  
2. ~~Experiments status + mine chips~~  
3. Processes (status / mine)  
4. Clients, Projects  
5. Admin catalogs  
6. Server `q=` where lists are large  

---

## Non-goals

- Full BI query builder  
- Replacing RBAC / RLS with filters  
- Per-user saved views in first slices  

## Suggested process

Continue rolling **ListFilterChips** (+ URL) page by page → then shared text search bar → docs sync manuals.
