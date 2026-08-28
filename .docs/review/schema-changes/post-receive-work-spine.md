# Schema changes: post-receive-work-spine

**Feature / cycle:** post-receive work spine  
**Phases covered:** P1 (asked-for) required this cycle; P2 tables specified so architecture can Accept the spine; P3 none; P4 additive FKs; P5 none  
**Status:** Draft for architecture review  
**Alembic revisions:** _(fill when implemented)_  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)

## 1. Summary

P1 adds asked-for + analysis param defs. P2 adds routing_map + work_orders. P3 is column-use only. P4 stores apply output on the SOP job. P5 uses existing parser tables.

RLS: asked_for and work_orders follow sample → project (same pattern as tests). routing_map is config (admin / config:edit); FORCE RLS with admin or config:edit policy.

## 2. Delta

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `analysis_param_defs` | Catalog of order params per analysis | `id`, `analysis_id` FK, `key` text, `data_type` text, `required` bool, `source_list_id` uuid null, `sort_order` int, audit |
| `asked_for` | Requested analysis on a sample | `id`, `sample_id` FK, `analysis_id` FK, `tat_days` int not null check > 0, `params` jsonb not null default `{}`, `status` text not null, `routed_work_order_id` uuid null, audit |
| `routing_map` | P2: analysis × sample_type × TAT range → process chain | `id`, `analysis_id` FK, `sample_type_id` uuid (list entry), `tat_range` int4range not null, `process_definition_ids` uuid[] not null, `active` bool, audit |
| `work_orders` | P2: backlog item | `id`, `asked_for_id` FK unique, `sample_id` FK, `analysis_id` FK, `process_definition_ids` uuid[] not null, `status` text not null, `process_id` uuid null FK eln_processes, audit |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| `sop_parse_jobs` (name as in code) | ADD `process_definition_id` uuid null FK | P4 |
| `eln_processes` | ADD `work_order_id` uuid null FK | P2; optional reverse of work_orders.process_id — pick **one** FK direction at implement (prefer `work_orders.process_id` only) |
| `results` | none | P3 uses `reported_result`, `qualifiers`, `raw_result` |
| `tests` | none | WO-7 timing only |

Do **not** add `results.unit_id`. Do **not** add asked-for columns on `samples`.

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| `uq_asked_for_open` | unique `(sample_id, analysis_id)` WHERE status <> 'cancelled' | RQ-AF-4 |
| `asked_for_status_chk` | status in (`requested`,`routed`,`cancelled`) | |
| `work_orders_status_chk` | status in (`queued`,`in_progress`,`completed`,`cancelled`) | |
| `routing_map_tat_excl` | EXCLUDE gist (`analysis_id` WITH `=`, `sample_type_id` WITH `=`, `tat_range` WITH `&&`) WHERE active | RQ-WO-4 |
| `routing_map_chain_chk` | `array_length(process_definition_ids, 1) >= 1` | empty chain forbidden |
| indexes | `asked_for(sample_id)`, `asked_for(status)`, `work_orders(status)`, `work_orders(sample_id)` | lists |

### 2.4 Enums / types

No Postgres ENUM. Text + check. Status lists may also seed `list_entries` if the app pattern prefers lists; if so, still constrain in DB.

### 2.5 RLS

| Table | Policy sketch |
|-------|----------------|
| `asked_for` | USING/WITH CHECK via sample.project access (mirror `tests`) |
| `work_orders` | same |
| `analysis_param_defs` | read: authenticated; write: config:edit / admin |
| `routing_map` | read: authenticated lab roles; write: config:edit / admin |

FORCE ROW LEVEL SECURITY on all four.

## 3. Seed

P1: no asked-for rows. Param defs optional (ELISA example: `cell_line` list-backed) — **do not** invent Qubit/blood IDs (extract-hold testdata Hold).

P2: **no** default routing rows that claim blood→Qubit until dest type lands.

## 4. Out of schema this cycle

Projects rename; intake profiles; lots; `status_history`; parser table redesign (already shipped).
