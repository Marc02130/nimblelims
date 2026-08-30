# Idea: Rename `projects` → `orders`; add real **projects** for work over time

**Status:** Placeholder — **not in data-parsers P0/P1**  
**Date:** 2026-07-19 · **Updated:** 2026-07-19 (client_projects kept; internal projects separate)  
**Related:** Accessioning / samples / RLS; [client_projects](../user-stories/nimblelims-user.md) (US-25); data-parsers **Decision #6** (no non-reportable runs; method-dev deferred here); [multi-tenant](multi-tenant.md); Lab QC system project

## One-liner

1. Today’s **`projects`** table is really an **order**: a **batch of samples from one environmental sampling event** (or similar discrete submission)—not a long-lived initiative.  
2. **Rename** that concept to **`orders`** (table/API/UI) so language matches the domain.  
3. **Keep `client_projects`** — client-facing program id for **CRO / client reporting** (do not merge away).  
4. Introduce a new **lab `projects`** table for **internal work over time** (method development, scratch, lab campaigns)—**separate** from client_project.

## Three different “project” words (lock this)

| Entity | Audience | Purpose | Example |
|--------|----------|---------|---------|
| **`client_projects`** | **Client / CRO / reports** | Client’s own program or job code that must appear on deliverables | Client’s “River Program 2026” / PO / WBS id they require on reports |
| **`orders`** (today’s `projects`) | Lab ops + client sample wall | One sampling event / submission (batch of samples) | Cooler from Site B, 2026-07-12 |
| **`projects`** (new, lab-internal) | **Lab only** | Track related work over time inside NimbleLIMS | “ICP metals method validation”; internal monitoring workspace |

**Decided for this idea:**

- **`client_projects` is kept.** A CRO (or the lab reporting for a client) needs the **client project id** on the chain for reporting. It is **not** replaced by lab `projects`.  
- **Lab `projects` ≠ `client_projects`.** Method-dev / scratch / internal tracking use lab projects. Client billable identity uses client_projects.  
- An **order** may reference **both**: `client_project_id` (for client/CRO reporting) and optional `project_id` (lab workspace)—independently.

```
                    client_projects          lab projects (NEW)
                    (client/CRO report id)   (internal work over time)
                           │                        │
                           └──────────┬─────────────┘
                                      ▼
                              orders (RENAMED)
                           one sampling event
                                      │
                                      ▼
                                   samples
```

## Why change existing `projects`?

| Today (code name) | Reality in env labs |
|-------------------|---------------------|
| Table: **`projects`** | Discrete **submission / order**: samples from one sampling event, with due dates, client, status, access |
| Samples require `project_id` | Sample belongs to **that order/event**, not a multi-year program |
| `client_projects` exists | **Client/CRO program id** for reporting — **keep**; not the same as lab work tracking |
| UI/docs say “Project” | Users hear “ongoing work”; product behaves like **order / job / submission** |

**Environmental sampling pattern:** field team samples a site on a date → cooler of containers → lab accessions as **one order** → tests/results for that event. Weeks later, another event is **another order**, even for the same **client project**. Lab may also group orders under an internal **project** for ops (optional).

| After rename | Meaning |
|--------------|---------|
| **`orders`** | One sampling event / submission: a batch of samples, due dates, status, client, access grants |
| **`client_projects`** | **Kept.** Client-owned program/job identity for **reporting** (CRO needs this id on deliverables) |
| **`projects`** (new) | Lab-internal container for related work over time (method-dev, scratch, etc.)—**not** the client report id |

## Problem

- **Language debt:** “project” misleads product, support, and new features (method-dev “project” vs sample “project” vs client project id).  
- **No home for lab work over time:** method validation, R&D, training need an **internal** parent—not client_projects and not order-as-project.  
- **Client/CRO reporting** still needs a stable **client project** identity on orders/samples/results.  
- **Method-dev / non-reportable** discussion: use lab projects + draft analyses — **not** “null analysis” and **not** abusing order or client_project.

## Target model (sketch)

```
clients
  └── client_projects (KEEP)            -- client/CRO report identity
        id, client_id, name, …
        -- appears on reports / packages CRO and client expect

  └── projects (NEW, lab-internal)      -- work over time inside the lab
        id, name, description,
        client_id NULL?,                -- optional link if work is client-related; null = pure internal
        kind / type?,                   -- method_dev | scratch | monitoring | …
        status, start_date, end_date?,
        active, custom_attributes, …
        -- NOT a substitute for client_projects

  └── orders (RENAMED from projects)    -- one sampling event / submission
        id, name?, 
        client_id NOT NULL,
        client_project_id NULL → client_projects,  -- KEEP for reporting / CRO
        project_id NULL → projects,                -- optional lab workspace
        start_date, due_date,
        status, custom_attributes, …
        -- access: order_users (renamed from project_users)

samples.order_id NOT NULL → orders      -- renamed from project_id

-- optional later
lims_runs.project_id NULL → projects    -- method-dev runs without samples
```

### Hierarchy (env lab)

| Level | Grain | Example |
|-------|--------|---------|
| **Client** | Customer org | Acme Environmental |
| **Client project** | Client/CRO program id (reporting) | Acme “River Program 2026” / their job code |
| **Lab project** (new) | Internal work over time | “ICP metals method validation” (lab-only) |
| **Order** (today’s project) | One sampling event / submission | “River Site B — 2026-07-12 event”; 24 aqueous samples |
| **Sample** | One specimen | SW-01, 2026-07-12 |
| **Batch** (existing) | Lab processing group | Prep batch across orders when allowed |

