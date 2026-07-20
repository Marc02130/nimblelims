# Idea: Rename `projects` → `orders`; add real **projects** for work over time

**Status:** Placeholder — **not in data-parsers P0/P1**  
**Date:** 2026-07-19  
**Related:** Accessioning / samples / RLS; [client_projects](../user-stories/nimblelims-user.md) (US-25); method-dev / non-reportable runs (data-parsers open Q6); [multi-tenant](multi-tenant.md); Lab QC system project

## One-liner

1. Today’s **`projects`** table is really an **order**: a **batch of samples from one environmental sampling event** (or similar discrete submission)—not a long-lived initiative.  
2. **Rename** that concept to **`orders`** (table/API/UI) so language matches the domain.  
3. Introduce a new **`projects`** table for **related work over time** (method development, multi-event campaigns, client programs, scratch/R&D workspaces).

## Why change existing `projects`?

| Today (code name) | Reality in env labs |
|-------------------|---------------------|
| Table: **`projects`** | Discrete **submission / order**: samples from one sampling event, with due dates, client, status, access |
| Samples require `project_id` | Sample belongs to **that order/event**, not a multi-year program |
| `client_projects` exists | Grouping of Nimble “projects” under a client initiative — naming already strained |
| UI/docs say “Project” | Users hear “ongoing work”; product behaves like **order / job / submission** |

**Environmental sampling pattern:** field team samples a site on a date → cooler of containers → lab accessions as **one order** → tests/results for that event. Weeks later, another event is **another order**, even for the same client site/program.

| After rename | Meaning |
|--------------|---------|
| **`orders`** | One sampling event / submission: a batch of samples, due dates, status, client, access grants |
| **`projects`** (new) | Longer-lived container: related orders (and optional other work) over time |
| **`client_projects`** | Revisit naming — may become client-side program label, or fold into new `projects` |

## Problem

- **Language debt:** “project” misleads product, support, and new features (method-dev “project” vs sample “project”).  
- **No home for work over time:** multi-event monitoring, method validation programs, R&D, training, and multi-order client campaigns need a **parent** of orders.  
- **`client_projects`** is a partial attempt at grouping but still parents *today’s* project rows and is client-centric only.  
- **Method-dev / non-reportable** discussion: developers want a place for related runs, draft analyses, and samples over time — **not** “null analysis” and **not** abusing order-as-project.

## Target model (sketch)

```
clients
  └── projects (NEW)                    -- work over time
        id, name, description,
        client_id NULL?,                -- null = internal lab project (R&D, method-dev, scratch)
        kind / type?,                   -- production | method_dev | monitoring | scratch | …
        status, start_date, end_date?,
        active, custom_attributes, …

  └── orders (RENAMED from projects)    -- one sampling event / submission
        id, name?, 
        project_id NULL → projects,     -- optional: order belongs to a long-lived project
        client_id NOT NULL,             -- keep if order can stand alone; or derive via project
        client_project_id?,             -- deprecate or map into new projects
        start_date, due_date,
        status, custom_attributes, …
        -- access: order_users (renamed from project_users) and/or inherit project access

samples.order_id NOT NULL → orders      -- renamed from project_id

-- optional later
lims_runs.project_id NULL → projects    -- method-dev runs without samples
analyses / notes / files scoped by project (policy TBD)
```

### Hierarchy (env lab)

| Level | Grain | Example |
|-------|--------|---------|
| **Client** | Customer org | Acme Environmental |
| **Project** (new) | Related work over time | “Acme River 2026 monitoring”; “ICP metals method validation” |
| **Order** (today’s project) | One sampling event / submission | “River Site B — 2026-07-12 event”; 24 aqueous samples |
| **Sample** | One specimen | SW-01, 2026-07-12 |
| **Batch** (existing) | Lab processing group | Prep batch across orders when allowed |

### Project kinds (illustrative)

| Kind | Typical content | Promote / reportable |
|------|-----------------|----------------------|
| **Production / monitoring** | Client orders + samples | Normal |
| **Method development** | Draft analyses, parser versions, spike samples, lims runs | Import OK; promote gated / off by default |
| **Scratch / training** | Throwaway samples and runs | No promote |
| **Internal QC program** | Related to Lab QC system order(s) | Lab rules |

