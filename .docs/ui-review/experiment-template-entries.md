# UI / UX Review: Experiment template entries

**Date:** 2026-07-29  
**Verdict date:** 2026-07-29  
**Status:** **Accepted with conditions**  
**Tech sketch:** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)  
**CEO:** [`.docs/ceo-review/experiment-template-entries.md`](../ceo-review/experiment-template-entries.md)  
**Reviewer:** Design / UX (session)

## Executive summary

The product model is clear: **template declares tables/forms → instance shows them**. Main UX risks are **vocabulary collision** (“steps” everywhere) and **two parallel SOP tabs** still looking primary. Fix with tab order, copy, and type chips—not by merging procedure in P0.

**Verdict: Accept with conditions.**

## Design litmus (0–10)

| Dimension | Score | Notes |
|-----------|-------|-------|
| 1. Information hierarchy | 8 | Entries second tab after Basic Info is correct |
| 2. Interaction states | 7 | Empty states specified; loading/error need explicit wire |
| 3. User journey | 8 | Author → run → link samples → capture is coherent |
| 4. Specificity | 7 | Cards + dialogs sketched; need column picker detail |
| 5. Accessibility | 6 | Tables need keyboard; labels not UUID-only (**condition**) |
| 6. Consistency w/ Field Mgmt | 8 | Field picker reuse is right |
| 7. Mental model | 7 | “Steps” overload remains until copy fix |

**Overall: 7.3 → target 8.5 with conditions.**

## User flows

### A. Author

```
Templates → Edit → [Tables & forms]
  → Add block → type: Starting samples | Measurements | Conditions
  → pick columns / fields
  → reorder
  → Save
```

### B. Run

```
New experiment from template
  → Entries tab
  → Roster empty → link samples (Sample Executions)
  → Roster fills with client_sample_id, biotype, …
  → Edit measurements → Save (⇄ if write-back)
```

### C. Process (later polish)

```
Start ELN process step → same Entries surface
  (roster still empty until Q8 or manual link)
```

## Critical issues & decisions

### 1. Naming: “Entries” vs “Tables & forms”

**Problem:** “Entry” is eng jargon; “step” conflicts with process steps and protocol steps.

**Decision:** Tab label **“Tables & forms”** with chip/subtitle `Entries` if needed for docs. In-product body copy never says “step” for entry blocks—use **block** or **table/form**.

### 2. Protocol / Transfer still present (Q11)

**Decision:** Keep. Demote:

- Helper under Protocol: “SOP narrative for reviewers. Not shown as working tables on the experiment.”
- Helper under Transfer: “Worklist / sign-off configuration. Not the experiment data tables.”
- Helper under Tables & forms: “These appear when you run this template.”

### 3. Display vs editable

**Decision:** Every block card and accordion shows:

| Type | Chip |
|------|------|
| sample_roster | `Display` (default grey) |
| sample_data | `Editable` (primary) |
| experiment_detail | `Editable` (info) |

### 4. Sample identity

**Decision:** Never show bare UUID as the only label. Pattern: `client_sample_id || name || short id`; tooltip full UUID. Applies to roster and sample_data first column.

### 5. Empty states (required copy)

| State | Message | Action |
|-------|---------|--------|
| Template has zero blocks | “Add tables and forms that appear when this template is run.” | Add block CTA |
| Instance, zero entries | “This template has no tables yet.” | Link to edit template if manage |
| Roster, zero samples | “No samples linked. Add sample executions to fill this table.” | Stay on Sample Executions tab hint |
| sample_data, zero fields | “No columns configured on this table.” | — |
| sample_data, samples but unsaved | Unsaved chip (exists) | Save entry |

### 6. Column pickers

| Type | Picker |
|------|--------|
| sample_roster | Multi-select checklist from **server-provided allowlist** (labels, not raw keys only) |
| sample_data / experiment_detail | FieldDefinition multi-select (display_name + data_type); write_back optional dropdown from allowlist |

### 7. Interaction edge cases

| Interaction | Required behavior |
|-------------|-------------------|
| Double-save entry | Idempotent upsert (existing) |
| Navigate away mid-edit | Optional dirty warning if easy; else rely on Unsaved chip |
| 0 samples / 100 samples | Empty state; table scroll for large N (no virtualization P0 unless lag) |
| Reorder blocks | Up/down or drag; persist sort_order on save |

## ASCII: screen hierarchy (instance)

```
Experiment detail
├── Overview
├── Sample Executions     ← populates roster rows
├── Tables & forms        ← NEW primary work surface
│   ├── [Display] Starting samples     (roster table)
│   ├── [Editable] Sample measurements (grid + Save)
│   └── [Editable] Conditions          (form + Save)
├── Details / Steps       ← legacy ExperimentDetail; demote if empty
└── Lineage
```

## Delight (deferred P1)

- Seed template “Sample prep (example)” with three blocks  
- Deep link from empty roster to “Add samples”  
- Process context banner when experiment came from process step  

## NOT in scope (UI)

- Full procedure designer merging protocol+transfer  
- Predefined action wizards  
- Mobile-first redesign  

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Tab label **Tables & forms**; no “step” for entry blocks |
| **U2** | Display/Editable chips on every block |
| **U3** | Human sample labels (not UUID-only) |
| **U4** | Empty states as table above |
| **U5** | Protocol/Transfer demotion helpers |
| **U6** | Loading + error toasts/alerts on roster fetch and save (mirror existing capture) |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U6) |
| **Date** | 2026-07-29 |
| **Must-fix before build** | U1–U5 in plan; U6 in implementation |
| **Nice-to-have** | P1 seed template, process banner |
