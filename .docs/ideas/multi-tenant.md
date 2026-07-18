# Idea: Multi-tenant / org segregation

**Status:** Exploratory placeholder — **out of scope for current development**  
**Date:** 2026-07-18  
**Related:** Existing RLS / client project access (partial isolation today); data-parsers and other config catalogs currently treated as **lab-global**

## One-liner

True multi-tenant isolation: segregate configuration and data **by organization** so multiple labs/customers can share infrastructure without seeing each other’s instruments, parsers, samples, or results—when NimbleLIMS has real multi-org production users.

## Why not now

- Product is **pre-release** / early; **real users** are not yet multi-org deployments.  
- Current work (including data parsers) assumes a **single lab deployment**: no segregating instruments, CRO sources, parsers, or similar catalogs by org.  
- Investing in full tenant isolation, dual-write, and cutover patterns before that need is premature.

**Until this idea is prioritized:** do not design schema or UX around per-org config namespaces for new features unless already required by existing client/project RLS.

## Problem (when we need it)

| Need | Today (approx.) | Multi-tenant target |
|------|-----------------|---------------------|
| Sample/result visibility | Project/client RLS paths | Strong tenant boundary |
| Lab config (instruments, parsers, lists, …) | Effectively **one lab** | Config owned by tenant/org |
| Super-admin / SaaS ops | N/A or single deploy | Cross-tenant admin carefully gated |
| Migrations / onboarding | One schema, one lab | Per-tenant bootstrap, no cross-tenant leakage |

## Sketch (not committed)

Possible directions (to explore later):

1. **Deploy-per-lab** (simplest “tenancy”) — isolation by infrastructure, not rows.  
2. **Row-level tenant_id** on all config + data tables + RLS.  
3. **Hybrid** — shared app, tenant-scoped catalogs; platform tables global.  

Open questions when reviewed:

- Tenant = Client? Lab? Billing org?  
- Shared vs dedicated DB?  
- How existing `client_id` / project RLS maps to tenants  
- Migration of single-lab DBs into multi-tenant  

## Explicit non-goals for current roadmap

- Segregating **instruments / cro_sources / data parsers** by org  
- Multi-tenant switchover plans in schema-changes for current features  
- Client users administering another org’s parsers  

## Success metric (future)

Zero cross-tenant data or config leakage in penetration tests; time-to-onboard a new org measured in hours, not custom forks.

## Links when work starts

- Requirements / tech sketch / schema-changes / open-questions under a future stem e.g. `multi-tenant`  
- Security review mandatory  
