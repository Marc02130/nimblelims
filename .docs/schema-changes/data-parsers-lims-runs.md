# Schema changes: data-parsers-lims-runs

**Feature / cycle:** Data parsers, instruments/CRO sources, LimsRun lineage  
**Phases covered:** **P0 + P1** (P2 AI = no extra schema beyond setup files already in P1)  
**Status:** Schema **accepted** by architecture (2026-07-19 Accept with conditions); **`data_parsers`**, versioning + active; pre-release  
**Alembic revisions:** `0054` (P0 catalogs); `0055` (P1 data_parsers rename/versioning, parser_analyses, setup files, lims_run_imports)  
**Requirements:** [../requirements/data-parsers-lims-runs.md](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [../tech-sketch/data-parsers-lims-runs.md](../tech-sketch/data-parsers-lims-runs.md)  
**Architecture review:** [../architecture-review/data-parsers-lims-runs.md](../architecture-review/data-parsers-lims-runs.md)  
**Open questions:** [../open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md)

> **This is the authoritative schema delta for this cycle.** Architecture review of “what changes in the DB” should use **this file**, not a full read of the packet.

## 1. Summary

Add **instrument types** + **instances**; **CRO sources**; **RENAME `instrument_parsers` → `data_parsers`**; re-scope to **instrument instance XOR CRO** with **version_group_id + version + active**; **many-to-many `parser_analyses`**; **DROP `experiment_template_id`**; **`lims_run_imports`**. Run still has one **`analysis_id`**. No lab location this cycle.

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| **`instrument_types`** | Vendor/model class (what the box *is*) | `id`, `name` (e.g. display label), `vendor` NULL, `model` NULL, `description` NULL, `active`, audit cols |
| **`instruments`** | **Instance** of a type (which physical unit / named stream) | `id`, **`instrument_type_id` NOT NULL** → `instrument_types`, `name` (lab nickname), **`serial_number` NULL**, `description` NULL, `active`, audit cols — **no location_id** this cycle |
| **`cro_sources`** | External/CRO export-source catalog | `id`, `name`, `description` NULL, `client_id` NULL → `clients`, `active`, audit cols |
| **`parser_setup_files`** | Persisted example / test / edge fixtures for parser setup | `id`, `parser_id` FK → **`data_parsers`**, `role` (`example`\|`test`\|`edge_fixture`), `filename`, `content_type`, `size_bytes`, storage, `created_by`, `created_at` |
| **`parser_analyses`** | **M2M:** which analyses a parser may serve | `parser_id` → **`data_parsers`**, `analysis_id`, `is_default`, PK (`parser_id`, `analysis_id`) |

**Instrument vs type**

| Entity | Holds | Example |
|--------|--------|---------|
| **Type** | vendor, model | Agilent 6495C |
| **Instance** | type FK, serial, lab name | “LCMS-1”, serial `US123456` |

**Location:** Do **not** FK instruments → client **`locations`**. That table should become **`addresses`** (rename idea). Lab **buildings/rooms** → [ideas/lab-locations.md](../ideas/lab-locations.md). No instrument location this cycle.

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| **`instrument_parsers`** | **RENAME → `data_parsers`** | Decision #9 — generic name (instrument + CRO) |
| **`data_parsers`** | **DROP `experiment_template_id`** | Not template-scoped |
| **`data_parsers`** | ADD `instrument_id` UUID NULL → **`instruments`** | Lab path (instance) — **no `analysis_id` on parser row** |
| **`data_parsers`** | ADD `cro_source_id` UUID NULL → `cro_sources` | CRO path |
| **`data_parsers`** | ADD **`version_group_id`** UUID NOT NULL | Logical parser identity shared by all versions |
| **`data_parsers`** | ADD **`version`** INT NOT NULL | Monotonic per group (1, 2, 3…); first version = 1 |
| **`data_parsers`** | ADD/keep **`active`** BOOLEAN NOT NULL DEFAULT false | **This version** is current production for the group; at most one `active=true` per `version_group_id` |
| **`data_parsers`** | `parser_config` JSONB | ParserConfig v1 for **this version only**; **immutable after insert** (updates → new version row) |
| **`lims_runs`** | *(optional)* last_* denorm for UI | Lineage via **`lims_run_imports`** |
| **`lims_run_data`** | ADD `import_id` UUID NULL → `lims_run_imports` | Row-level lineage |

**Versioning rules (app + constraints):**

1. **Create** → insert version row (`version=1`, usually activate).  
2. **Update** → **insert** new row same `version_group_id`, `version = max+1`, new `parser_config` / links — **never UPDATE `parser_config` in place**.  
3. **Activate** (prompt on save) → set new row `active=true`; set all other rows in group `active=false`.  
4. **Import** stores `parser_id` = **specific version** PK. Resolve defaults / pickers from **`active=true` only**.  
5. **No** `parser_config_snapshot` on imports or runs.

### 2.1b Import events + parser↔analysis M2M

| Table | Purpose | Key columns |
|-------|---------|-------------|
| **`parser_analyses`** | **Many-to-many:** parser ↔ analyses | `parser_id`, `analysis_id`, **`is_default`** (default for this analysis when using this parser’s instrument/CRO) |
| **`lims_run_imports`** | One import file/batch on a run | `id`, `lims_run_id`, `instrument_id`\|`cro_source_id`, **`parser_id`** (specific **version** row), `imported_at`, `imported_by`, filename optional — **no config snapshot column** |

`lims_runs.analysis_id` — **required on the run** (Decision #6 — no non-reportable path; target **NOT NULL**). What the run **stores/promotes** (e.g. RCRA-8 only).  
`lims_runs.experiment_template_id` — **unchanged**.

**Product:**

| Concept | Example |
|---------|---------|
| **Parser / instrument** | Metals ICP file maps **all** metal columns the instrument reports |
| **Run analysis** | RCRA-8 or RCRA-13 — promote only **relevant** analytes for that analysis |
| **M2M** | Same ICP parser linked to **both** RCRA-8 and RCRA-13 |
| **Import** | Run analysis = RCRA-8; instrument = ICP-1; parser must be linked to RCRA-8 **and** match ICP-1 |

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| **`data_parsers` source CHECK** | Exactly one of `instrument_id` / `cro_source_id` non-null | Lab XOR CRO |
| **`data_parsers` version unique** | UNIQUE (`version_group_id`, `version`) | One row per version number in a group |
| **At most one active per group** | Partial unique: UNIQUE (`version_group_id`) WHERE `active` | Only one production version |
| **`parser_analyses` PK** | (`parser_id`, `analysis_id`) | M2M **per version row** |
| **`parser_analyses` FK** | → parsers, analyses | Integrity |
| **Default uniqueness** | App-enforced among **active** versions: at most one `is_default` per (analysis_id, instrument_id\|cro_source_id) | Join parsers ↔ parser_analyses WHERE active |
| **`lims_run_imports` source CHECK** | Exactly one of instrument / cro | Same as parsers |
| Drop | `experiment_template_id` indexes/FKs | Column drop |
| Indexes | type, instance, version_group_id, parser_analyses, import FKs | Lookup |
| Optional unique | `instruments (instrument_type_id, serial_number)` WHERE serial not null | Serials |

**App integrity on import:**

```
run.analysis_id = A
import uses instrument I (or CRO C) and parser P

Required:
  EXISTS parser_analyses(P, A)
  P.instrument_id = I   (or cro_source_id = C)
```

**Promote:** only maps columns that resolve to analytes **on analysis A** (extra metals in row_data stay in JSONB / unresolved for that analysis—not forced into Results).

**Capability:** instrument usable for analysis A ⇔ an **`active`** version of a parser for that instrument with row in `parser_analyses` for A.

### 2.4 Enums / types

| Type | Change |
|------|--------|
| — | **None** this cycle |

### 2.5 Optional / not MVP (later — not P0/P1)

| Object | Notes |
|--------|-------|
| Import-time `parser_config_snapshot` JSONB | **Rejected** (Decision #5) — use versioned parser rows instead |
| Dual-write / gradual production cutover of template parsers | **Out of scope** — pre-release; simple migrate-or-delete |
| **`instruments.room_id` / location** | Lab buildings/rooms + rename `locations`→`addresses` — [ideas/lab-locations.md](../ideas/lab-locations.md) |
| Parser keyed only by **instrument_type** | Out of scope this cycle; parsers/runs use **instance** (type available via join) |

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| `instrument_types` | Lab-global config | Lab config roles; not client-writable |
| `instruments` | Lab-global config | Same; instances of types |
| `cro_sources` | Lab-global config | Same as instruments |
| `data_parsers` | Lab-global config | Same; client roles cannot mutate |
| `parser_analyses` | Lab-global | Same |
| `parser_setup_files` | Lab-global / owned via parser | Same posture as parsers |
| `lims_run_imports` | Via parent run RLS | Same access as lims_run / run data |
| `lims_run_data.import_id` | Existing run data RLS | |

**Multi-tenant / org segregation:** out of scope — [ideas/multi-tenant.md](../ideas/multi-tenant.md). Do not add tenant keys “for later” in this feature.

## 4. Data migration / backfill

**Context:** NimbleLIMS is **pre-release**. Do **not** design a multi-step production switchover, dual-write window, or long dual-path import. Chunk work by **phase (P0/P1/P2)**; keep migrations simple.

- [x] New catalogs and `parser_setup_files` start empty (or only what setup creates)  
- [ ] **Existing template-scoped parser rows:** **delete** (or one-shot re-create) then **RENAME → `data_parsers`**, **DROP `experiment_template_id`**  
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
| — | **None for product** (2026-07-19) | Architecture re-accept of full delta |

Closed: Q1–Q9, #10a–d, #11–17 as applicable. Reviews **Accepted** 2026-07-19 (Architecture conditions A1–A7).

Product: analysis×instrument/CRO (M2M), `data_parsers`, versioning, analysis required.

## 8. Implementation checklist

- [x] **P0** Migration `0054` — instrument_types, instruments, cro_sources  
- [x] **P0** SQLAlchemy models + API + admin UI (config:edit)  
- [x] **P0** RLS lab-global (`is_admin() OR active`)  
- [x] **P1** Migration `0055` — data_parsers rename/versioning, parser_analyses, setup files, lims_run_imports  
- [x] ParserConfig v1 validated in app (`extra=forbid`; engine delimiter/encoding)  
- [x] Import resolution uses **active** version; stores version `parser_id` on import  
- [x] Parser “update” = new version; activate deactivates prior in group  
- [x] Table/model/API **`data_parsers`** / `DataParser` / `/v1/data-parsers`  
- [x] analysis_id required on create/start/import/publish (app-enforced)  

## 9. App-level contract (not DB, but schema-adjacent)

Stored in `data_parsers.parser_config` JSONB; **validated by Pydantic**, not CHECK JSON:

- `schema_version`, `delimiter`, `encoding`, `skip_rows`, `header_row`, `columns[]`, `well_col`, `sample_col`  
- See tech sketch §5 and open-questions Decision #1  

DB does not enforce JSON shape beyond JSONB type.
