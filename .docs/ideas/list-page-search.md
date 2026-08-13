# Idea: Search on list pages

**Status:** Placeholder — not implemented  
**Date:** 2026-08-12  
**Related:** Samples Management, Experiments, Processes, Clients, Projects, admin DataGrids; [ui-tabbed-admin-catalogs.md](ui-tabbed-admin-catalogs.md)

## One-liner

Add consistent **text search / filter** across major list pages so users can find rows by name, ID, or key metadata without relying only on column sort or URL query params.

## Why

- Labs accumulate many samples, experiments, processes, and config rows.
- Today most list pages load a page of rows with little or no global search (some support URL filters like `?project_id=` only).
- Users expect a search box (and optionally filters) on every primary list, similar to industry LIMS/ELN UIs.

## Current state (NimbleLIMS)

| Exists | Gap |
|--------|-----|
| DataGrid column sort / client pagination on many pages | No shared search field pattern |
| Samples: optional URL filters (`project_id`, `status`, `custom.*`) | No free-text search box on `/samples` |
| Some admin pages have local filter text | Inconsistent; not applied to all list pages |

## Direction (when prioritized)

1. **UX pattern (shared)**  
   - Search field above each primary DataGrid (name / ID / common fields).  
   - Optional: filter chips (status, project, type).  
   - Debounced input; clear button; preserve selection when filtering if feasible.

2. **Implementation options**  
   - **Client-side filter** on already-loaded rows — fine for small pages / current page-size.  
   - **Server-side** `?q=` or field filters — needed when lists are large or paginated from API.  
   Prefer server-side for Samples / Experiments / Processes once volume grows.

3. **Pages in scope (suggested order)**  
   - Samples (`/samples`)  
   - Experiments (`/experiments`)  
   - Processes (`/experiments/processes`)  
   - Clients, Projects, admin catalogs (analyses, instruments, data parsers, field management)

4. **API**  
   - Extend list endpoints with `q` (ilike on name / client_sample_id / description) and document in manuals.  
   - Keep existing structured filters (`status`, `project_id`, …).

## Non-goals (this idea)

- Full advanced query builder / saved searches (later).  
- Replacing DataGrid column filters entirely.

## Open when prioritized

- Client-only vs server `q=` for each page.  
- Search across related names (e.g. sample shows project name — join vs denormalized display).  
- Accessibility and mobile layout of the shared search bar.

## Suggested process

Ideation (this doc) → small requirements slice → implement Samples first as template → roll out to other list pages → docs sync.
