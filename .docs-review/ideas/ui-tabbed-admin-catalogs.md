# Idea: UI cleanup — tabbed shells with logical menu names

**Status:** Placeholder — **UI/nav cleanup**; independent of data-parsers P1 schema  
**Date:** 2026-07-20 · **Updated:** 2026-07-20 (menu names + expanded groups)  
**Related:** Admin Instruments UI (P0); Lab Mgmt; [orders-and-projects](orders-and-projects.md); [data-parsers](../schema-changes/data-parsers-lims-runs.md)

## One-liner

1. **Sidebar items** name a **logical domain** (shell), not every entity.  
2. **In-page tabs** host the related catalog UIs.  
3. Group by **how lab people think**, never by sprint timing.  
4. Split entities that only shared an implementation window (e.g. instruments vs CRO).

## Principle

| Layer | What it is | Example |
|-------|------------|---------|
| **Menu item** | Domain shell — short, stable label | **Assay catalog**, **Customers**, **Access control** |
| **Tab** | Concrete entity / list UI | Analyses · Analytes · Units · Test batteries |
| **Deep link** | Detail / nested config | Analysis → linked analytes |

**Tabs = domain kinship.**  
**Separate menu item = different domain or different primary audience.**

## Proposed information architecture

### Legend

| Column | Meaning |
|--------|---------|
| **Menu label** | Sidebar (and Admin overview card) text |
| **Route shell** | Suggested path for the shell page |
| **Tabs** | In-page tab labels → existing entity screens |
| **Where** | Admin vs Lab Mgmt |
| **Permission (typical)** | Who sees the menu item |

---

### Lab Management

