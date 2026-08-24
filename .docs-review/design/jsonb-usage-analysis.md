# JSONB Field Usage Analysis

**Date:** 2026-06-30  
**Branch:** refactor/jsonb  
**Context:** Part of the broader experiment/process and data model refactor.

## Overview

NimbleLIMS makes extensive use of PostgreSQL `JSONB` columns to provide flexibility. This document catalogs all significant JSONB usages, assesses whether each is a good fit, identifies suboptimal uses, and provides pros/cons for retaining JSONB on a per-field (or per-pattern) basis.

JSONB is powerful for:
- Rapidly evolving or highly variable data
- Avoiding expensive schema migrations
- Storing semi-structured configuration or instrument output

However, it can become a liability when:
- Data has predictable structure that users want to query/report on
- Strong typing, constraints, or referential integrity would be valuable
- Performance of JSON path queries becomes a bottleneck

## Complete Inventory of JSONB Columns

| Entity/Table                  | Column                  | Purpose                                      | Typical Contents                              | Indexed? | Assessment     |
|-------------------------------|-------------------------|----------------------------------------------|-----------------------------------------------|----------|----------------|
| Analysis                      | custom_attributes       | EAV for lab-defined fields                   | key → value (mixed types)                     | No       | Mixed          |
| Analyte                       | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| Batch                         | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| Client                        | billing_info            | Opaque billing data                          | Provider-specific billing details             | No       | Good           |
| Client                        | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| CustomAttributesConfig        | validation_rules        | Rules for custom attribute (type, range, etc)| JSON schema-like object                       | No       | Suboptimal     |
| Experiment                    | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| ExperimentDetail              | content                 | Protocol steps, notes, links, conditions     | Free-form structured data                     | GIN      | Mixed          |
| ExperimentDetail              | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| ExperimentSampleExecution     | processing_conditions   | Per-sample conditions in an experiment       | e.g. { "temperature": 37, "media": "..." }    | GIN      | Suboptimal     |
| ExperimentSampleExecution     | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| ExperimentTemplate            | template_definition     | Protocol structure, plate layout, entries    | Complex nested object (steps, wells, etc.)    | GIN      | Mixed          |
| ExperimentTemplate            | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| InstrumentParser              | parser_config           | Column mapping rules for instrument files    | Array of {source_col, field_name, data_type}  | GIN      | Good           |
| Project                       | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| Result                        | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| RobotWorklistConfig           | worklist_config         | Source/dest/volume mappings for robots       | Steps with source/dest/volume columns         | GIN      | Good           |
| Sample                        | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| SopParseJob                   | result                  | Extracted template/parser/worklist from AI   | Nested template_definition + configs          | No       | Good           |
| Test                          | custom_attributes       | EAV                                          | key → value                                   | No       | Mixed          |
| WorkflowTemplate              | template_definition     | Sequence of workflow actions                 | { "steps": [ { "action": "...", "params": ... } ] } | GIN | Good (mostly) |
| WorkflowInstance              | runtime_state           | Live context/state during workflow execution | Arbitrary context dict                        | No       | Good           |
| ExperimentData                | row_data                | Raw instrument row after parsing             | Instrument-specific columns                   | GIN      | Good           |

## Detailed Assessment of Suboptimal Uses

### 1. `custom_attributes` (across ~10 tables)

**Current State:** Ubiquitous EAV pattern. Used for almost every major entity.

**Why Suboptimal in Many Cases:**
- Most "custom" fields end up being the same across similar entities (e.g. "lot_number", "expiry_date" on samples).
- Querying is cumbersome (`WHERE custom_attributes->>'lot_number' = 'ABC'`).
- No database-level constraints or foreign keys.
- Reporting and filtering in the UI becomes inconsistent.
- Migration path when a field becomes "core" is painful (data must be moved out of JSONB).

