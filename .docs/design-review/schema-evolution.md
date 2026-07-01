# Design Review: Schema Evolution System

**Date:** 2026-06-30  
**Reviewer perspective:** Based on current codebase, existing docs, user feedback on Experiments/Processes, and JSONB analysis.

## 1. Summary of Proposed Design

The design introduces a `FieldDefinition` / schema registry layer on top of the existing custom attributes and lists infrastructure. Key ideas:

- Admin-driven addition of properly typed columns (especially list-backed like `specimen_biotype`).
- Generation of safe Alembic migrations.
- Gradual migration out of JSONB for structured data.
- Support for deprecation and (limited) new table creation.
- Integration with the emerging Entries model for Experiments and Processes.

Overall direction is sound: move from "everything in JSONB" toward controlled extensibility.

## 2. Strengths

- Builds on existing patterns (lists, custom_attributes_config, EAV lessons).
- Addresses real pain points identified in the JSONB analysis.
- Supports the user stories for adding list columns, removing columns, and adding tables.
- Phased approach reduces risk.
- Acknowledges the need for dual-write/migration windows.

## 3. Issues and Risks That Need to Be Addressed

### 3.1 Data Model and Naming

**User decisions (2026-06-30):**
- We will use **FieldDefinition** terminology.
- We will **remove the "custom attributes" concept** entirely for extensibility.
- **JSONB will not be used to extend functionality.** It is restricted to Out-Of-Box (OOB) unstructured data only. There will be **no UI** for defining new unstructured fields.
- We are planning a **hard cutover** (not a prolonged dual-storage period) when migrating away from custom_attributes.

**Issue:** Proliferation of similar concepts.
- We already have `custom_attributes_config`, `list_entries`, `ExperimentDetail`, `ExperimentSampleExecution`, and proposed `FieldDefinition` + `ProcessSample`.
- Risk of confusion between "custom attributes", "field definitions", "entries", and "process samples".

**Recommendation (updated):** 
- Use **FieldDefinition** as the canonical term for all modeled extensibility.
- Retire "custom attributes" completely as an extension mechanism.
- JSONB strictly limited to OOB unstructured data (no UI for defining new unstructured extensibility).
- Hard cutover (not gradual dual-write) when moving data out of custom_attributes.
- Full glossary + relationship explanation is in `.docs/design/schema-evolution.md`.

**FieldDefinition vs Entry relationship (clarified):**

- **FieldDefinition** = the atom. It defines a single typed field (e.g. `specimen_biotype` as a list, or `concentration` as a number, or a custom column inside a data table).
- **Entry** = the molecule. It is a richer construct inside an Experiment or Process step.
  - A predefined Entry (OOB) is a behavior + possibly some fields (e.g. "Aliquots" action entry, "QC Review" pass/fail entry).
  - A custom Sample data entry or Experiment detail entry is essentially a table whose columns are defined by FieldDefinitions (the columns are declared in the template).
- So: Entries can *contain* FieldDefinitions (for their columns), but FieldDefinitions can also stand alone as top-level fields on entities (like adding specimen_biotype directly to Sample).

This separation keeps scalar/list extensions clean while allowing richer, template-defined data structures inside experimental work.

### 3.2 Scope of "Add Table" Feature

**Issue:** The design mentions generating tables and basic CRUD. This is powerful but dangerous if not tightly scoped.
- Will users be allowed to add tables that participate in Processes or link to Runs?
- Foreign key and RLS complexity explodes quickly.
- Generated models can drift from hand-written ones.

**Risk:** Feature creep into a full low-code platform without the supporting governance.

**Recommendation:** 
- Limit v1 "add table" to read-only supporting entities or very simple child tables.
- Make table creation require a higher privilege + explicit approval step.
- Generate only the schema + basic admin views; require developer involvement for integration with core workflows.

### 3.3 Migration Safety and Downtime

**Issue:** Even with "nullable first", adding columns to high-volume tables (`samples`, `results`) can cause table locks or bloat in PostgreSQL under load.

**Gaps:**
- No mention of `CREATE INDEX CONCURRENTLY`, online schema change tools, or zero-downtime strategies.
- Backfill jobs for existing data are mentioned but not designed (locking, batch size, failure handling).

**Recommendation:** Define a concrete migration playbook and tooling (perhaps a `schema_migrate` management command with dry-run, batching, and progress).

### 3.4 RLS and Multi-Tenancy Implications

**Issue:** New columns and especially new tables must not accidentally bypass client isolation.
- Current RLS is heavily based on `created_by` → client or project membership.
- A dynamically added column on `samples` is relatively safe if the base table policies remain.
- A new table requires new policies or inheritance rules.

