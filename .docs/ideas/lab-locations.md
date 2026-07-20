# Idea: Lab locations (facility / storage places)

**Status:** Placeholder — **not in data-parsers P0/P1**  
**Date:** 2026-07-19  
**Related:** [data-parsers / instruments](../schema-changes/data-parsers-lims-runs.md), containers, equipment

## One-liner

First-class **lab facility locations** (building, room, bench, cold room, etc.) so instruments, containers, and other assets can record **where they are**.

## Why not use existing `locations`?

| Table | Meaning today |
|-------|----------------|
| **`locations`** | **Client** addresses (mail/site for people/contacts)—`client_id`, street, city, country |
| **Lab locations (this idea)** | **Internal lab** places—not a client mailing address |

Reusing client `locations` for “LCMS in Room 12” would conflate CRM geography with lab ops.

## Problem

Instrument **instances** need optional location (and serial). Containers and other assets often need the same. Without a lab location model, we either skip location (current choice for instruments) or stuff free-text.

## Sketch (not committed)

```
lab_locations (
  id, name,  -- e.g. "Building A / Room 12 / Bench 3"
  parent_id NULL,  -- optional hierarchy
  description, active, …
)

instruments.location_id → lab_locations  -- optional
containers.location_id → …  -- possible future
```

Open questions when reviewed:

- Hierarchy depth (site → building → room)?  
- List-backed “location type” vs free hierarchy?  
- Shared with sample storage vs instruments only?  

## Current decision (instruments)

**No location column on instruments** until this idea is a real requirements cycle. Instance fields for P0: type FK, serial, name, active.

## Success metric (future)

Assets reportable by room/bench; no free-text location sprawl.
