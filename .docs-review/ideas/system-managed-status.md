# Idea: System-managed status (samples & experiments)

**Status:** Placeholder — **priority**  
**Priority:** **High** — status is critical tracking; user-set status at create is the wrong default  
**Date:** 2026-08-12  
**Related:** Accessioning; Samples list; Experiment create; process start (Decision #24 — Available for Testing); [list-page-search.md](list-page-search.md)

## One-liner

**Status** on samples (and experiments) is **maintained by the system** through workflows — not chosen by the user at accessioning or experiment create. **Managers / admins** may still edit status deliberately.

## Why

- Status drives eligibility (e.g. cohort start requires **Available for Testing**), reporting, and audit.
- Letting any tech set status on create produces inconsistent queues and breaks process gates.
- Labs expect LIMS-like lifecycle: Received → Available for Testing → … via controlled transitions, not free-form dropdowns at create.

## Current state (NimbleLIMS)

| Surface | Today |
|---------|--------|
| Sample accessioning | User can set `status` (required field) |
| Sample edit | User with `sample:update` can change status |
| Experiment create | User can set experiment `status_id` |
| Process / experiment start | System checks status (Decision #24) but does not own transitions yet |

## Direction (when prioritized)

### Sample status

| Actor | Behavior |
|-------|----------|
| **System** | Sets status on accession (default **Received** or lab-configured intake status); advances on defined events (release to testing, testing complete, review, report, etc.) |
| **Lab tech** | **Cannot** set status at accessioning or normal edit (field hidden/read-only) |
| **Lab manager / Admin** | May edit status (override) with audit; prefer reason/note later |

Suggested default transitions (product to refine):

1. Accession → **Received** (system)  
2. Release / ready for lab → **Available for Testing** (system or manager action)  
3. In process / testing → optional intermediate statuses (system)  
4. Complete / review / report → system transitions  

### Experiment status

| Actor | Behavior |
|-------|----------|
| **System** | Draft on create; **In Progress** on start; **Completed** on complete rules |
| **Lab tech** | Does not pick status on create |
| **Manager / Admin** | May override |

### Permissions

- New or existing: e.g. only `config:edit` / manager role / dedicated `sample:status:override` for manual status change.  
- `sample:update` alone should **not** allow status override if that matches product.

## Non-goals (this idea)

- Full configurable state machine engine day one.  
- Client-visible status editing.

## Open when prioritized

- Exact default accession status and transition map.  
- Process assign does **not** change Sample.status (Available for Testing remains a separate gate). Process-sample status uses **queued / in_progress / completed** (see Decision #24).  
- UI: hide status on accessioning; show read-only + “Override status” for managers on sample detail.  
- Same pattern for experiment and process instance status lists.

## Suggested process

Ideation (this doc) → requirements (transition table + RBAC) → implement accessioning + experiment create + edit gates → dogfood with Decision #24 start eligibility → docs sync.
