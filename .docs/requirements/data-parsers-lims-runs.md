# Requirements: Data parsers, instruments/CRO sources, and LimsRun import

**Date:** 2026-07-12  
**Status:** **In review** — **CEO Accept** (2026-07-12); Security · Architecture · UI outstanding; tech sketch attached  
**Idea / direction:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Depends on (shipped):** [run-results](../ideas/run-results.md) promote-on-publish (`analysis_id`, analyte aliases, `ResultPromotionService`)  
**Related:** [manuals/lims-runs.md](../manuals/lims-runs.md), SOP parse (template-centric AI, separate)

## 1. Introduction

### 1.1 Problem

LimsRun import today depends on an **`InstrumentParser`** (table `instrument_parsers`) **tied to an experiment template**. Real labs and CROs need **`data_parsers`** (generic name) keyed by instrument or CRO:

- A **reusable, deterministic** way to turn instrument/CRO result files into `lims_run_data`  
- Scoping by **analysis + instrument** (in-house) or **analysis + CRO** (external)  
- **Lineage on the run** (which source and which parser were used) for troubleshooting  
- Optional **AI only at setup** to draft parser instructions from a sample text file—not on every import  

Promote-on-publish already maps JSONB columns → analytes/results when `analysis_id` is set. That path is stronger when import produces **stable field names** that match analyte names/aliases.

### 1.2 Goal

| Goal | Description |
|------|-------------|
| **G1** | Parsers are **first-class DB configs** (JSONB instructions), not custom code |
| **G2** | Parsers are keyed by **analysis + instrument** or **analysis + CRO source** |
| **G3** | Each LimsRun stores **instrument or CRO**, and **parser_id** (default + override) |
| **G4** | Day-to-day import is **deterministic** (no LLM) |
| **G5** | Optional AI **drafts** `parser_config` from an example text file; human saves |
| **G6** | Import and promote remain two clear stages (file→JSONB, JSONB→Results) |

### 1.3 Out of scope (this requirements set)

- Full equipment management (calibration, IQ/OQ, location, service history)  
- User-uploaded or generated executable parser code  
- AI inventing numeric results or auto-promoting without publish  
- Binary proprietary formats as MVP (XLSX may be a later phase)  
- Replacing SOP→template AI (that path remains template-centric)  
- Changing promote-on-publish product rules (already shipped)  
- **Multi-tenant / org segregation** of instruments, CRO sources, or parsers ([ideas/multi-tenant.md](../ideas/multi-tenant.md))

### 1.3b Multi-tenant readiness (consideration only)

NimbleLIMS is not implementing multi-tenant isolation in this cycle. Catalogs are **lab-global**.

**Do:** design instruments/CRO/parsers so a future tenant scope can be added without rewriting import/promote (UUID PKs, clear FKs, soft active, config not owned by lab-client users).  
**Do not:** add tenant columns, dual RLS paths, or org-scoped UX “for later” without a multi-tenant requirements cycle.

Optional `cro_sources.client_id` is a **label** (related client), not a tenant security wall.

### 1.4 Personas

| Persona | Needs |
|---------|--------|
| Lab manager / admin | Configure instruments, CRO sources, parsers once |
| Lab tech | On a run: set analysis + source, import file, publish |
| CRO workflow user | Same import path at `results_received`; source = CRO |
| Support / troubleshooting | See which parser/source a historical run used |

---

## 2. Definitions

| Term | Meaning |
|------|---------|
| **Instrument** | Light catalog entry for an in-lab data source (named instance or named export stream) |
| **CRO source** | Light catalog entry for an external lab/org export stream |
| **Parser** | DB row: scope (analysis + instrument\|CRO) + **`parser_config` JSONB** instructions |
| **parser_config** | Declarative instructions: delimiter, skip_rows, header, column map (`source_col` → `field_name`), etc. |
| **Generic parse engine** | Application code (`InstrumentDataService` or successor) that applies any `parser_config` to a file |
| **Default parser** | Preferred parser for a given analysis × source (when multiple exist) |
| **Run parser** | `lims_runs.parser_id` — the instructions used (or to be used) for that run’s import |

---

## 3. Functional requirements

### FR-1: Instrument types and instances (light)

| ID | Requirement |
|----|-------------|
| FR-1.1 | System shall support CRUD for **instrument types** with **vendor** and **model** (plus name/description/active). |
| FR-1.2 | System shall support CRUD for **instrument instances** with **FK to instrument type**, **name** (lab nickname), optional **serial number**, description, active. |
| FR-1.3 | Instruments are **lab configuration**, not full CMMS (no calibration/IQ-OQ this cycle). |
| FR-1.4 | **No location** on instruments this cycle. Existing `locations` is client address data—not lab rooms. Future: [ideas/lab-locations.md](../ideas/lab-locations.md). |
| FR-1.5 | Soft-deactivate preferred over hard delete when parsers/runs reference the instrument. |
| FR-1.6 | Parsers and lims_runs reference the **instance** (not the type). Type is available via join for display/AI context (vendor/model). |
| FR-1.7 | Permission: **`config:edit`** for instrument types/instances (and related config). |

