# Idea: Lab locations (buildings & rooms) + rename client locations → address

**Status:** Placeholder — **not in data-parsers P0/P1**  
**Date:** 2026-07-19  
**Related:** [data-parsers / instruments](../schema-changes/data-parsers-lims-runs.md), containers, equipment, clients/people

## One-liner

1. Rename today’s client **mailing/site** table from `locations` → **`addresses`** (semantics match reality).  
2. Introduce a real **lab location** model: **buildings** (optional link to an address) and **rooms** (inside buildings)—for instruments, storage, and other assets.

## Why change existing `locations`?

| Today | Reality |
|-------|---------|
| Table name: **`locations`** | Rows are **client postal/site addresses** (`client_id`, street, city, country) used with people/contacts |
| Implied meaning | “Where something is in the lab” — **misleading** |

**Proposal:** rename table (and model/API) to **`addresses`** so “location” is free for lab ops.

| After rename | Meaning |
|--------------|---------|
| **`addresses`** | Physical postal/site address (client-related or shared); street, city, etc. |
| **`lab_locations`** (or `locations` after rename) | Lab facility graph: building / room |

Migration is rename + API path updates (`/locations` → `/addresses` or keep alias)—product timing TBD.

## Problem

- Instrument **instances** need optional **where** (building/room), plus serial.  
- Containers and other assets often need the same.  
- Free-text “Room 12” does not scale.  
- Client address table must not be overloaded for lab floor plans.

## Target model (sketch)

```
addresses                          -- renamed from locations
  id, name?, client_id?,
  address_line1, address_line2, city, state, postal_code, country,
  lat/long?, type?, active, …

lab_buildings                      -- or lab_locations with type=building
  id, name,                        -- "Building A"
  address_id NULL → addresses,     -- campus / street address of the building
  description, active, …

lab_rooms                          -- or lab_locations with type=room + parent
  id, name,                        -- "Room 12" / "Cold room 2"
  building_id NOT NULL → lab_buildings,
  description, active, …

instruments.room_id NULL → lab_rooms   -- optional; not in parsers P0/P1
-- future: containers.room_id, etc.
```

### Hierarchy

| Level | Has address? | Example |
|-------|----------------|---------|
| **Address** | *Is* the street address | 100 Lab Ave, City |
| **Building** | Optional FK → address | Building A (at that address) |
| **Room** | No (inherits building’s address) | Room 12, Mass Spec suite |

Optional later: floor, bench, shelf as children of room—or list-backed “place type.”

### Alternative: single `lab_locations` table

```
lab_locations (
  id, name, kind: building | room,
  parent_id NULL,           -- room → building
  address_id NULL,          -- only for buildings
  …
)
```

Same product rules; one table vs two. Choose in a future tech sketch.

## Explicit non-goals (this idea until scheduled)

- Implementing lab locations in the **data-parsers** cycle  
- Putting `location_id` on instruments in P0/P1  
- Using client `locations`/`addresses` as “Room 12”  

## Current instruments decision (unchanged)

**No location/room column on instruments** until this idea is requirements + schema-changes. Instance fields for parsers P0: **type FK, serial, name**.

## Open questions (when this idea is reviewed)

1. Rename `locations` → `addresses` in one migration vs dual name period?  
2. Two tables (buildings/rooms) vs single hierarchical `lab_locations`?  
3. Can a building exist without an address (on-campus only name)?  
4. Share rooms with container storage and instruments?  
5. Permissions: same as lab config vs facilities admin?  

## Success metrics (future)

- Client addresses clearly named; no confusion with lab places  
- Instruments/assets reportable by building/room  
- No free-text location sprawl for lab assets  

## Links when work starts

- Requirements / tech sketch / **schema-changes** (rename + new tables)  
- Update client/people APIs and UI labels  
- Instruments: optional `room_id`  
- Security: lab-global config (multi-tenant still OOS unless multi-tenant idea ships)  
