# Schema changes: data-parsers-lims-runs

**Feature / cycle:** Data parsers, instruments/CRO sources, LimsRun lineage  
**Phases covered:** **P0 + P1** (P2 AI = no extra schema beyond setup files already in P1)  
**Status:** Schema **verified** by architecture (2026-07-18); updated 2026-07-18 — no ephemeral setup path; pre-release (no production switchover plan)  
**Alembic revisions:** _(none yet)_  
**Requirements:** [../requirements/data-parsers-lims-runs.md](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [../tech-sketch/data-parsers-lims-runs.md](../tech-sketch/data-parsers-lims-runs.md)  
**Architecture review:** [../architecture-review/data-parsers-lims-runs.md](../architecture-review/data-parsers-lims-runs.md)  
**Open questions:** [../open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md)

> **This is the authoritative schema delta for this cycle.** Architecture review of “what changes in the DB” should use **this file**, not a full read of the packet.

## 1. Summary

Add **instrument types** (vendor/model) and **instrument instances** (serial, type FK); **CRO sources**; re-scope **instrument_parsers** to **analysis × instrument instance|CRO only**; **DROP `experiment_template_id`** from parsers; add **lims_runs** FKs for instrument instance, CRO, parser. No lab location FK yet (existing `locations` = client addresses only). No change to `results` / promote schema.

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| **`instrument_types`** | Vendor/model class (what the box *is*) | `id`, `name` (e.g. display label), `vendor` NULL, `model` NULL, `description` NULL, `active`, audit cols |
| **`instruments`** | **Instance** of a type (which physical unit / named stream) | `id`, **`instrument_type_id` NOT NULL** → `instrument_types`, `name` (lab nickname), **`serial_number` NULL**, `description` NULL, `active`, audit cols — **no location_id** this cycle |
| **`cro_sources`** | External/CRO export-source catalog | `id`, `name`, `description` NULL, `client_id` NULL → `clients`, `active`, audit cols |
| **`parser_setup_files`** | Persisted example / test / edge fixtures for parser setup | `id`, `parser_id` FK (nullable until saved), `role` (`example`\|`test`\|`edge_fixture`), `filename`, `content_type`, `size_bytes`, storage (bytea or object ref), `created_by`, `created_at` |

**Instrument vs type**

| Entity | Holds | Example |
|--------|--------|---------|
| **Type** | vendor, model | Agilent 6495C |
| **Instance** | type FK, serial, lab name | “LCMS-1”, serial `US123456` |

**Location:** Do **not** FK instruments → client **`locations`**. That table should become **`addresses`** (rename idea). Lab **buildings/rooms** → [ideas/lab-locations.md](../ideas/lab-locations.md). No instrument location this cycle.

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| **`instrument_parsers`** | **DROP `experiment_template_id`** (column + FK + related indexes) | **Decided:** parsers are not template-scoped. Pre-migration data handling: §4 |
| **`instrument_parsers`** | ADD `analysis_id` UUID **NOT NULL** → `analyses(id)` | Required for every parser |
| **`instrument_parsers`** | ADD `instrument_id` UUID NULL → **`instruments`** (instance) | Lab path — analysis × **instance** |
| **`instrument_parsers`** | ADD `cro_source_id` UUID NULL → `cro_sources(id)` | CRO path |
| **`instrument_parsers`** | ADD `is_default` BOOLEAN NOT NULL DEFAULT false | Default among siblings |
| **`instrument_parsers`** | ADD `active` BOOLEAN NOT NULL DEFAULT true | Soft deactivate |
| **`instrument_parsers`** | `parser_config` JSONB | **No structural change** — content must match ParserConfig v1 (app validation) |
| **`lims_runs`** | *(optional)* last_instrument_id / last_parser_id for UI only | **Not** sole lineage—see **`lims_run_imports`** |
| **`lims_run_data`** | ADD `import_id` UUID NULL → `lims_run_imports` | Row-level lineage to import event |

### 2.1b Import events (multi instrument/parser per run)

| Table | Purpose | Key columns |
|-------|---------|-------------|
| **`lims_run_imports`** | One import file/batch on a run | `id`, `lims_run_id` NOT NULL, `instrument_id` NULL, `cro_source_id` NULL, `parser_id` NOT NULL, `imported_at`, `imported_by`, filename/meta optional |

`lims_runs.analysis_id` — **already exists**; **required** for structured import path (run tied to analysis).  
`lims_runs.experiment_template_id` — **unchanged** (protocol/lifecycle).

**Product (Decision #16):** A run may import from **multiple instruments/CROs** (hence multiple parsers). Each import must use a parser for **(run.analysis_id, that instrument|CRO)**—not a random parser.

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| **`instrument_parsers` source CHECK** | Exactly one of `instrument_id` / `cro_source_id` is non-null | Lab XOR CRO scope |
| **`instrument_parsers` analysis** | `analysis_id` NOT NULL | Every parser belongs to an analysis |
| **`lims_run_imports` source CHECK** | Exactly one of instrument_id / cro_source_id non-null | Same as parsers |
| **`uq_parser_default_instrument`** | UNIQUE (`analysis_id`, `instrument_id`) WHERE `is_default AND active AND instrument_id IS NOT NULL` | One default per analysis×instrument |
| **`uq_parser_default_cro`** | UNIQUE (`analysis_id`, `cro_source_id`) WHERE `is_default AND active AND cro_source_id IS NOT NULL` | One default per analysis×CRO |
| Drop indexes/FKs | Any index/FK solely on `instrument_parsers.experiment_template_id` | With column drop |
| Indexes on FKs | type, instance, parser, import FKs | Lookup performance |
| Optional unique | `instruments (instrument_type_id, serial_number)` WHERE serial not null | Avoid duplicate serials per type |

Exact CHECK SQL may be refined at implement time; intent is fixed.

**App (and ideally DB) integrity on import:**

```
import.parser.analysis_id = run.analysis_id
import.parser.instrument_id = import.instrument_id   -- if lab
import.parser.cro_source_id = import.cro_source_id   -- if CRO
```

**Capability:** instrument/CRO “can perform” this analysis ⇔ an active parser exists for `(analysis, instrument|cro)`. No separate capability table required for MVP.

**Note:** File **format** ~ **instrument type** (vendor/model). Parsers and imports key the **instance** (or CRO).

### 2.4 Enums / types

| Type | Change |
|------|--------|
| — | **None** this cycle |

### 2.5 Optional / not MVP (later — not P0/P1)

| Object | Notes |
|--------|-------|
| Snapshot column on `lims_runs` (e.g. `parser_config_snapshot` JSONB) | Open Q5 — lean defer |
| Dual-write / gradual production cutover of template parsers | **Out of scope** — pre-release; simple migrate-or-delete |
| **`instruments.room_id` / location** | Lab buildings/rooms + rename `locations`→`addresses` — [ideas/lab-locations.md](../ideas/lab-locations.md) |
| Parser keyed only by **instrument_type** | Out of scope this cycle; parsers/runs use **instance** (type available via join) |

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| `instrument_types` | Lab-global config | Lab config roles; not client-writable |
| `instruments` | Lab-global config | Same; instances of types |
| `cro_sources` | Lab-global config | Same as instruments |
| `instrument_parsers` | Lab-global config | Same; client roles cannot mutate |
| `parser_setup_files` | Lab-global / owned via parser | Same posture as parsers |
| `lims_run_imports` | Via parent run RLS | Same access as lims_run / run data |
| `lims_run_data.import_id` | Existing run data RLS | |

**Multi-tenant / org segregation:** out of scope — [ideas/multi-tenant.md](../ideas/multi-tenant.md). Do not add tenant keys “for later” in this feature.

## 4. Data migration / backfill

**Context:** NimbleLIMS is **pre-release**. Do **not** design a multi-step production switchover, dual-write window, or long dual-path import. Chunk work by **phase (P0/P1/P2)**; keep migrations simple.

- [x] New catalogs and `parser_setup_files` start empty (or only what setup creates)  
- [ ] **Existing template-scoped `instrument_parsers` rows:** **delete** (or one-shot re-create under analysis×source if we care about a specific env) then **DROP `experiment_template_id`**  
- [x] **No dual-write**, no “legacy fallback” import path after cutover  
- [x] **Import** only via `run.parser_id` / analysis×source default  

**SOP parse (app):** stop creating template-linked parsers; protocol template only or future analysis×source path.

## 5. Rollback

- Forward migrations preferred; pre-release envs can rebuild DB if needed.  
- Soft-delete via `active=false` for catalogs/parsers once data is real.

## 6. Explicitly out of scope (this cycle)

Do **not** change as part of data-parsers P0/P1:

| Area | Why |
|------|-----|
| `results`, `tests`, promote columns | Shipped in run-results |
| `analyte_aliases` | Shipped |
| Field Management / dynamic schema product (`design/schema-evolution.md`) | Separate workstream |
| `experiment_templates` structure | Unchanged (still used for protocol/lifecycle on the **run**) |
| Parser ↔ template link | **Removed** — not “nullable legacy” |
| Executable parser storage | Forbidden |
| **Multi-tenant / org segregation** | **Out of scope** — [ideas/multi-tenant.md](../ideas/multi-tenant.md) |

## 6b. Multi-tenant readiness (not implementation)

**Now:** single-lab, **lab-global** catalogs (`instruments`, `cro_sources`, parsers, setup files). No `tenant_id` / `org_id` columns this cycle.

**Goal of readiness:** later multi-tenant should be an **additive** change (column + unique/RLS), not a rewrite of import/promote.

| Do (cheap readiness) | Do not (over-design) |
|----------------------|----------------------|
| UUID PKs; soft `active` | Nullable `tenant_id` with all nulls “for later” |
| Clean FKs: instrument/cro → parser → run | Dual code paths `if multi_tenant` |
| Unique `name` simple for one lab; note future `(tenant_id, name)` | Partial unique indexes on null tenant |
| App: resolve parser by analysis×source, not “global magic” | Per-org admin UX now |
| Optional `cro_sources.client_id` as **label** only (not security tenancy) | Using client_id as tenant wall without a multi-tenant design |
| Client roles cannot mutate lab config | Fake multi-tenant RLS policies |

**When multi-tenant ships:** likely add tenant/org scope to these tables, change uniques to per-tenant, RLS by tenant. Document that work under a future multi-tenant requirements/schema-changes cycle—not as dual-write in P0/P1.

## 7. Open schema blockers

| ID | Topic | Blocks |
|----|--------|--------|
| Q2 | Instrument type vs instance | **Decided:** type (vendor/model) + instance (serial); no location FK |
| Q7 | Multi-tenant catalogs | **Decided: lab-global; multi-tenant OOS** — ideas/multi-tenant.md |
| Q9 | Keep table name `instrument_parsers` | Naming only |
| #10a | Persist setup files? | **Decided: yes** — `parser_setup_files` in P1 |
| Q5 | parser_config snapshot on run | Defer until multi-user production need |

Product: CEO locked analysis×instrument/CRO scope (Decision #11). Architecture to approve this delta list.

## 8. Implementation checklist

- [ ] Migration(s) match this doc  
- [ ] SQLAlchemy models match migration  
- [ ] RLS policies documented and tested  
- [ ] ParserConfig v1 validated in app (not a DB constraint)  
- [ ] This file updated with Alembic revision id(s)  
- [ ] Import resolution uses `lims_runs.parser_id`  

## 9. App-level contract (not DB, but schema-adjacent)

Stored in `instrument_parsers.parser_config` JSONB; **validated by Pydantic**, not CHECK JSON:

- `schema_version`, `delimiter`, `encoding`, `skip_rows`, `header_row`, `columns[]`, `well_col`, `sample_col`  
- See tech sketch §5 and open-questions Decision #1  

DB does not enforce JSON shape beyond JSONB type.
