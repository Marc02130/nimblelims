# CEO / Founder Review: Schema Evolution for NimbleLIMS

**Date:** 2026-06-30  
**Reviewer:** CEO / early-stage startup perspective  
**Audience:** NimbleLIMS (early-stage biotech tooling)  
**Focus:** Does the proposed FieldDefinition + schema admin approach make business sense for development velocity and market fit with early-stage biotech startups (in-house labs + heavy CRO usage)?

## Executive Summary

**Overall Assessment: Directionally smart, but execution risk and scope must be tightly controlled.**

The move away from unstructured `custom_attributes` JSONB toward typed FieldDefinitions with real columns (or controlled value tables) is the right long-term product decision. It improves data quality, reporting, search, and downstream analysis — all of which matter enormously to early biotech teams who need clean data for investors, partners, and decision-making.

However, building a general-purpose "admin can modify the schema" system (add list columns, remove columns, add tables) is a significant product and engineering bet. For a small team targeting resource-constrained early-stage companies, this can easily become a time sink that delays core value (fast experiment tracking, reliable CRO handoff, good Entries/Processes UX, robust instrument data import).

**Bottom line:** Ship a narrow, high-value version focused on the most common needs (list-backed fields like specimen_biotype, simple scalars, easy deprecation) with a hard cutover. Defer full "add table" capability and broad schema UI. This still differentiates you from spreadsheet hell and pure JSONB tools without over-engineering.

## Market Reality for Early-Stage Biotech

Target users (pre-seed to Series B, often <30 people total):
- Lab teams are small and scientist-led.
- Many assays (especially ADME, PK, complex QC, NGS prep) are sent to CROs.
- Needs change weekly: new compound types, new metadata for a grant, new QC metrics, new process steps.
- Engineering resources are extremely limited — the "LIMS person" is often the same scientist doing the bench work.
- Data must be "good enough" for funding updates, partner reports, and internal decisions. Perfection is not required.
- They hate tools that require weeks of configuration or ongoing maintenance.

**What actually wins at this stage:**
- Fast time-to-first-useful-data.
- Good defaults and opinionated workflows for common biotech patterns (CRO results import, ordered experimental processes, dose-response analysis).
- Low cognitive load — "I can add the fields I need without calling the dev team or breaking things."
- Reliability and auditability when things go wrong.

**What loses:**
- Overly flexible systems that become configuration nightmares.
- Features that require deep understanding of data modeling.
- Anything that slows down core lab execution tracking.

## Alignment with Current Product Direction

**Positive alignment:**
- The JSONB refactor (moving `custom_attributes`, `processing_conditions`, loose `content` to structured FieldDefinitions + Entries) directly improves the quality and usability of Experiments and Processes — core to your ELN + LIMS separation story.
- Supporting list-backed fields via the existing Lists system is low-friction and high-value (scientists already understand lists for statuses, matrices, roles).
- Hard cutover + explicit deprecation is honest and reduces long-term technical debt.
- Better structure helps the dose-response / curve curator side (more queryable, typed data).

**Tension / risk:**
- The more powerful the schema admin becomes (especially "add table"), the more it competes for attention with finishing robust Process UI, sample queuing, Entries UX, and better CRO result ingestion.
- Early customers may ask for flexibility, but what they usually need is "make the common 80% stupidly easy and structured."

## Specific Feedback on the Proposal

### 1. Scope of "Add Table" Capability
This is the highest-risk item from a product perspective.

**Recommendation:** Defer or severely limit in v1.
- Adding columns/fields to existing entities (Samples, Experiments, Processes) = high value, manageable risk.
- Adding entirely new top-level tables = high implementation cost, high support burden, and often not the real blocker.

Early teams rarely need new top-level entities; they need better capture inside the ones they already have (Samples + Experiments + Processes).

If you ship "add table" too early, you risk:
- Feature bloat and support tickets ("how do I link my new table to Runs?").
- Dilution of focus from finishing the core experiment/process model.

### 2. Admin-Driven vs Developer-Guided
Scientists want self-service for common things. They do not want to become amateur DBAs.

**Recommendation:** Make the UI extremely guided and opinionated:
- Strong defaults (list-backed when possible).
- Clear templates for common biotech fields.
- "Promote from JSONB" helper that suggests proper typing.
- Impact preview ("this will appear in these reports and forms").

Avoid exposing raw "create any column type on any table."

### 3. Hard Cutover Reality
Hard cutovers are brave but operationally expensive.

For an early product, a short, well-communicated dual period with clear "before/after" for power users may reduce churn risk more than a pure hard cutover. Document the migration experience ruthlessly — this will be one of the first big tests of trust with new customers.

### 4. Differentiation Opportunity
Done right (structured + flexible + integrated with Processes/Entries), this can be a real differentiator vs:
- Traditional LIMS that require developer tickets for every field.
- ELN-heavy tools that stay in unstructured notes/spreadsheets.
- Over-configurable tools that feel like they were built for big pharma IT departments.

Lean into "flexibility without the foot-gun" as a positioning strength for resource-strapped teams.

## Resource & Sequencing Advice

For a small team:

**Do first (high ROI):**
- FieldDefinition model + admin UI for adding list-backed and simple scalar fields.
- Hard cutover migration tooling focused on Samples + Experiments.
- Integration so new fields appear cleanly in Entries and Processes.
- Good deprecation experience.

**Do later (or never for v1/v2):**
- Full "add arbitrary table" with auto-generated everything.
- Highly dynamic per-client schema with no core model impact.

**Time allocation warning:** Every week spent making the schema admin more powerful is a week not spent making "create process → assign samples → queue into experiment with proper entries" delightful. The latter is what actually gets you paid.

## Market Fit Verdict

**Makes sense if scoped:**
- Yes for the core idea of structured extensibility.
- Yes for list-backed columns and deprecation tooling.
- Yes as a way to clean up technical debt from JSONB.

**Does not (yet) make sense:**
- Broad "users can modify the schema however they want" as a headline feature.
- Adding table creation as a day-one capability.

Early-stage biotech buyers buy speed, clarity, and "this just works for how we actually run experiments and CRO work." A clean, guided way to add the fields they need without JSONB mess is valuable. A full schema designer is a nice-to-have that can wait until you have 10+ paying customers screaming for it.

**Suggested positioning:**
"NimbleLIMS gives you structured, queryable data by default — with just enough self-service flexibility that your scientists can add what they need without waiting on engineering or descending into spreadsheet chaos."

## Recommended Next Steps (CEO Lens)

1. Validate with 3–5 target users: "If you could add a list field like specimen biotype or deprecate an old one yourself in 5 minutes, would that change how you evaluate tools?"
2. Scope v1 of the schema admin to column additions + deprecation on the highest-usage entities (Samples + Experiments).
3. Make the migration experience a first-class product feature (great docs, dry-run, clear before/after).
4. Measure success by: reduced support tickets about "how do I capture X", faster time-to-first-structured-report, and qualitative feedback on data cleanliness.

This can be a real strength if executed with discipline. It can become a distraction if allowed to grow into a general-purpose schema platform too early.

---

**Related Documents**
- `.docs/design/schema-evolution.md`
- `.docs/security-review/schema-evolution.md`
- `.docs/requirements/schema-evolution.md`
- `.docs/user-stories/schema-modification.md`
- `.docs/jsonb-usage-analysis.md`
- `.docs/processes.md`
- `.docs/experiments.md`