### FR-2: CRO source catalog (light)

| ID | Requirement |
|----|-------------|
| FR-2.1 | System shall support CRUD for **CRO sources** (name, optional description, optional link to client/org, active). |
| FR-2.2 | CRO source is the external analogue of instrument for parser scoping and run lineage. |
| FR-2.3 | Soft-deactivate when referenced by parsers. |
| FR-2.4 | Same permission: **`config:edit`**. |

### FR-3: Parser as DB instructions (not code)

| ID | Requirement |
|----|-------------|
| FR-3.1 | A parser shall be stored as a database entity with **`parser_config` JSONB**—no per-source code modules or user scripts in v1. |
| FR-3.2 | `parser_config` shall be interpretable by a **generic** server-side engine (extend existing `InstrumentDataService` / `ParserConfig` schema). |
| FR-3.3 | Minimum instruction support: delimiter (tab/comma/semicolon/etc.), encoding, skip_rows / header_row, column mappings (`source_col`, `field_name`, `data_type`, optional `unit`), optional well_col / sample_col. |
| FR-3.4 | Parser shall be scoped to **exactly one** source: **instrument instance** XOR **CRO source** (file shape). |
| FR-3.5 | Parser shall link to **one or more analyses** via **`parser_analyses`** (M2M). Example: one metals ICP parser → RCRA-8 and RCRA-13. |
| FR-3.6 | Multiple parsers per (analysis, source) allowed; at most one **default** per (analysis, source) via `parser_analyses.is_default` among **active** versions. |
| FR-3.7 | Admin UI for parsers + multi-select analyses; no AI required for P1. |
| FR-3.8 | Parsers are **not** linked to experiment templates; **`experiment_template_id` removed**. |
| FR-3.9 | Parser config may map **all** instrument columns; **run.analysis_id** + promote determine which analytes become Results. |
| FR-3.10 | Parsers shall be **versioned**: each row is one version (`version_group_id`, `version`, `active`). |
| FR-3.11 | **Any update** to a parser definition creates a **new version row** — do **not** mutate `parser_config` (or definition) in place on an existing version. |
| FR-3.12 | On save of a new version, UI shall **prompt to make active**. If yes: activate new version and **deactivate** the previous active version in the same group. If no: new version stays inactive; prior active remains for imports. |
| FR-3.13 | Default resolution, capability, and pickers use **active** versions only. Historical imports keep their stored version `parser_id`. |
| FR-3.14 | **No** `parser_config` JSON snapshot on import or run — lineage is the version FK only. |

### FR-4: LimsRun tied to analysis; multi-instrument imports; valid parsers only

