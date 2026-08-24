# Tech sketches

Lightweight **how** documents produced **after requirements** and **before or alongside** architecture / UI reviews.

## Purpose

| Tech sketch answers | It is not |
|---------------------|-----------|
| Proposed data model, APIs, engine contracts | Full product requirements (that’s `requirements/`) |
| Sequence of runtime steps | CEO / market justification |
| Risks and open technical questions | Final architecture verdict (that’s `architecture-review/`) |
| Enough detail to review and implement a phase | Always a long design novel (optional deeper writeups go to `design/`) |

## When to write one

- **Full pipeline** features: **required** (or architecture review cannot complete).  
- **Small** work: optional.  
- **Tiny** work: skip.

## Naming

Use the same stem as requirements/reviews, e.g.:

- `requirements/data-parsers-lims-runs.md`  
- `tech-sketch/data-parsers-lims-runs.md`  
- `architecture-review/data-parsers-lims-runs.md`

## Suggested outline

1. Problem / link to requirements  
2. Goals and non-goals (technical)  
3. Proposed components and data model  
4. Key contracts (e.g. JSON Schema / Pydantic for configs)  
5. Runtime flows (import, setup, AI job if any)  
6. Migration / compatibility  
7. Phase mapping (what lands in P0 vs P1…)  
8. Open technical risks → link to `open-questions/`

## Process

See [development-process/README.md](../development-process/README.md).