**Better Alternatives:**
- Typed attribute definition system (already partially present via `custom_attributes_config`).
- Promote frequently used fields to real columns over time.
- Use a proper EAV table with `attribute_id`, `entity_id`, `value_type`, and typed value columns.

### 2. `content` in `ExperimentDetail`

**Usage:** Stores protocol steps, conditions, `experiment_link` references, free-form notes.

**Suboptimal Aspects:**
- Mixes very different concerns in one column (structured protocol vs. ad-hoc notes vs. links).
- `experiment_link` is particularly bad — it should be a proper junction or part of a Process model.
- Hard to enforce structure or validate expected shapes.

**Recommendation:** Split into typed detail rows or use the new "Entries" model being designed for experiments.

### 3. `processing_conditions` in `ExperimentSampleExecution`

**Usage:** Captures per-sample processing parameters during an experiment.

**Why Suboptimal:**
- Data is often semi-structured and queryable (temperature, volume, time, etc.).
- Being inside JSONB makes it difficult to do aggregate queries or link to units.
- In a LIMS, this data frequently needs to be reported or used in calculations.

**Recommendation:** Consider a dedicated `sample_execution_conditions` table or move common fields to real columns + JSONB only for truly exotic values.

### 4. `validation_rules` in `CustomAttributesConfig`

**Usage:** Defines rules for user-defined attributes.

**Problem:** The rules themselves are stored as opaque JSONB while the attributes they govern are also in JSONB. This creates a double layer of indirection with very little type safety.

This is a meta-level configuration that would benefit from a more structured schema.

### 5. `template_definition` in `ExperimentTemplate`

**Current State:** Contains a mix of:
- Structured protocol steps
- Plate layout (partially moved to `template_well_definitions` in 0043)
- Transfer steps
- Result column definitions
- `mandatory_review_count`

**Assessment:** Mixed. The migration of plate layout to relational tables was the right call because the data needed to be queryable.

Remaining structure is still mostly treated as a black box by the backend (loaded entirely into memory).

Suboptimal when the app needs to query "all templates that use a certain transfer step" or validate structure at the database level.

## Pros and Cons of Keeping JSONB (Per Major Pattern)

### Pattern: `custom_attributes`

**Pros of Keeping as JSONB**
- Maximum flexibility — users can add arbitrary fields without migrations.
- Simple implementation (one column for all custom data).
- Works across all entity types with the same code path.
- Fast to add new fields during development.

**Cons of Keeping as JSONB**
- Poor query performance for anything beyond simple equality on small datasets.
- No constraints (uniqueness, foreign keys, ranges).
- Inconsistent data shapes across records.
- Difficult to index efficiently at scale.
- Reporting and export tools struggle.
- Future refactoring (promoting a field to a real column) requires data migration scripts.

### Pattern: Instrument / External Data (`row_data`, `parser_config`, `worklist_config`, `result`)

**Pros**
- Instrument output is inherently variable per device/vendor.
- External AI output (SopParseJob.result) has unpredictable structure.
- GIN indexes provide reasonable performance for the access patterns used today.
- Avoids constant schema churn as new instruments are added.

**Cons**
- Still requires application-level schema (the parser_config defines the expected shape).
- Difficult to evolve the stored data shape over time.
- Limited ability to do cross-run analytics on the raw data.

**Verdict:** Generally appropriate. Only move to relational if specific analytical needs arise.

### Pattern: Process/Protocol Definitions (`template_definition`, `content`, `worklist_config`)

**Pros**
- Allows rich, nested structures (steps, conditions, layouts) without dozens of tables.
- Easy to version the entire definition as one blob.

**Cons**
- Structure is enforced only in Python (Pydantic models exist for some, not all).
- Hard to query "which templates use this particular action/condition".
- Changes to the expected shape require careful migration of existing JSON.

**Verdict:** Reasonable for the top-level definition, but sub-structures that need querying (e.g. wells, transfers) should be normalized (as was done for wells).

### Pattern: Runtime / State Data (`runtime_state`, `processing_conditions`)

