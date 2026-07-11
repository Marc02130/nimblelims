# Security Review: Schema Evolution for NimbleLIMS

**Date:** 2026-06-30  
**Reviewer:** Security perspective (CSO mode)  
**Context:** Design for FieldDefinition-based schema evolution, replacing heavy custom_attributes JSONB with structured, admin-driven field additions (list-backed columns like specimen_biotype, deprecation, new tables). Hard cutover migration. Focused on early-stage biotech / CRO use cases.

## Executive Summary

The proposal moves in a positive direction for security by reducing reliance on unstructured JSONB for user-defined data. Structured FieldDefinitions with real columns (or typed value tables) improve auditability, query safety, and the ability to enforce invariants.

However, introducing a **dynamic schema modification capability** (even scoped) creates new attack surfaces and trust boundaries in a system that already relies heavily on PostgreSQL Row-Level Security (RLS) for client isolation.

**Overall Risk:** Medium. Mitigable with disciplined implementation, but several high-severity issues must be addressed before production use, especially around RLS consistency during migrations and blast radius of admin schema changes.

**Key Recommendation:** Treat schema changes as high-privilege operations with explicit RLS policy review. Do not allow "add table" in v1 for customer-facing use. Prioritize hard cutover safety and comprehensive testing of isolation post-migration.

## Current Security Posture Relevant to This Change

NimbleLIMS uses:
- PostgreSQL RLS with `FORCE ROW LEVEL SECURITY` on sensitive tables.
- Client isolation via `client_id` on some tables (dose-response, template_wells) and `created_by` + `has_experiment_access()` functions on experiment-related tables.
- Permission system with roles (e.g., `config:edit`, `experiment:manage`).
- Audit logging on many operations.

Strengths: Strong database-level enforcement that works even if app code has bugs.

Weaknesses for this feature: RLS policies are table-specific. Adding columns or tables without updating/ensuring policies can create leaks. Migrations that touch many rows risk locking or temporary policy bypasses.

## Identified Security Issues & Risks

### 1. RLS Policy Inconsistency During Schema Changes (Critical)

Adding a new column via the proposed system (or new table) must automatically or manually ensure the column inherits the parent's RLS policy.

Risk:
- New column on `samples` or a new `ProcessSample` table could be readable by users outside the client's scope if policy not applied.
- Hard cutover migration from `custom_attributes` JSONB: if the migration reads/writes without proper `current_setting` or role, data could be exposed in logs or temporary tables.

Evidence from codebase: Dose-response tables explicitly set `client_id` and RLS policies using `current_setting('app.client_id')`. Core experiment tables rely on function-based checks.

**Mitigation Required:**
- Schema change wizard must surface and require confirmation of RLS policy application.
- All new tables/columns must have RLS enabled by default in migrations.
- Migration scripts must run under restricted roles and validate isolation post-apply.
- Add automated tests that assert no cross-client data leakage after applying example FieldDefinitions.

### 2. Blast Radius of Admin Schema Changes (High)

An admin with `config:edit` can add fields visible across clients or projects.

Risk:
- Accidental or malicious addition of a "global" field that leaks metadata patterns (e.g., custom compound IDs or concentrations that reveal client work).
- In CRO scenarios, one tenant's admin affecting shared experiment templates.

Current controls: Permissions are coarse. No obvious "schema change approval" workflow.

**Mitigation Required:**
- Scope FieldDefinitions by default (client or project level where possible).
- Add a review/approval step for schema changes (even if lightweight).
- Audit every FieldDefinition creation/update with before/after.
- Consider a separate `schema:edit` permission or requiring `admin` role.

### 3. Data Exfiltration via New Fields or Reporting (Medium-High)

If the UI or API for new fields doesn't properly apply the same filters as core fields, or if reporting endpoints expose new columns without RLS context, leaks occur.

Risk amplified because:
- "Entries" inside Experiments will use these fields.
- ProcessSample will link samples across experiments.

**Mitigation Required:**
- New fields must be subject to the same access control logic as existing attributes (project membership + experiment access).
- Query builders and export functions must be updated to respect the new model.
- Penetration test the schema admin + any dynamic query paths.

### 4. Migration Safety and Downtime / Integrity (High)

Hard cutover from JSONB:
- Large `UPDATE ... SET new_column = custom_attributes->>...' ` can lock tables or cause bloat.
- Race conditions if app writes during migration.
- Data type mismatches or lost precision during move from JSONB.

**Mitigation Required:**
- Use batched, resumable migrations with locking strategy (e.g., `pg_repack` or online schema change tools if needed).
- Dual-write window (even if short) with verification.
- Transactional integrity checks.
- Rollback plan that can restore from archived JSONB if cutover fails.

### 5. New Attack Surface: Schema Admin UI and Dynamic Behavior

- Input validation on field names, types, list references.
- Potential for denial of service by creating many fields/indexes.
- If "add table" is implemented, risk of resource exhaustion or complex query injection if not carefully sandboxed.

**Mitigation Required:**
- Strict allow-list for field names and types.
- Rate limiting and quotas on schema changes per client.
- No execution of user-controlled SQL in migration paths.

### 6. Audit and Compliance Gaps

Schema changes themselves must be first-class auditable events (who added the field, when, what validation).

Current system has good audit on data operations; schema meta-changes need the same treatment.

## Positive Security Aspects

- Moving to typed columns + FieldDefinitions makes it easier to apply constraints, indexes, and RLS at the DB layer (better than opaque JSONB).
- Hard cutover forces cleanup of legacy paths.
- Integration with existing Lists system for controlled vocabularies is good (reduces free-text injection risks).
- Explicit deprecation/removal path is better than silent JSONB drift.

## Recommendations (Prioritized)

**P0 (Must fix before any rollout):**
- Enforce RLS policy application as part of every schema change.
- Add comprehensive isolation tests for new FieldDefinition examples.
- Make schema changes auditable and attributable.

**P1 (Strongly recommended):**
- Limit initial scope: column additions only (defer "add table" to later phase or behind extra controls).
- Separate or elevate permission for schema modifications.
- Provide clear impact analysis before applying changes (affected reports, workflows, RLS).

**P2:**
- Consider feature flag or client opt-in for the new system during transition.
- Document exact behavior for JSONB during and after cutover.

## Conclusion

The design can improve security posture long-term by making data more structured and queryable with proper controls. However, the introduction of runtime schema modification capability is a significant new trust boundary that must be engineered and reviewed with the same rigor as core access control.

For an early-stage product, start narrow, test isolation ruthlessly, and do not underestimate the operational complexity of safe migrations under RLS.

This change is supportable from a security standpoint **if** the above issues are addressed before general availability.

---

**Related Documents**
- `.docs/design/schema-evolution.md`
- `.docs/ceo-review/schema-evolution.md`
- `.docs/requirements/schema-evolution.md`
- `.docs/design/jsonb-usage-analysis.md`
- `.docs/design-review/schema-evolution.md` (prior version)