# Security Review (CSO): Process and Experiment Plans

**Date:** 2026-07-09  
**Branch:** refactor/experiments  
**Reviewer:** CSO / Security  
**Scope:** Security implications of introducing Processes, ProcessSample, Entries, and related data flows. References: `.docs/manuals/experiments.md`, `.docs/manuals/processes.md`, `.docs/design/gap-analysis-process-and-experiment.md`, `.docs/requirements/experiment-processes-entries.md`, and existing RLS patterns in the codebase.

## Executive Summary

The proposed changes introduce several new security surfaces:

- New first-class entities (`Process`, `ProcessSample`, `entries`, `entry_field_*` tables)
- Sample write-back capability from inside experiment entries
- New authorization boundaries around process-level sample assignment and progression
- Potential for ordering and state changes that affect downstream integrity

**Positive notes:**
- The existing RLS discipline (client scoping, `is_admin()`, FORCE RLS on experiment tables) provides a strong foundation.
- Moving away from arbitrary JSONB in favor of FieldDefinitions + lists reduces injection and validation surface area.
- Audit fields are already planned on the new models.

**Critical Areas Requiring Attention (P1):**
1. RLS policies for all new tables must be designed and implemented before any data is created.
2. Write-back from Entries to core `Sample` attributes is a high-risk integrity and audit vector.
3. Naming collision between new ELN "Process" concepts and existing LIMS `experiment_processes` / `process_steps` creates risk of policy or query mistakes.
4. Migration path for existing `experiment_link` records must not create visibility or integrity gaps.
5. Clear ownership and consistency model between `ProcessSample` and `ExperimentSampleExecution`.

## Threat Model (STRIDE)

### Spoofing
- Attacker could attempt to advance samples in a process they shouldn't control.
- Mitigation: Strong `experiment:manage` (or finer-grained `process:*`) checks + RLS on assignment/queue actions.

### Tampering
- **High risk**: Write-backs to Sample attributes from multiple steps in a process.
  - Multiple users or steps updating concentration/volume could corrupt data.
  - Need: explicit conflict rules, last-writer-wins policy (or better: optimistic locking + audit), and authorization at the entry level.
- Tampering with process ordering or step membership.
  - Mitigation: Enforce ordering and membership integrity at the database level (FKs + unique constraints on sort_order per process) rather than only in application code.

### Repudiation
- **Medium-High risk**: Lack of specific audit for:
  - Sample assigned to / removed from Process
  - Sample advanced between steps
  - Entry value changes that trigger write-backs
- Current generic `created_by` / `modified_by` may be insufficient. Consider dedicated audit events or columns for process lifecycle actions.

### Information Disclosure
- **High risk area**: Process membership granting implicit access to contained Experiments and Samples.
  - Must define clear policy: Does being in a Process grant read access to all steps' data?
  - Risk of leaking sample data across clients/projects if RLS policies for `ProcessSample` are incorrect.
- Cross-process queries ("show me all samples currently in step X") must respect existing project/client boundaries.

### Denial of Service
- Long-running Processes with many samples could create expensive queries if not indexed properly.
- Concurrent advancement of the same sample in a process could cause race conditions or lock contention.

### Elevation of Privilege
- A user with access to one experiment in a process could affect data or state visible to others.
- Write-back capability could allow low-privilege users to mutate Sample records used by downstream tests or reporting.
- Process-level actions must not bypass per-experiment or per-sample permissions.

## Key Security Requirements

### 1. RLS Policies (P1)
All new tables must have RLS enabled with policies defined before migration.

Recommended approach:
- `Process` and `ProcessSample` should inherit client/project scoping from the samples and experiments they contain.
- A sample assigned to a Process should generally remain visible to users who could see it before assignment (do not expand visibility without explicit policy).
- Process membership should not automatically grant broader access than the user's existing project/client permissions.

Existing patterns to follow:
- `is_admin()` for full access
- Project-based sample access
- FORCE RLS on experiment engine tables (see 0041/0042)

New tables that will need policies:
- `processes`
- Junction for ordered steps
- `process_samples`
- `entries`
- `entry_field_definitions`
- `entry_field_values`

### 2. Write-Back Controls (P1)
Write-back from `sample_data` Entries to core Sample columns (e.g. `concentration`, `volume_ml`) is powerful but dangerous.

Requirements:
- Write-backs must be explicitly allowed per FieldDefinition or per entry type.
- Must be gated by experiment and/or process status (e.g., cannot write back from a completed or cancelled step).
- Full audit record (who, when, which entry/process/step, old value, new value).
- Conflict handling documented and implemented (e.g., "last write wins within a process" vs. "require manual resolution").
- Authorization check at the point of write-back, not just at entry creation.

### 3. Audit & Accountability
- Add or extend audit mechanisms for:
  - `assign_samples_to_process` / removal
  - `queue_sample_in_process_step`
  - `advance_sample_to_next_step`
  - Any entry change that triggers a write-back
- Consider adding a lightweight process-specific audit table or using the existing audit trigger pattern with additional context columns.

### 4. Naming & Isolation
- The term "Process" and "ProcessSample" collide with existing LIMS constructs (`experiment_processes`, `process_steps`).
- **Strong recommendation**: Use distinct naming in schema and code for the ELN side (e.g., `eln_processes`, `eln_process_samples`, or keep in a clearly separated module).
- This reduces the chance of accidentally applying the wrong RLS policy or joining the wrong tables.

### 5. Migration & Coexistence Risks
- Existing `experiment_link` records and sample executions must not become invisible or mutable in unexpected ways during transition.
- Dual-write period (if any) must be short and well-audited.
- One-time migration scripts must preserve visibility semantics.

### 6. Additional Controls
- Concurrency: Use database constraints or application-level locking when advancing the same sample within a process.
- Permissions granularity: Evaluate whether a new `process:manage` permission (or `entry:manage`) is warranted instead of overloading `experiment:manage`.
- Data classification: Samples moving through Processes may carry higher sensitivity if they contain experimental conditions or preliminary results.

## Recommendations

1. **Design RLS policies and write-back rules before any schema work.** Do not create the tables until policies are written and reviewed.
2. **Resolve naming collision early.** Choose ELN-specific names or clear separation before implementation.
3. **Treat write-back as a first-class security feature**, not an afterthought. Include it in the threat model and test plan.
4. **Add explicit process-lifecycle audit events** in addition to generic row-level auditing.
5. **Document the visibility contract**: "Assigning a sample to a Process does/does not change who can see it."
6. **Include security test cases** in any UAT for Processes (cross-client visibility, write-back from unauthorized step, etc.).

## Open Security Questions

- What is the exact visibility rule when a sample is assigned to a Process?
- Will write-backs be allowed only from certain entry types or always?
- Should process-level actions require additional approval workflows in some `lifecycle_type` cases?
- How do we handle a sample that is in multiple overlapping Processes?

## References

- Existing RLS implementations (migrations 0030, 0041, 0042, etc.)
- `.docs/requirements/experiment-processes-entries.md` (Security section)
- `.docs/design/gap-analysis-process-and-experiment.md` (Cross-Cutting section)
- FieldDefinitions security improvements (list-backed fields reduce arbitrary JSONB risk)

---
**Next step:** Security sign-off on RLS policy drafts and write-back rules before implementation begins.