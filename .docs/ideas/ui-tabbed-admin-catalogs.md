# Idea: UI cleanup — tabbed catalog pages (group by domain, not by sprint)

**Status:** Placeholder — **UI/nav cleanup**; independent of data-parsers P1 schema  
**Date:** 2026-07-20  
**Related:** Admin Instruments UI (P0), Lab Mgmt Analyses/Analytes, Test Batteries; [data-parsers](../schema-changes/data-parsers-lims-runs.md)

## One-liner

Use **in-page tabs** to group **related** catalog entities on one screen (and one sidebar entry). Do **not** group entities only because they shipped in the same phase. Split unrelated catalogs into their own pages/nav items.

## Motivation (from P0 feedback)

| Feedback | Implication |
|----------|-------------|
| Instrument **types** + **instruments** as tabs works well | Keep that pattern for type→instance (or parent→child catalogs) |
| **CRO sources** should **not** share a tab strip with instruments | Only co-located for P0 implementation timing — not a domain relationship |
| Apply the same idea to assay setup | Analyses / analytes / test batteries are one mental model |
| Lab Mgmt also has analyses + analytes | Same tab pattern, appropriate permissions |

## Principle

**Tabs = domain kinship.**  
**Separate page/nav = different domain or different audience.**

| Group if… | Split if… |
|-----------|-----------|
| Users think of them as one setup area | Only related by “we built both last week” |
| Frequent cross-reference while editing | Different permissions or different personas long-term |
| Parent/child or tightly coupled catalogs | Import lineage siblings that are not hierarchical |

## Target information architecture

### Admin (`config:edit` unless noted)

| Sidebar label (one item) | Tabs | Notes |
|--------------------------|------|--------|
| **Instruments** | Instrument **types** · **Instruments** (instances) | Drop CRO from this page |
| **CRO sources** | _(single page, no forced tabs)_ | Own nav item; same CRUD as today |
| **Assay setup** (name TBD) | **Analyses** · **Analytes** · **Test batteries** | Replaces three separate Admin links |
| Lists, Units, Container types, Users, … | Unchanged unless later cleanup | Out of scope for this idea |

Suggested route shapes (implementation detail):

```
/admin/instruments          ?tab=types | instances   (or nested paths)
/admin/cro-sources
/admin/assays               ?tab=analyses | analytes | batteries
# keep deep links working:
/admin/analyses             → redirect → /admin/assays?tab=analyses
/admin/analytes             → redirect → /admin/assays?tab=analytes
/admin/test-batteries       → redirect → /admin/assays?tab=batteries
```

Nested routes that already exist (e.g. `/admin/analyses/:id/analytes` for analysis↔analyte link) **stay**; tabs only consolidate the **list/management** entry points.

### Lab Management (`analysis:manage` etc.)

| Sidebar label (one item) | Tabs | Notes |
|--------------------------|------|--------|
| **Analyses** (or **Assays**) | **Analyses** · **Analytes** | Replaces two Lab Mgmt links |
| Projects, Clients, Client projects | Unchanged | Different domain |

```
/assays                     ?tab=analyses | analytes
/analyses                   → redirect → /assays?tab=analyses
/analytes                   → redirect → /assays?tab=analytes
```

Lab Mgmt pages may remain **lighter** than Admin (if Admin has extra configure tools); tabs still share one shell so navigation matches.

## Explicit non-goals

- Merging **data models** or APIs (still separate endpoints).  
- Putting **Data parsers** on the Instruments page (parsers are their own P1 surface).  
- Combining CRO with instruments “for sidebar density.”  
- Global redesign of Admin Overview cards (optional follow-on: cards point at new routes).  
- Changing RBAC semantics (only how items appear when the user has permission).

## CRO vs instruments (lock)

```
Admin
  ├── Instruments          tabs: Types | Instances
  ├── CRO sources          standalone page
  └── … (assay setup tabs later)
```

**Why separate:** CRO is an external **export origin**, not a vendor/model/instance of lab equipment. Shared use later is only as **parser source XOR** (instrument | CRO)—that belongs on the **Data parsers** UI, not on the instrument catalog.

## Assay grouping rationale

| Entity | Role in one mental model |
|--------|---------------------------|
| **Analysis** | Assay / panel offered by the lab |
| **Analyte** | Measurand catalog |
| **Test battery** | Ordered/optional set of analyses for ordering |

Users configuring “what we can test” jump among these three often → **one Admin entry, three tabs**.

Lab Mgmt users who **view/manage** analyses and analytes (not always batteries) get **two tabs**. Batteries can stay Admin-only if product prefers (confirm when implementing).

## UX rules for tabbed shells

1. **One primary create button** that matches the **active tab**.  
2. **URL reflects tab** so refresh/share/bookmark work.  
3. **Old routes redirect** so bookmarks and docs don’t break.  
4. **Permission gate** on the shell: show only tabs the user can use; if only one tab remains, still use the shell for consistency (or collapse to single view).  
5. **Don’t force-load all tabs’ data** on first paint if lists are heavy—load on tab focus.  
6. **Empty states** stay tab-specific.  
7. Keep **fill-height DataGrid** pattern per tab.

## Implementation sketch (when scheduled)

| Step | Work |
|------|------|
| 1 | Split P0 page: Instruments (types + instances tabs only); new **CRO sources** page + nav |
| 2 | Admin assay shell: mount existing Analyses / Analytes / Test Batteries list UIs as tab panels |
| 3 | Lab Mgmt shell: Analyses + Analytes tabs |
| 4 | Redirects from old paths; update MainNav, Sidebar, AdminDashboard cards, MainLayout titles |
| 5 | Light regression: permissions, deep links, create dialogs |

No backend/schema required for this idea.

## Open questions

| # | Question | Lean |
|---|----------|------|
| 1 | Admin shell title: “Assay setup” vs “Analyses” vs “Test catalog”? | **Assay setup** or **Analyses & batteries** |
| 2 | Include **Test batteries** on Lab Mgmt or Admin only? | **Admin only** unless lab techs need it |
| 3 | Tab state: query `?tab=` vs path segments `/admin/instruments/types`? | **`?tab=`** or path segments—pick one project-wide |
| 4 | Admin vs Lab Mgmt analyses UI: share one component with mode prop? | **Yes** if possible (DRY) |
| 5 | Admin Overview: one card per shell or per tab? | **One card per shell** |
| 6 | Immediately split CRO from instruments in a small PR? | **Yes** — cheap, matches product feedback |

## Success criteria

1. Sidebar has **fewer** redundant peer links for the same domain.  
2. Instruments page tabs = **types + instances only**; CRO has its **own** entry.  
3. Admin assay entities reachable from **one** nav item with clear tabs.  
4. Lab Mgmt analyses + analytes use the **same tab pattern**.  
5. Old URLs still work via redirect.  
6. No regression in `config:edit` / `analysis:manage` access.

## Out of scope links

- Data parsers admin UI (P1) — separate page when built  
- [orders-and-projects](orders-and-projects.md) nav (future rename)  
- [lab-locations](lab-locations.md)  
