# CEO Review: Schema Evolution for NimbleLIMS

**Date:** 2026-06-30  
**Reviewer:** CEO of NimbleLIMS  
**Context:** As the CEO of NimbleLIMS, deciding whether to invest engineering resources in the proposed FieldDefinition-based schema evolution system. This would replace heavy reliance on `custom_attributes` JSONB with structured, admin-driven extensibility (FieldDefinitions for list-backed columns like `specimen_biotype`, deprecation of fields, and eventually new tables), with a hard cutover migration. The system must support our ELN (Experiments + Processes + Entries) and LIMS (Experiment Runs) offerings for early-stage biotech customers.

**Key question:** Does building this make business sense? Will it help us acquire and retain paying early-stage biotech customers faster, or will it slow us down and increase churn risk?

## Executive Summary

**Verdict: The core direction is smart and aligns with what early-stage biotechs will pay for — but we must scope it very narrowly in the near term.**

Early-stage biotechs (our target buyers) are scientist-led, cash- and time-constrained, and pay subscription fees because we save them time and deliver clean, usable data for internal decisions, investor updates, CRO partners, and funding milestones. They repeatedly complain about two things:

- Having to file tickets, hack spreadsheets, or abuse `custom_attributes` every time they need a new field or data structure.
- Their data becoming an unqueryable, unmaintainable mess.

A well-executed move to FieldDefinitions (real columns or controlled typed storage where it makes sense, leveraging our existing Lists system for things like specimen_biotype, clean hard cutover from JSONB) directly attacks a painful, recurring problem. It strengthens the value of our Experiments + Processes + Entries model and reduces support burden as customers grow from 5 people to 30+.

However, building a full self-service "schema admin" (especially the ability to add arbitrary tables) is non-trivial engineering. For a small team, every month spent here is a month not spent on the workflows that actually close deals and drive retention today: robust Process UI and sample queuing, reliable CRO result import into Runs, excellent Entries experience, and solid dose-response analysis.

**Bottom-line recommendation as CEO:**
- Build a focused MVP now: FieldDefinitions for the 80% use case (list-backed and simple scalar fields on Samples/Experiments, easy deprecation, seamless integration with Entries and Processes), with a rock-solid hard cutover on high-usage entities.
- Defer full "add table" capability and broad dynamic schema editing until we have clear signals from paying customers that lack of flexibility is blocking adoption or renewal.
- This approach will help us sell and retain faster without turning NimbleLIMS into a configuration platform before we have product-market fit.

## Market Fit for Early-Stage Biotech

Our customers (pre-seed to Series B biotechs, often <30 people total, heavy CRO usage for ADME, PK, NGS prep, etc.):
- Lab teams are small and scientist-led. The "LIMS admin" is frequently the same person running experiments.
- Needs change fast (new compound classes, new QC metrics for a grant, new process steps for a CRO).
- They need "good enough" structured data quickly for internal decisions and external reporting. They do not have IT departments.
- They pay for tools that demonstrably save scientist time and produce clean, analyzable data.

**What wins at this stage:**
- Fast path from "raw idea" to "structured data in a Process or Run that I can actually use and report on."
- Low cognitive load — scientists can add the fields they need without becoming amateur database administrators.
- Opinionated defaults for common biotech patterns (CRO handoff into Runs, ordered experimental processes, dose-response).
- Reliability — data doesn't disappear or become unqueryable during growth.

**What loses:**
- Tools that require weeks of setup or ongoing maintenance.
- Overly flexible systems that become configuration hell.
- Features that require deep data modeling knowledge.

The FieldDefinition approach, if scoped correctly, directly supports the "low cognitive load + structured data" win. Over-building it risks the "configuration hell + delayed core features" lose.

## Alignment with NimbleLIMS Product and Development Reality

