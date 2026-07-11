# Idea: Multi-tenancy

**Status:** Exploratory (not scheduled)  
**Date:** 2026-07-11

## Terminology

| Term | Meaning |
|------|---------|
| **Lab** | Organization running NimbleLIMS (env lab, CRO, biotech internal lab) |
| **Lab personnel** | Lab employees (System client users today) |
| **Client** | **Customer of the lab** (sponsor, industrial customer)—not “SaaS tenant of the NimbleLIMS vendor” |
| **Lab-client isolation** | Client A never sees Client B’s data **within one lab** |
| **Multi-lab tenancy** | Lab A never sees Lab B’s data on a **shared product platform** |

These are different problems. Most CRO / environmental-lab value is **lab-client isolation**.

## What works well today (lab–client)

The existing model is built for multi-**client** labs:

- `clients` + `projects.client_id`
- Client users scoped to their projects; lab (System) staff see across clients
- RLS (`has_project_access`, session user id, FORCE RLS on many tables) + API checks
- Fits CROs (e.g. Charles River–style sponsors) and env labs with many industrial customers

**Assessment:** ~8–9/10 fit for lab–client isolation. Harden new tables (ELN, SOP jobs, vectors) to the same rules; keep shared assay config as **lab-owned** unless tagged client-confidential.

## What does *not* fit drop-in (multi-lab SaaS)

One deployment is effectively **one laboratory**:

- Single **System client** = “the lab”
- Global unique names on many entities
- Lists / FieldDefinitions / templates / process defs largely **lab-global**, not org-partitioned
- No first-class `organization` / lab-tenant key for config, billing, branding

**Assessment:** ~4–5/10 for many independent labs on one shared DB without a new tenant layer.

## Options if we host multiple labs later

| Approach | Pros | Cons |
|----------|------|------|
| **DB (or schema) per lab** | Reuses current model as-is; strong isolation | Ops overhead; harder cross-lab analytics |
| **Shared DB + `organization_id`** | Single ops plane | Large migration; redefine System; fix global uniques; scope all config |

**Default lean:** Prefer **DB-per-lab** for early hosted multi-lab; invest in shared multi-lab schema only with clear product demand.

## Non-goals (for this idea note)

- Redesigning RBAC from scratch
- Multi-region / multi-site “site” hierarchy (can be a later partition)
- Billing/metering design

## Related

- API isolation summary: [../manuals/api-endpoints.md](../manuals/api-endpoints.md) (Client Data Isolation)
- Open questions #7 / #9 (sample journey; lab-only data edit): [../open-questions/experiments.md](../open-questions/experiments.md)
- SOP RAG memory must respect lab-client SOP ownership: [../design/sop-rag-config.md](../design/sop-rag-config.md) §3.0–3.7

## Open questions (if ever productized)

1. Is the primary hosted product **one lab per deploy**, or true multi-lab SaaS?
2. Should client-confidential SOPs / design docs always be client-tagged for RAG?
3. Multi-site single company: is `client_id` enough, or do we need `site_id`?