| Menu label | Route shell | Tabs | Permission | Notes |
|------------|-------------|------|------------|--------|
| **Customers** | `/customers` | **Clients** · **Client projects** | `project:manage` (or current client/project access) | Client org + their reportable program ids |
| **Work** *(or **Sample work**)* | `/work` | **Orders** · **Projects** | `project:manage` / project access | See [Projects & orders](#projects--orders-logical-group) |
| **Assay catalog** | `/assay-catalog` | **Analyses** · **Analytes** | `analysis:manage` | Lab-facing; batteries optional (lean: Admin only) |

**Today’s mapping (until orders rename ships):**

| Menu label | Tabs (interim) |
|------------|----------------|
| **Customers** | Clients · Client projects |
| **Work** | **Projects** only (today’s order-like entity) — tab strip can still be prepared as Orders later, or single-tab until rename |
| **Assay catalog** | Analyses · Analytes |

Redirects: `/clients`, `/client-projects`, `/projects`, `/analyses`, `/analytes` → appropriate shell + tab.

---

### Admin (`config:edit` unless noted)

| Menu label | Route shell | Tabs | Notes |
|------------|-------------|------|--------|
| **Overview** | `/admin` | — | Dashboard cards → shells |
| **Lists** | `/admin/lists` | — | Standalone (config backbone) |
| **Containers** | `/admin/containers` | **Container types** *(+ types of packaging later if any)* | Today: container types only |
| **Assay catalog** | `/admin/assay-catalog` | **Analyses** · **Analytes** · **Test batteries** · **Units** | What the lab can measure + how units attach |
| **Instruments** | `/admin/instruments` | **Types** · **Instruments** | Lab equipment only |
| **CRO sources** | `/admin/cro-sources` | — | Standalone; **not** under Instruments |
| **Data parsers** | `/admin/data-parsers` | — | P1 when built; own menu item |
| **Access control** | `/admin/access` | **Users** · **Roles** | People and permissions |
| **Custom fields** | `/admin/custom-fields` | — | Standalone |
| **Workflows** | `/admin/workflow-templates` | — | Standalone |
| **Help** | `/admin/help` | — | Standalone |

Redirects: existing `/admin/analyses`, `/admin/analytes`, `/admin/test-batteries`, `/admin/units`, `/admin/users`, `/admin/roles` → shells + tabs.

---

## Menu label guide (logical names)

Names should answer: *“What area of the lab is this?”* not *“What table am I editing?”*

| Menu label | Why this name | Avoid |
|------------|---------------|--------|
| **Customers** | Client org + client programs people talk about together | “Clients and client projects” as two peers |
| **Work** / **Sample work** | Intake and multi-event lab work in one place | Two “project” words without hierarchy |
| **Assay catalog** | Analyses, analytes, batteries, units = test offering | Separate “Units” far from analyses |
| **Instruments** | Lab boxes (type + instance) | “Instruments & CRO” |
| **CRO sources** | External data origin | Nesting under Instruments |
| **Access control** | Users + roles | Separate “Users” / “Roles” peers when always configured together |
| **Data parsers** | How files become run data | Hiding under Instruments |

Alternate labels (if product prefers):

| Menu | Alternatives |
|------|----------------|
| Customers | **Accounts**, **Clients** (if “projects” tab title makes “Customers” clear) |
| Work | **Sample work**, **Lab work**, **Intake** |
| Assay catalog | **Test catalog**, **Methods**, **Assays** |
| Access control | **People & access**, **Security** (weaker—sounds IT) |

---

## Group rationales (product)

### Customers = Clients · Client projects

| Tab | Entity |
|-----|--------|
| Clients | Org / account |
| Client projects | Client-facing program / job code for **reporting** (CRO needs this) |

Same persona (lab manager setting up who the work is for). Frequent “create client → create their project.”

### Projects & orders (logical group)

**Yes — they should share one shell** when both exist. That is the natural hierarchy in [orders-and-projects](orders-and-projects.md):

```
Work (menu)
  tabs:  Projects (lab, multi-event / method-dev)
         Orders   (one sampling event / sample batch)
```

| Tab | After rename | Today |
|-----|--------------|--------|
| **Orders** | Renamed from current `projects` | Current **Projects** UI (order-like behavior) |
| **Projects** | **New** lab-internal work-over-time | *Does not exist yet* |

**Until the orders rename / lab projects ship:**

- Menu can still be **Work** with a single tab **Orders** (labeled **Projects** temporarily if language not ready), **or** keep menu **Projects** with no tabs.  
- Prefer introducing the shell name **Work** only when tab language is clear, to avoid “Work → only Projects.”  
- **Do not** put **Client projects** in this shell — those belong under **Customers** (reporting identity, not lab work containers).

**Do not** put Clients under Work: client is the *who*; order/project is the *work package*.

### Assay catalog = Analyses · Analytes · Test batteries · Units

| Tab | Why here |
|-----|----------|
| Analyses | Assay / panel |
| Analytes | Measurands |
| Test batteries | Bundles of analyses for ordering |
| Units | Concentrations, masses, volumes used on analytes/results |

Units sit with assay config more than with “Containers” or “Lists.” List system remains global primitives under **Lists**.

**Lab Mgmt** assay shell can omit **Test batteries** and **Units** if those stay config-only (lean: batteries + units Admin-only; Lab Mgmt = Analyses · Analytes).

### Instruments = Types · Instruments

Unchanged intent: type (vendor/model) + instance (nickname/serial).

### CRO sources — standalone

External export origin; only meets instruments as **parser source XOR** on Data parsers UI.

### Access control = Users · Roles

Always configured together; fewer sidebar items; matches admin mental model.

---

## CRO vs instruments (lock)

```
Admin
  ├── Instruments     tabs: Types | Instruments
  ├── CRO sources     standalone
  └── Data parsers    (P1) — instrument | CRO picker lives here
```

## Suggested sidebar order

### Lab Mgmt (example)

1. Projects → becomes **Work** (when ready)  
2. **Customers** (Clients · Client projects)  
3. **Assay catalog** (Analyses · Analytes)  

### Admin (example)

1. Overview  
2. Lists  
3. **Assay catalog** (Analyses · Analytes · Batteries · Units)  
4. Containers (types)  
5. Instruments (Types · Instruments)  
6. CRO sources  
7. Data parsers *(when P1)*  
8. **Access control** (Users · Roles)  
9. Custom fields · Workflows · Help  

---

## UX rules for tabbed shells

1. Menu label = domain; tab label = entity.  
2. **Create** button matches the **active tab**.  
3. **URL** encodes tab (`?tab=` or path segment—pick one project-wide).  
4. **Redirect** old routes.  
5. **Permissions:** hide tabs user cannot use; hide menu if no tabs left.  
6. Lazy-load tab data on focus.  
7. Fill-height grids; tab-specific empty states.  
8. Nested detail routes (e.g. analysis↔analyte linker) **outside** the tab strip, with back to the right tab.

## Implementation phases (suggested)

| Phase | Scope |
|-------|--------|
| **A** | Split CRO from Instruments; menu **Instruments** + **CRO sources** |
| **B** | Admin **Assay catalog** (analyses, analytes, batteries, units) + redirects |
| **C** | Admin **Access control** (users, roles) |
| **D** | Lab Mgmt **Customers** (clients, client projects) |
| **E** | Lab Mgmt **Assay catalog** (analyses, analytes) |
| **F** | **Work** shell — after or with [orders-and-projects](orders-and-projects.md) rename; interim optional |

No schema required for A–E. F may need the orders/projects product work for honest tab labels.

## Explicit non-goals

- Merging DB tables or APIs.  
- Grouping by sprint (instruments + CRO again).  
- Putting client projects under Work.  
- Renaming backend `projects` → `orders` in this idea alone (track in orders-and-projects).  
- Full visual redesign beyond nav + shells.

## Open questions

| # | Question | Lean |
|---|----------|------|
| 1 | Menu **Work** vs **Sample work** vs keep **Projects** until rename? | Hold **Projects** until orders rename; then **Work** with Orders · Projects |
| 2 | Lab Mgmt assay shell includes Units? | **No** — Units Admin-only in Assay catalog |
| 3 | Lab Mgmt includes Test batteries? | **No** — Admin Assay catalog only |
| 4 | Customers vs Accounts vs Clients as menu name? | **Customers** if client projects are second tab; else **Clients** |
| 5 | Access control vs Users & roles? | **Access control** |
| 6 | Tab state encoding? | Project-wide **`?tab=`** or path segments—pick in first PR |
| 7 | Containers shell name if only types? | **Container types** until more tabs appear |

## Success criteria

1. Every multi-entity domain has a **clear menu name** + **tabs**, not N peer links.  
2. Instruments ≠ CRO.  
3. Clients + client projects under one customer-facing shell.  
4. Units live with assay configuration.  
5. Users + roles under Access control.  
6. Path to **Work** = Projects + Orders when product rename lands—without putting client projects there.  
7. Redirects preserve old bookmarks.

## Cross-links

- [orders-and-projects.md](orders-and-projects.md) — entity rename + lab projects  
- Data parsers P1 — separate **Data parsers** menu  
- [lab-locations.md](lab-locations.md) — future instruments room tab? (optional later)  