**Pros**
- Can capture whatever the workflow or experiment needs at runtime.
- Flexible for future workflow actions.

**Cons**
- `processing_conditions` is often treated as structured scientific data, not opaque runtime state.
- Loses the ability to do efficient joins or aggregates.

**Verdict:** `runtime_state` is probably fine. `processing_conditions` is a candidate for normalization.

## Recommendations

**Key decisions (2026-06-30):**
- **Custom attributes** as an extensibility mechanism is being retired.
- We are doing a **hard cutover** (not long dual-write) when migrating data out of custom_attributes JSONB.
- **JSONB is restricted to Out-Of-Box (OOB) unstructured data only**. There will be no UI allowing users or admins to define new unstructured fields for extensibility.

1. **Keep JSONB** only for OOB cases:
   - Raw instrument output (`row_data`)
   - External opaque payloads (`billing_info`, AI extraction results)
   - Core OOB configuration (`template_definition`, `parser_config`, `worklist_config`, `runtime_state`)

2. **Refactor away from JSONB** for extensibility:
   - All `custom_attributes` → move to FieldDefinition + real columns / typed storage.
   - `processing_conditions`
   - `content` (especially links and structured protocol data)
   - `validation_rules`

3. **Long-term model**:
   - FieldDefinition for all modeled/scalar/list extensions.
   - Entries (in Experiments/Processes) built on top of FieldDefinitions for their columns.
   - JSONB only for the OOB unstructured cases listed above.

---

This document should serve as input for the JSONB refactor work. Each suboptimal field should be evaluated individually during the design of the new "Entries" and attribute systems.

## Recommended Refactor Order

Based on impact, risk, and dependencies, the following order is recommended for refactoring JSONB usage:

1. **Build foundational schema management capabilities first**
   - Enhance or replace the existing `custom_attributes_config` system with a proper `AttributeDefinition` / `EntryDefinition` model.
   - Add support for list-backed fields (e.g., referencing `list_entries` like `specimenbiotype`).
   - Create admin UI for defining new attributes/columns (type, required, list source, validation).
   - Implement safe migration primitives (add column, deprecate column, add table with data migration hooks).

2. **Address highest-pain custom_attributes**
   - Start with high-volume, frequently queried entities: `Sample`, `Project`, `Batch`, `Test`.
   - Promote common fields out of JSONB into real columns or typed attribute tables.
   - Provide data migration scripts + dual-read/write period for backward compatibility.

3. **Refactor Experiment/Process data capture**
   - Move from loose `ExperimentDetail.content` + JSONB to the new Entries system (as described in related design docs).
   - Normalize `processing_conditions` where possible.
   - Ensure template-driven column definitions are supported.

4. **Clean up configuration and protocol JSONB**
   - `template_definition` (ExperimentTemplate, WorkflowTemplate): Keep top-level structure as JSONB but normalize sub-structures that need querying (wells already done; consider transfers, entries).
   - `parser_config`, `worklist_config`: Keep as JSONB (good fit) but add stricter JSON Schema validation at write time.
   - `validation_rules`: Evolve toward structured definitions in the attribute system.

5. **Handle runtime/state JSONB**
   - `runtime_state` (WorkflowInstance): Keep as flexible JSONB with versioning.
   - Review `content` in details and `row_data` for any normalization opportunities (raw data usually stays JSONB).

6. **Deprecation and cleanup**
   - Remove dual-write paths.
   - Drop unused JSONB columns after migration windows.
   - Update reporting, search, and UI layers to use structured fields.

7. **Advanced / future**
   - Full user-driven schema extension with safe, auditable migrations.
   - Support for adding entirely new tables via UI (with generated models/migrations if possible, or dynamic tables).

**Risk mitigation notes:**
- Always maintain a migration window with dual storage where data moves between JSONB and structured columns.
- Prioritize entities that block reporting or workflow improvements.
- Leverage the existing lists system for new "list" type columns to avoid reinventing controlled vocabularies.