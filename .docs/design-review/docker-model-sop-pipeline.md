# Design Review: Docker Models for SOP → LIMS Configuration

**Date:** 2026-07-11  
**Branch:** `docker-model`  
**Reviewer:** Design / UX  
**Scope:** End-to-end experience for uploading SOPs and reviewing AI-proposed FieldDefinitions, Experiment Templates, Process Definitions, and LimsRun scaffolds. Based on [ideas/model-fine-tune.md](../ideas/model-fine-tune.md) and post–Phase 3 experiments surface.

## Executive Summary

The user job is not “run a fine-tuned model.” The job is: **“Turn this protocol document into correct NimbleLIMS configuration without fighting four admin screens.”**

Design must make the AI feel like a **careful junior lab admin** who prepares drafts for sign-off—not an autonomous agent that mutates production config.

**Strengths of the idea:**
- Single narrative entry point (SOP upload) for a multi-object outcome.
- Aligns with existing mental models once Processes and Field Management exist.
- Review-before-apply matches lab culture (SOPs are controlled documents).

**Key design risks:**
- Cognitive overload if the draft dumps templates + processes + runs + fields in one opaque blob.
- Naming collisions (Process vs LimsRun vs Workflow) amplified when AI chooses wrong object type.
- Loss of trust after one bad auto-apply.
- Fine-tune/Docker ops UX is irrelevant to 95% of users; hide it behind “Advanced / Self-hosted model.”

## User Jobs & Personas

| Persona | Job | Success moment |
|---------|-----|----------------|
| Lab manager / scientist-admin | Stand up a new assay from SOP | Reviewed draft, Apply, templates/process appear, ready to start instance |
| Lab tech | Use resulting templates/process | Unchanged; they shouldn’t need AI config UI |
| Client (later) | Create order | **Not** this flow—ordering ≠ SOP configuration (Decision #9) |
| Platform admin (enterprise) | Air-gapped inference | Optional model endpoint settings; not day-1 |

## Core UX Principles

1. **Draft, never live** — AI writes only to a job/draft store; production objects appear on explicit Apply.
2. **Progressive structure** — Show “what we think you need” as a plan checklist before detail forms.
3. **Object-type honesty** — Every proposed item labeled: Field / Experiment template / Process definition / LimsRun config.
4. **Editability** — Full edit of draft fields before Apply; never force accept.
5. **Traceability** — Link draft → source SOP filename, page/snippet refs if available, model/provider version.
6. **Idempotent re-runs** — Re-parse updates draft; does not duplicate production objects unless user asks.

## Proposed Flow (Happy Path)

```
[Upload SOP] (+ optional instrument sample file)
        ↓
[Job processing…]  (same pattern as today’s SOP parse)
        ↓
[Plan summary]
  • 3 new/updated FieldDefinitions
  • 1 Experiment template “DNA Extraction”
  • 1 Process definition “NGS Prep” (3 steps: ELN, ELN, LimsRun)
  • 0 LimsRun-only scaffolds
        ↓
[Review tabs]
  Plan | Fields | Templates | Process | Runs | Raw JSON
        ↓
[Accept all / Accept selected] → Apply
        ↓
[Success] links to created objects + “Start process instance”
```

### Plan summary (critical screen)

Before deep forms, answer:

- **Multi-step protocol?** → Process definition proposed (or not).
- **Instrument / plate / file-based results?** → LimsRun config proposed.
- **New columns needed for capture?** → FieldDefinitions + list sources.
- **Confidence / gaps** — e.g. “Could not determine QC pass criteria; left blank.”

If the model is unsure between “one template” vs “process,” **default to the simpler object** and show an upgrade suggestion: “Make this a multi-step process?”

## Information Architecture

**Entry points:**
- Experiments → Templates → **Configure from SOP** (extend current Upload SOP).
- Processes → Definitions → **From SOP** (secondary).
- Optional: Admin → AI configuration (provider, local endpoint)—not primary.

**Avoid** a fourth top-level “AI” nav item that becomes a second configuration system.

### Review UI structure

| Tab | Content |
|-----|---------|
| Plan | Checklist of proposed objects + rationale bullets |
| Fields | Table of proposed FieldDefinitions (name, type, list, entity); map to existing fields where match |
| Templates | Same as today’s SOP apply form (protocol steps, entries, mandatory review) with AI-highlight |
| Process | Ordered steps with step_kind chips (ELN Experiment / LIMS Run); template refs |
| Runs | Parser/worklist/result column proposals only if instrument-shaped |
| Source | SOP preview / extracted text; snippets per proposal if available |

### States & empty cases

- Processing / failed (retry, show error, no partial Apply).
- Low confidence: banner “Review carefully—model confidence low on step 2.”
- Partial accept: Apply only selected rows; leave rest in draft.
- Name collisions: “Template name exists—rename or update existing?”

## Interaction Design Details

### Matching existing entities

When the model proposes `specimen_biotype`-like fields or a known list:

- Prefer **link to existing** FieldDefinition / list over creating duplicates.
- UI: “Matched existing field X” vs “New field.”

### Process vs single template

Visual chooser if both are viable:

```
○ Single experiment template (simpler)
● Multi-step process definition (recommended for this SOP)
```

### LimsRun steps

- Never imply a live run was created.
- Copy: “**Run configuration** (create LimsRun when you start this step).”
- Align with Decision #1 lazy LimsRun create.

### After Apply

- Toast/list of created IDs with deep links.
- CTA: **Start process from definition** or **Open template**.
- Do not auto-assign samples or auto-start instances.

## Visual / Mental Model

- AI sections use a consistent “Draft / AI-assisted” chip (not loud purple AI slop).
- Step kind chips match Process UI (`ELN Experiment` / `LIMS Run`).
- Avoid robot illustrations and fake “thinking” animation longer than job poll needs.

## Accessibility & Trust

- All draft fields keyboard-editable.
- Apply disabled until at least one object selected and required names filled.
- Explicit confirmation modal: “Create N objects. This cannot auto-delete. Continue?”
- Audit-friendly: who applied, when, from which job.

## Anti-Patterns to Reject

| Anti-pattern | Why |
|--------------|-----|
| Chat-only configuration | Labs need structured review, not conversation history as SoT |
| Silent auto-Apply | Trust destroyer |
| Creating process **instances** from SOP parse | SOP defines protocol, not a cohort run |
| Mixing client ordering into this UI | Different persona and permissions |
| Exposing Unsloth/fine-tune knobs in main UI | Ops surface for engineers only |

## Success Metrics (Design)

- % of jobs that reach Apply (not abandon after plan).
- Median edits per draft before Apply.
- % of Applies that create a process vs template-only.
- Support tickets: “AI created wrong thing.”
- Time from SOP upload to first process instance started (downstream).

## Design Recommendations

1. **Extend existing SOP upload UX** rather than inventing a new product island.
2. **Plan-first, details-second** layout.
3. **Default to simpler object graph**; offer process/run as explicit upgrades.
4. **Match-or-create** for FieldDefinitions and lists.
5. **Hide Docker/fine-tune** behind settings for self-hosted inference.
6. **Reuse Process + Template visual language** so AI drafts feel native.

**Design score for MVP (draft→review→apply): 8/10** if plan-first and no auto-mutate.  
**Design score if “fine-tune Docker model” is the UI center: 3/10.**

---

Related: [ceo-review/docker-model-sop-pipeline.md](../ceo-review/docker-model-sop-pipeline.md), [design/docker-model-sop-pipeline.md](../design/docker-model-sop-pipeline.md)