**CRO path:** order (and thus samples/results) carry **`client_project_id`** so reports and packages can show the id the client/CRO expects—independent of any lab `project_id`.

### Lab project kinds (illustrative)

| Kind | Typical content | Promote / reportable |
|------|-----------------|----------------------|
| **Method development** | Draft analyses, parser versions, spike samples, lims runs | Import OK; promote gated / off by default |
| **Scratch / training** | Throwaway samples and runs | No promote |
| **Internal monitoring workspace** | Lab-side grouping of related production orders | Promote still driven by analysis/order rules |
| **Internal QC program** | Related to Lab QC system order(s) | Lab rules |

Kinds can start as a **list** entry, not a hard enum.  
**Client-facing multi-event programs** remain **`client_projects`**, not lab project kinds.

## Mapping from today

| Current | Proposed |
|---------|----------|
| `projects` | **`orders`** |
| `project_users` | **`order_users`** (or keep junction name temporarily) |
| `samples.project_id` | **`samples.order_id`** |
| `has_project_access()` | `has_order_access()` (+ optional lab project-level access later) |
| Laboratory QC **system project** | Laboratory QC **system order** (or system lab project + system order—decide at design time) |
| **`client_projects`** | **Keep as-is** (name and role). Orders continue to use `client_project_id` for client/CRO reporting |
| API `/projects` (today’s sample container) | `/orders` (compat alias during migration) |
| UI “Projects” (today) | **Orders**; keep **Client projects** UI; add **Projects** for lab-internal work |

### Access / RLS (sketch)

- **Order-level** access remains the primary sample wall (today’s model).  
- **`client_projects`** remain client-scoped reporting/grouping (existing RLS patterns).  
- **Lab `projects`:** internal; method-dev/scratch use lab roles. Optional later: project-level grants for child orders.  
- Do not require a lab project for client/CRO report identity—that is **`client_project_id`**.

## Method-dev (tie-in) — data-parsers Decision #6

**Locked in data-parsers:** **no non-reportable runs**; structured import always requires `analysis_id`. Method-dev is **deferred to this idea** (lab projects), not a null-analysis path.

When this idea is implemented, prefer:

| Need | Prefer |
|------|--------|
| Assay under development | **Draft analysis** + versioned parsers (data-parsers Decision #5) |
| Related work over weeks | **Lab project** kind = method_dev (not a client_project) |
| Samples / spikes for the program | **Orders** optionally under that lab project |
| Client/CRO report line | **`client_project_id` on the order** when billable/client work—method-dev orders often omit it |
| Not yet reportable | Policy on promote / draft analysis / lab project kind—**still has an analysis** |

Until then: production path only—analysis required for import.

## Migration (when scheduled)

Pre-release friendly options:

1. **Rename in place:** today’s `projects` → `orders`, update FKs/API/UI; **leave `client_projects` and `orders.client_project_id` intact**.  
2. **Create new** lab `projects` table + optional `orders.project_id` (lab workspace FK).  
3. Backfill lab projects only as needed (e.g. method-dev); do **not** auto-create lab projects that duplicate client_projects.  
4. If rename collision is painful: temporarily name lab table `lab_projects` / `work_programs`, then rename.

Prefer one clean rename migration over long dual-write; product is pre-release.

## Explicit non-goals (until this idea is scheduled)

- Renaming or splitting as part of **data-parsers P0/P1**  
- **Merging or removing `client_projects`** — they stay for client/CRO reporting  
- Replacing analysis/parser catalog scope with lab project ownership  
- Full ELN “study” / protocol management  
- Multi-tenant rewrite ([multi-tenant.md](multi-tenant.md))  
- Changing batch cross-order rules in the same cycle (unless required by FK renames)

## Open questions

| # | Question | Status |
|---|----------|--------|
| 1 | Must every order belong to a **lab** project, or is `project_id` optional? | Open — lean **optional** |
| 2 | Does `client_id` stay on order, only on lab project, or both? | Open — lean keep on **order** |
| 3 | Fate of **`client_projects`**? | **Decided: keep** for client/CRO reporting |
| 4 | Lab project-level vs order-level **RLS** for client users? | Open — lean clients see **orders** + client_projects, not internal lab projects |
| 5 | Can method-dev lab projects have **no client**? How do internal samples accession? | Open — lean yes, internal client or null client policy |
| 6 | UI nav: Client projects vs Orders vs lab Projects | Open |
| 7 | Rename **Laboratory QC** system row to order vs wrap in internal lab project? | Open |
| 8 | LimsRun: optional lab `project_id` for runs not sample-bound? | Open |
| 9 | Migration compat period for `/projects` → `/orders`? | Open |

## Success criteria (when promoted to requirements)

1. Domain language: **order** = sampling event / sample batch; **client project** = client/CRO report id; **lab project** = internal work over time.  
2. Samples always hang off **orders**; orders keep **`client_project_id`** for reporting when applicable.  
3. Lab **projects** optionally group orders / method-dev work—**without** replacing client_projects.  
4. Method-dev / scratch use **lab project kinds** + draft analysis; not null-analysis hacks.  
5. CRO/client reports can resolve **client project id** from the order chain.  
6. Existing accessioning, batching, and client isolation still work after rename.  
7. API/UI and manuals use distinct labels for the three concepts.

## Out of scope links

- Parser versioning / import: [open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md) Decision #5  
- Promote-on-publish: [manuals/lims-runs.md](../manuals/lims-runs.md)  
- Lab buildings/rooms: [lab-locations.md](lab-locations.md)  
)
