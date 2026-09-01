# User stories — Configuration framework

Working notes (`.docs/internal/`). Formal review SoT stays under `.docs/review/`.

**PRD:** [`../../prd/configuration/PRD.md`](../../prd/configuration/PRD.md) · **Spec:** [`../../specs/configuration/SPEC.md`](../../specs/configuration/SPEC.md)

Ids `CFG-*` so they do not collide with domain `US-*`. Not an implement packet. P2 merge held.

---

## Spine

- **CFG-1: Configure the four-layer path**  
  As an Administrator, I want accessioning, asked-for, routing, and execution each to have a named configuration home so a second lab can change how they run the spine without a code fork.  
  *Acceptance Criteria*:  
  - Receive config is lists / fields / name templates; no analysis picker.  
  - Asked-for config is analyses + param defs.  
  - Routing config is TAT + ordered process definitions; types and analyses are derived.  
  - Execution config is process definitions (steps + accepted types), experiment templates, analyses / parsers.  
  *Priority*: High

---

## Accessioning

- **CFG-2: OOB receive without a profile engine** **[MVP]**  
  As a Lab Technician, I want to receive tubes on the OOB atomic receive path so I can start without configuring intake profiles.  
  *Acceptance Criteria*:  
  - `/receive`; stay on the form; sticky type / project.  
  - Non-empty `analysis_ids` → **422**. Zero Tests.  
  - Intake profiles deferred (FW-1).  
  *Priority*: High

---

## Asked-for

- **CFG-3: Configure what can be requested** **[MVP]**  
  As an Administrator, I want to maintain analyses and their param defs so techs can record requested analysis + TAT without minting work.  
  *Acceptance Criteria*:  
  - `config:edit` on analyses and `PUT /analyses/{id}/param-defs`.  
  - Asked-for save creates no Test and no work order.  
  - Wrong pairings may sit in the lake; refusal is routing / start.  
  *Priority*: High

---

## Routing

- **CFG-4: Author a route as ordered processes**  
  As an Administrator, I want to save TAT + an ordered process list, and see each process’s accepted types, LimsRun analyses, and emerging types, so I am not picking analyses or sample types on the map.  
  *Acceptance Criteria*:  
  - `/admin/routing-map` has no analysis picker and no sample-type picker.  
  - Display is derived from process-definition steps.  
  - Map save **409** on TAT ∩ first-step types ∩ LimsRun analyses.  
  - Map save **422** when process *x* emerging type is not accepted by *x+1*.  
  - `config:edit`.  
  *Priority*: High  
  *Note*: proposed after signed `8cfa2a9`; Leadership confirm pending.

- **CFG-5: Route uses process-step types**  
  As a Lab Technician, I want Route to assign a work order when my sample’s current type is on the first process’s first step **and** the asked-for analysis is a LimsRun in the chain.  
  *Acceptance Criteria*:  
  - Zero → **422**. Two rows that both accept this type and this analysis → **409**.  
  - Snapshot ordered list, zero Tests.  
  - `test:assign` + project access.  
  *Priority*: High

---

## Execution

- **CFG-6: Set accepted sample types on process definition steps**  
  As a process author, I want to set accepted sample types on each process-definition step so extract can take plasma and a later Qubit step can take DNA, without putting those lists on the experiment template or the analysis.  
  *Acceptance Criteria*:  
  - Process-definition editor: Autocomplete **Accepted sample types** per step.  
  - Stored on `eln_process_definition_step_accepted_sample_types`.  
  - Same template or analysis may appear in two processes with different lists.  
  - Empty list fails closed at Route / Start (`422 route_sample_type`).  
  - No accepted-type picker on Experiment template, Experiment, LimsRun, or Analysis.  
  *Priority*: High  
  *Lock*: Marc 2026-08-30.

- **CFG-7: Experiment template owns entries and dest, not inbound type**  
  As a process author, I want experiment templates to define entries (including aliquot/pool dest) so emerging type for handoff comes from the last experiment of process *x*, while inbound type stays on that process step.  
  *Acceptance Criteria*:  
  - Dest on template entry `default_dest_sample_type`.  
  - Dest-type mint remains Hold.  
  *Priority*: Medium

- **CFG-8a: Review an AI-drafted LimsRun step on the process definition**  
  As a lab manager, I want AI SOP parse (SOP + instrument example files) to draft a `lims_run` step onto a process definition so I can edit analysis and accepted types in the same editor I use when I author by hand, then activate.  
  *Acceptance Criteria*:  
  - Draft is inactive. No `lims_runs` row until Start.  
  - Edit = process-definition step (kind, analysis, accepted types). Parser = dry-run / activate.  
  - One SOP → one definition. Two methods in a job → two definitions; human writes the routing map.  
  - SOP-only = skeleton, no parser. Example files required to draft a parser.  
  *Priority*: Medium  
  *Note*: north star; implement gate CLOSED. Today Apply writes ExperimentTemplate only.

- **CFG-8b: Choose parser at import, not on the process**  
  As a Lab Technician, I want an analysis to have parsers for each instrument (or CRO) that can run that test, so when I import a file on a started LimsRun I pick the instrument/CRO and the matching parser is used — not something baked into the process definition.  
  *Acceptance Criteria*:  
  - Process LimsRun step stores `analysis_id` only.  
  - Many parsers per analysis (`parser_analyses`). Parser scoped to instrument XOR CRO.  
  - Import: source + optional parser override; must be linked to `run.analysis_id`. Default if set.  
  - Stored on `lims_run_imports.parser_id` (that version). No LLM.  
  - Manual LimsRun: no parser required (WO-4).  
  *Priority*: High

- **CFG-8: LimsRun step picks an analysis, not a template**  
  As a process author, I want a LimsRun step to pick an analysis so the run is WO-4 honest, without inventing a LimsRun template for sample types.  
  *Acceptance Criteria*:  
  - Step kind `lims_run` → `analysis_id`.  
  - Accepted types still on the step (CFG-6).  
  - No `LimsRunTemplate` in this packet.  
  *Priority*: Medium  
  *Note*: LimsRun template for parser/worklist/lifecycle remains discuss-only; no implement.

---

## Out of scope

- Moving accepted types onto ExperimentTemplate or Analysis  
- Implementing LimsRunTemplate  
- Intake-profile engine  
- Dest-type mint / blood→DNA E2E  
- Rewriting signed P2 UAT  
