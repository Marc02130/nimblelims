# Schema change: Extract-hold destination sample type

**Date:** 2026-08-23  
**Migration:** `0068_sample_type_transitions.py`  
**Scope:** Mathilda plan-entry destination-type slice

## Delta

Add `sample_type_transitions`, a client-scoped many-to-many catalog:

| Column | Type | Rule |
|--------|------|------|
| `id` | UUID | Primary key |
| `client_id` | UUID FK → `clients.id` | Required |
| `source_sample_type` | UUID FK → `list_entries.id` | Required |
| `operation` | varchar(16) | `aliquot` or `pool` |
| `allowed_dest_sample_type` | UUID FK → `list_entries.id` | Required |
| `active` | boolean | Defaults true |
| audit columns | UUID/timestamp | Existing catalog convention |

Unique key:
`(client_id, source_sample_type, operation, allowed_dest_sample_type)`.

No column is added to `samples`; existing `samples.sample_type`,
`samples.parent_sample_id`, and `samples.matrix` remain unchanged. Plan-line
`dest_sample_type` stays in the existing entry `config.plan_lines` JSON payload.

## Seed

- Ensure the Sample Types list contains `DNA`.
- Add `Blood × aliquot → DNA` for every existing client.
- New clients require catalog configuration through a future `config:edit`
  management surface; this slice exposes no catalog mutation API.

## RLS and authorization

RLS is enabled and forced. Administrators and System-client lab users can read
all rows; regular users are limited to their own `client_id`. The API added in
this slice is read-only and requires the existing `experiment:manage`
dependency. No create, update, or delete route is added, so catalog mutation
cannot bypass the locked `config:edit` requirement.

## Rollback

Drop the transition table and remove only the migration-owned `DNA` list entry
when no sample references it. Samples, matrix values, and entry plans are not
rewritten.