**Gap:** The design does not specify how RLS policies are generated or validated for new schema elements.

**Recommendation:** 
- Default new columns to "inherit parent RLS".
- For new tables, require explicit policy definition as part of the creation wizard.
- Add automated tests that new schema elements do not leak data across clients.

### 3.5 Interaction with Current Experiment / Process Design

**Issue:** The schema evolution design and the Process/Entries work are being developed in parallel but have dependencies.

- Can a "specimen_biotype" added to Samples be automatically available as a column in sample data entries inside Experiments?
- How do Process-level fields interact with per-experiment entries?
- When a Process queues a sample into an experiment, do newly added fields on the sample become part of the entry data automatically?

**Recommendation:** Explicitly model how dynamically added fields surface inside the Entries system. Add this as a requirement in both design documents.

### 3.6 Validation and Type System

**Issue:** `validation_rules` is currently JSONB. The new system should not replicate the same problem at a higher level.

- Need a proper typed definition for validation (not another blob).
- Cross-field and cross-table validation will be requested quickly.

**Recommendation:** Define a small, versioned validation language or reuse something like JSON Schema with a strict subset. Avoid open-ended JSONB for the rules themselves.

### 3.7 Code Generation vs. Purely Dynamic

**Issue:** Tension between:
- Fully dynamic UI + models (fast but can hide complexity, harder to debug).
- Code generation (more maintainable long-term but requires regeneration step).

Current codebase mixes both (some dynamic, lots of explicit models).

**Risk:** Inconsistent experience and maintenance burden.

**Recommendation:** 
- Use dynamic generation for admin preview and for truly user-defined supporting tables.
- For core entities (Sample, Experiment, etc.), generate the column addition but keep an explicit model update step (or use SQLAlchemy introspection carefully).
- Document the supported path clearly.

### 3.8 Impact on Existing Custom Attributes and JSONB

**Issue:** The design talks about "gradual migration" but does not define the user experience for fields that currently live in `custom_attributes`.

- Will admins see their old JSONB fields in the new schema admin?
- How do we prevent new work from going into JSONB while old data is still there?
- Dual storage increases complexity in queries and forms.

**Recommendation:** 
- Make the schema admin the single source of truth going forward.
- Provide a one-time "import existing custom attributes" tool that creates FieldDefinitions from current data shapes (best-effort).
- Add deprecation warnings in code paths that still write directly to `custom_attributes`.

### 3.9 Governance and Blast Radius

**Issue:** Who can add tables vs. columns? What is the approval process?

- Adding a column to Samples affects every accessioning workflow, every report, every client.
- Adding a table may have narrower impact.

Current permissions model (`config:edit`) may be too coarse.

**Recommendation:** Introduce finer-grained permissions (e.g., `schema:edit_column`, `schema:add_table`) and require review for high-impact changes.

### 3.10 Performance and Indexing Strategy

**Issue:** The design says "system suggests indexes". This needs to be concrete.

- For list-backed columns: usually a B-tree on the FK + possibly a partial index.
- For high-cardinality text fields: GIN or trigram.
- Adding many indexes has its own cost (write amplification, bloat).

**Recommendation:** Define a default indexing policy per data_type and require explicit opt-out + justification for high-impact tables.

## 4. Open Questions Highlighted by This Review

1. What is the exact boundary between "FieldDefinition" (scalar extensions) and the richer "Entry" concept inside Experiments/Processes?
2. How do we handle required fields on historical data (mandatory backfill vs. "applies only to new records")?
3. Should schema changes be versioned at the Process/Template level (i.e., a Process can pin a schema version)?
4. Long-term ownership: who maintains generated migrations and any generated UI code?
5. Integration depth with the R Calculator / dose-response pipeline (if new fields affect calculations).

## 5. Recommendations / Required Follow-ups

- Produce a small data model diagram showing FieldDefinition + how it maps to actual columns vs. entries.
- Define a minimal viable permissions model for schema changes before implementation.
- Create concrete examples for the specimenbiotype story end-to-end (migration + UI + sample write-back).
- Add explicit requirements for RLS generation/validation.
- Schedule a follow-up review focused on the migration safety playbook.

## 6. Overall Assessment

The direction is correct and addresses real needs. The main risks are scope creep on "add table", insufficient attention to RLS/migration safety in the current draft, and lack of tight integration specifications with the parallel Experiment/Process/Entries work.

With the issues above addressed, this is a viable foundation for the JSONB refactor.

---

**Related Documents**
- `.docs/design/schema-evolution.md`
- `.docs/requirements/schema-evolution.md`
- `.docs/user-stories/schema-modification.md`
- `.docs/jsonb-usage-analysis.md`
- `.docs/processes.md`
- `.docs/experiments.md`