**Positive alignment:**
- Cleaning up `custom_attributes`, `processing_conditions`, and loose `content` into structured FieldDefinitions + Entries directly improves the usability and perceived quality of our core ELN offering (Experiments and Processes).
- List-backed fields via the existing Lists system is low-friction and feels native to how these labs already work (statuses, matrices, roles, qc_types).
- Hard cutover + explicit deprecation is cleaner long-term than letting JSONB technical debt accumulate.
- Better structure helps the LIMS side (more queryable data feeding into Runs and dose-response).

**Real tensions for a small team:**
- Every week on schema admin UI, safe migration tooling, impact analysis, and RLS policy attachment for new fields is a week not spent on finishing robust Process UI, sample queuing across experiments, better CRO result parsing into Runs, or making Entries delightful.
- Early customers buy the workflows that solve their immediate pain (tracking complex experimental work with CROs and getting clean data out). They buy flexibility as a nice-to-have once the core is solid.
- A hard cutover on early customers carries real churn risk if not executed perfectly.

## Specific Feedback on Scope and Sequencing

**Add list-backed columns (e.g. specimen_biotype on Samples) + simple scalars:** High ROI. Do this. Scientists understand lists. It directly reduces "we hacked it into custom_attributes or a spreadsheet" complaints. Integrate cleanly so the new field appears in Entries and Processes.

**Deprecation / removal of columns:** Valuable. Reduces long-term mess. Include good impact analysis and audit.

**"Add table" capability:** Defer. Early biotechs rarely need to invent new top-level entities in month one. They need better capture inside the entities and processes they already have. Shipping this too early risks support burden and dilutes focus.

**Hard cutover:** Brave and ultimately correct, but operationally expensive. For an early product, the migration experience will be one of the first big tests of customer trust. Document it ruthlessly and have excellent rollback + communication.

## Differentiation and Willingness to Pay

Done narrowly and well, this can be a real differentiator:
- Vs. traditional LIMS: "You can add the fields you need without tickets."
- Vs. pure ELN/spreadsheet tools: "Your data stays structured and queryable by default."
- Vs. over-configurable big-pharma tools: "Flexibility without the configuration nightmare or IT dependency."

Early-stage biotechs will pay more (or churn less) for a tool that grows with them without becoming a mess. The key is delivering the flexibility *as part of* making Experiments, Processes, and Runs excellent — not as a separate heavyweight feature.

## Resource Allocation Advice from the CEO

For our current team size and runway:

**Prioritize (high ROI, supports core product):**
- FieldDefinition model + simple admin UI for adding list-backed and scalar fields.
- Hard cutover migration tooling focused on Samples + Experiments first.
- Seamless integration so new fields appear in Entries, Processes, and Runs.
- Excellent deprecation and audit experience.

**Defer (or put behind extra controls):**
- Full "add arbitrary table" with auto-generated models and UI.
- Highly dynamic per-template schema without clear product demand.
- Anything that turns the schema admin into a general-purpose low-code builder.

**Measure success by:**
- Reduction in support tickets about "how do I capture X?"
- Faster time from signup to first useful structured report or process.
- Qualitative feedback from growing customers: "This is actually usable as we scale."

## Final CEO Take

This is a good strategic bet for NimbleLIMS if we treat it as **productized flexibility** rather than an infrastructure project.

Early-stage biotechs will pay us because we make their chaotic lab + CRO work manageable with clean data. A clean, scoped schema evolution system helps us deliver on that promise without requiring them (or us) to become database experts.

Over-scope it, and we risk building something impressive on paper that delays the core workflows that actually get us paid today.

Ship the narrow, high-value version. Listen to what real paying customers complain about after using it. Then decide how much further to go.

This direction makes sense — with disciplined scoping.

---

**Related Documents**
- `.docs/design/schema-evolution.md`
- `.docs/security-review/schema-evolution.md`
- `.docs/requirements/schema-evolution.md`
- `.docs/user-stories/schema-modification.md`
- `.docs/jsonb-usage-analysis.md`
- `.docs/processes.md`
- `.docs/experiments.md`