| ID | Requirement |
|----|-------------|
| FR-4.1 | **Every run has `analysis_id`** (required from create). No non-reportable / null-analysis path (Decision #6). |
| FR-4.2 | A run **may** perform **multiple imports** using **different instruments and/or CRO sources** (and thus different parsers). |
| FR-4.3 | Each import shall record **instrument XOR cro_source** and **`parser_id`** (e.g. `lims_run_imports` + optional `lims_run_data.import_id`). |
| FR-4.4 | Parser on an import **must** be linked to `run.analysis_id` via **`parser_analyses`** and match the import’s instrument/CRO. |
| FR-4.5 | UI shall only offer parsers for the selected instrument\|CRO that include **run.analysis** in their M2M links—not an arbitrary parser. |
| FR-4.6 | Instrument/CRO is eligible for a run’s analysis only if an **active version** of a parser for that source is linked to that analysis. |
| FR-4.7 | Import shall use the **stored import `parser_id`** (specific **version** row) — load that version’s config; no silent re-resolve; no config blob on the import. |
| FR-4.8 | UI shall show analysis on the run; import history shows instrument/CRO + parser **name + version** used per batch. |
| FR-4.9 | Optional: denormalize “last import” source/parser on the run for display only. |

### FR-5: Deterministic import on LimsRun

| ID | Requirement |
|----|-------------|
| FR-5.1 | Import remains allowed only in existing statuses (`running`, `results_received`). |
| FR-5.2 | Upload path: text table file → apply `parser_config` → preview optional → write `lims_run_data`. |
| FR-5.3 | No LLM call on import path. |
| FR-5.4 | Validation failures (missing expected fields, bad delimiter, etc.) shall be user-visible and actionable. |
| FR-5.5 | Integration with promote-on-publish: publish maps `field_name`/aliases → results for the run’s **required** `analysis_id`. |

### FR-6: Parser setup — multi-file examples, tests, and optional AI

User testing is part of the **parser framework**, not a separate product.

| ID | Requirement |
|----|-------------|
| FR-6.1 | When creating/editing a parser, user may upload **one or more example files** (text tables) used to derive/refine `parser_config`. Files are **persisted** (not session-only). |
| FR-6.2 | User may upload **one or more test files** used to validate a candidate config (may differ from examples). Files are **persisted**. |
| FR-6.3 | Framework shall run the **same import engine** against each test file with the candidate config (after schema validation—see open Q1). |
| FR-6.4 | UI shall show per-file results: pass/fail, row counts, warnings, hard errors. |
| FR-6.5 | **Activate version** (Decision #5 + #10c): **all** test and edge files must complete with **zero hard errors**. Activate deactivates the prior active version in the group. |
| FR-6.12 | Setup file caps (**#10b**): max **10 files**, max **10 MB per file** (examples + tests + edges combined unless product later splits pools). |
| FR-6.6 | Optional AI may draft `parser_config` from example file(s); **human must review and save**. |
| FR-6.7 | Optional AI may **suggest edge test cases** based on observed data (e.g. negative values, empties, type stress, structural noise); suggestions become fixtures only after user accepts. |
| FR-6.8 | Edge tests and all test files are judged by the **code engine**, not by the LLM alone. |
| FR-6.9 | AI shall not invent official result values or run on production LimsRun import. |
| FR-6.10 | Optional: AI may suggest analyte aliases (human confirm)—see [ai-analyte-resolution](../ideas/ai-analyte-resolution.md). |
| FR-6.11 | LLM path requires server credentials; degrade with clear error if missing. Async job pattern recommended (cf. SOP parse). |

### FR-7: Compatibility and migration

| ID | Requirement |
|----|-------------|
| FR-7.1 | **No template-scoped parsers** after cutover; import does **not** fall back to `experiment_template_id`. |
| FR-7.2 | Migration **renames** `instrument_parsers` → **`data_parsers`**, **drops** `experiment_template_id`; existing rows migrated or removed (see schema-changes). |
| FR-7.3 | SOP parse must **stop** creating template-linked parsers; parser setup uses the analysis×instrument/CRO flow (or SOP only fills protocol template). |

### FR-8: Permissions and audit

| ID | Requirement |
|----|-------------|
| FR-8.1 | Catalog and parser CRUD require **`config:edit`** (not lab client users). |
| FR-8.2 | Run field changes (analysis, source, parser) require run edit permissions consistent with existing LimsRun RBAC. |
| FR-8.3 | Import and parser CRUD actions are auditable (who, when, entity ids, including **new version** and **activate** events). |
| FR-8.4 | Instruments / CRO sources / parsers are **lab-global** config (not client-configurable). **Multi-tenant / org segregation is out of scope** — see [ideas/multi-tenant.md](../ideas/multi-tenant.md). |

### FR-9: Analysis required on every run (no non-reportable path)

| ID | Requirement |
|----|-------------|
| FR-9.1 | **No non-reportable runs** (Decision #6). `analysis_id` required on create/edit. |
| FR-9.2 | Start, import, and publish shall **reject** if `analysis_id` is null (no ack / continue-without). |
| FR-9.3 | Method-dev / scratch is **out of scope** until [lab projects](../ideas/orders-and-projects.md)—not solved by null analysis. |
| FR-9.4 | Target schema: `lims_runs.analysis_id` **NOT NULL** when implementation aligns with this lock. |

---

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Import performance suitable for multi-MB text files; no LLM latency on import. |
| NFR-2 | Parser JSON schema validated on save (reject invalid configs). |
| NFR-3 | Clean cutover: after migration, only analysis×source parsers; document handling of any pre-existing template-parser rows. |
| NFR-4 | Secrets: LLM keys only on backend env; never sent to client beyond job status. |
| NFR-5 | Clear separation in UX and API: setup vs import vs promote. |

---

## 5. Data model sketch (requirements-level)

```
instruments (id, name, vendor?, model?, description?, active, …)
cro_sources (id, name, description?, client_id?, active, …)

data_parsers (renamed from instrument_parsers — each row is one version)
  id, version_group_id, version, active   -- at most one active per group
  name, description
  instrument_id NULL | cro_source_id NULL  -- exactly one
  parser_config JSONB NOT NULL            -- immutable after insert
  -- NO analysis_id on row; NO experiment_template_id
  -- updates create new version; activate prompt deactivates prior

parser_analyses (M2M per version)
  parser_id, analysis_id, is_default
  -- e.g. ICP metals parser → RCRA-8 and RCRA-13

lims_run_imports
  lims_run_id, instrument_id|cro_source_id, parser_id (version row), …
  -- no parser_config snapshot

lims_runs
  analysis_id  -- which panel this run stores/promotes
```

---

## 6. Two mapping layers (must remain clear in UX/docs)

```
File column  --parser-->  row_data[field_name]  --promote-->  Result(analyte)
```

| Layer | Config | When |
|-------|--------|------|
| Parser | source_col → field_name | Import |
| Promote | field_name / alias → analyte | Publish if analysis_id set |

---

## 7. Phased delivery (recommended)

| Phase | Scope | AI | LimsRun |
|-------|--------|-----|---------|
| **P0** | Instrument + CRO source catalogs + UI | No | Optional FKs only if cheap |
| **P1** | Parser scoped analysis×source; **versioning + active**; manual editor; example/test dry-run; import stores **version** `parser_id` | No | **Yes** |
| **P2** | AI draft config from examples + **AI edge-test suggestions** | Yes | Setup only |
| **P3** | Richer formats, SOP bridge, alias co-suggest | Optional | Polish |

**Recommended first implementation branch:** P0+P1 (includes test harness without AI).  
**Second branch:** P2 (AI draft + edge suggestions).

---

## 8. Acceptance criteria (MVP = P0+P1)

1. Lab can create an instrument and a CRO source.  
2. Lab can create a parser for (analysis + instrument) and (analysis + CRO) with JSONB config via UI (no AI required) as **version 1**.  
3. Lab can attach **≥1 example file** and **≥1 test file** while creating/editing a parser.  
4. Framework runs engine on all test files and shows pass/fail/warnings per file.  
5. **Save of an edit creates a new version**; UI prompts **make active**; activating deactivates the prior active version.  
6. Only **active** versions appear as defaults/capability for new imports (provisional test gate before activate).  
7. On a LimsRun, user picks instrument/CRO; **default active parser_id** is applied and stored **per import**.  
8. User can override among active parsers for the pair; override is stored and used on import.  
9. Import loads config from the **stored version row** (no JSON snapshot); fails clearly if missing/invalid.  
10. Publish + promote still works when analysis_id set (existing behavior).  
11. Historical import shows instrument/CRO + parser **name + version**; reopening that version shows the config used then.

**P2 acceptance (when scheduled):**  
12. From example file(s) + analysis + source, AI produces draft parser_config; user must save as a version.  
13. AI suggests edge test fixtures from data (e.g. negatives); user accepts; engine re-runs tests.  
14. Production LimsRun import still never calls AI.

---

## 9. Open questions (for reviewers)

**Living log:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

| # | Question | Suggested default |
|---|----------|-------------------|
| **1** | How is AI/manual `parser_config` kept compatible with the import engine? | **Decided:** schema-first proposal accepted (Pydantic + JSON Schema; validate all writers; AI same schema) |
| 2 | Instrument type vs instance? | **Decided:** type (vendor/model) + instance (serial); see schema-changes |
| 3 | Permission for parser CRUD? | `config:edit` |
| 4 | Allow override to a parser from a different analysis? | No without strong warning / block |
| 5 | Snapshot vs versioning? | **Version + active**; no import JSON snapshot; updates create new versions |
| 6 | Non-reportable / null analysis import? | **Decided:** no non-reportable runs; require analysis; method-dev deferred to lab projects |
| 7 | Multi-tenant / org segregation? | **Out of scope** — lab-global config; [ideas/multi-tenant.md](../ideas/multi-tenant.md) |

---

## 10. Review packet (resubmitted with tech sketch)

| Doc | Location | Status |
|-----|----------|--------|
| Requirements | this file | **In review** |
| **Tech sketch** | [tech-sketch/data-parsers-lims-runs.md](../tech-sketch/data-parsers-lims-runs.md) | **Ready for review** |
| CEO / product | [ceo-review/data-parsers-lims-runs.md](../ceo-review/data-parsers-lims-runs.md) | Awaiting review |
| Security | [security-review/data-parsers-lims-runs.md](../security-review/data-parsers-lims-runs.md) | Awaiting review |
| Architecture | [architecture-review/data-parsers-lims-runs.md](../architecture-review/data-parsers-lims-runs.md) | Awaiting review |
| UI / UX | [ui-review/data-parsers-lims-runs.md](../ui-review/data-parsers-lims-runs.md) | Awaiting review |
| Open questions | [open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md) | Living |
| Idea | [ideas/ai-data-import.md](../ideas/ai-data-import.md) | Direction sketch |

**Gate:** Do not start P1 until CEO + Architecture blockers are **Decided** (or provisional defaults accepted) and developer has processed review verdicts. Security must accept trust boundaries before AI setup (P2) ships.