Kinds can start as a **list** entry, not a hard enum.

## Mapping from today

| Current | Proposed |
|---------|----------|
| `projects` | **`orders`** |
| `project_users` | **`order_users`** (or keep junction name temporarily) |
| `samples.project_id` | **`samples.order_id`** |
| `has_project_access()` | `has_order_access()` (+ optional project-level access) |
| Laboratory QC **system project** | Laboratory QC **system order** (or system project + system order—decide at design time) |
| `client_projects` | Open: rename to client **programs**, merge into new `projects`, or keep as external CRM id layer |
| API `/projects` | `/orders` (compat alias during migration) |
| UI “Projects” | **Orders**; new **Projects** for long-lived work |

### Access / RLS (sketch)

- **Order-level** access remains the primary sample wall (today’s model).  
- **Project-level** access may grant all child orders, or projects are navigation-only at first.  
- Internal projects (`client_id` null) use lab roles, not client RLS.

## Method-dev / non-reportable (tie-in)

Do **not** use “run with no analysis” as the method-dev model.

| Need | Prefer |
|------|--------|
| Assay under development | **Draft analysis** + versioned parsers (data-parsers Decision #5) |
| Related work over weeks | **Project** kind = method_dev |
| Samples / spikes for the program | **Orders** under that project (or one long-lived order if product allows) |
| Non-reportable | **No promote** (draft analysis / project policy)—not missing `analysis_id` |

Data-parsers P0/P1 can stay on **lab-global parsers + analysis-scoped import** without waiting for this rename. This idea unblocks **language and long-horizon grouping** later.

## Migration (when scheduled)

Pre-release friendly options:

1. **Rename in place:** `projects` → `orders`, update FKs/API/UI; then **create new** empty `projects` and optional `orders.project_id`.  
2. Add `projects` first under a temporary name (`work_programs`) if rename collision is painful; then rename.  
3. Backfill: each existing order gets an optional default project per client (“{Client} general”) or leave `project_id` null until users group them.

Prefer one clean rename migration over long dual-write; product is pre-release.

## Explicit non-goals (until this idea is scheduled)

- Renaming or splitting as part of **data-parsers P0/P1**  
- Replacing analysis/parser catalog scope with project ownership  
- Full ELN “study” / protocol management  
- Multi-tenant rewrite ([multi-tenant.md](multi-tenant.md))  
- Changing batch cross-order rules in the same cycle (unless required by FK renames)

## Open questions

| # | Question |
|---|----------|
| 1 | Must every order belong to a project, or is `project_id` optional? |
| 2 | Does `client_id` stay on order, only on project, or both (denormalized)? |
| 3 | Fate of **`client_projects`**: keep, merge into `projects`, or rename to programs? |
| 4 | Project-level vs order-level **RLS** for client users? |
| 5 | Can method-dev projects have **no client**? How do internal samples accession? |
| 6 | UI nav: Projects → Orders → Samples, or Orders primary with optional Project filter? |
| 7 | Rename **Laboratory QC** system row to order vs wrap in internal project? |
| 8 | LimsRun: optional `project_id` for runs not sample-bound? |
| 9 | Name collision in code reviews / docs during migration—compat period length? |

## Success criteria (when promoted to requirements)

1. Domain language: **order** = sampling event / sample batch; **project** = work over time.  
2. Samples always hang off **orders**; orders optionally group under **projects**.  
3. Method-dev / monitoring / scratch can use **project kinds** without null-analysis hacks.  
4. Existing accessioning, batching, and client isolation still work after rename.  
5. API/UI and manuals updated; no dual “project means two things” in user-facing copy.

## Out of scope links

- Parser versioning / import: [open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md) Decision #5  
- Promote-on-publish: [manuals/lims-runs.md](../manuals/lims-runs.md)  
- Lab buildings/rooms: [lab-locations.md](lab-locations.md)  
)
