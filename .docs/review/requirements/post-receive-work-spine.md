# Requirements: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Draft for formal review  
**Stem:** `post-receive-work-spine`  
**Leadership sequencing (2026-08-28):** order (asked-for) → work_order → results → SOP+AI → process → instrument import config  
**Do not implement until reviews Accept / Accept-with-conditions and open questions that block the named phase are Decided.**

**Domain PRD:** [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)

**Depends on (shipped):** atomic receive CORE (`/receive`, zero Tests). Wizard removed (PR 75). Process / Experiment / LimsRun execute substrate. `data_parsers` catalog (import engine). SOP parse → ExperimentTemplate only (lie to close in P4).

**Stamps:** WO-1…WO-7, FW-0/FW-2, WO-7 Test at LimsRun start. This packet **opens X-5**. It does **not** reopen CORE receive.

---

## 1. Problem

Receive registers identity + vessels. The bench question after that is **what was asked for** and **what the lab must do**. Today those are missing:

| Gap | Today | Hurt |
|-----|--------|------|
| Asked-for | Tests page can mint a Test; receive refuses analyses | Test is treated as the work plan (WO-7 violation if used as “order”) |
| Work list | No `work_order` | Tech guesses extract vs assay |
| Results persist | Classic results exist; persist lock not a reviewed slice | Typed number vs unit/qualifiers drift |
| SOP + AI | Apply writes ExperimentTemplate only | Selling point is a lie |
| Parser setup | Engine exists; ops skill floor high (R-8) | Labs cannot configure import without eng |

## 2. Spine (normative)

```text
RECEIVE          identity + 1..N vessels          SHIPPED
ASKED-FOR (P1)   analysis + TAT + params          THIS PACKET (lake)
ROUTING (P2)     analysis × sample_type × TAT     THIS PACKET
WORK_ORDER (P2)  ordered process_definition chain THIS PACKET
EXECUTE          Process → Exp and/or LimsRun     SHIPPED (route into it)
TEST (WO-7)      created at LimsRun start         THIS PACKET (timing lock)
RESULTS (P3)     persist lock                     THIS PACKET
SOP+AI (P4)      Apply → process definition       THIS PACKET
PARSER SETUP (P5) instruments / CRO / parsers     THIS PACKET (config UX)
```

**Name collision:** `asked-for` is **not** a rename of `projects`. The “projects → orders” idea stays parked.

## 3. Phases (implement in order)

| Phase | Name | MVP pillar | Implement when |
|-------|------|------------|----------------|
| **P1** | Asked-for (lake) | Test ordering | After this packet’s reviews Accept P1 |
| **P2** | Routing + work_order | Test ordering / processing | P1 shipped; OQ-TAT overlap Decided |
| **P3** | Results persist | Results entry | After P1 (may parallel P2 if Test exists via LimsRun or classic) |
| **P4** | SOP+AI → process definition | Processing (not MVP bar) | P2 process chain is the Apply target; extract-hold dest type still Hold for blood→DNA→Qubit E2E |
| **P5** | Instrument import configuration | Processing (parsers shipped) | Independent of P1; do not block P1 |

P1 is the **lake**. P2–P5 are specified here so reviews see the path. Coding agents implement **one phase per PR**.

## 4. Functional requirements

### 4.1 P1 — Asked-for (lake)

| ID | Requirement |
|----|-------------|
| **RQ-AF-1** | After receive, a user with `test:assign` and sample/project access can record **asked-for** rows: `sample_id`, `analysis_id`, `tat_days` (integer ≥ 1), optional `params`. **L1:** one action may target a **set** of samples (same analysis + TAT + params); API still one row per sample. Copy: requested analysis, never “assign test” / “start work.” No Start/Execute on `requested`. |
| **RQ-AF-2** | Asked-for does **not** create Test, Result, Process, Experiment, or LimsRun rows. |
| **RQ-AF-3** | UI is **not** `/receive`. Surface: Sample Mgmt item **Asked-for** (`/asked-for`) plus a section on sample detail. Receive never sends `analysis_ids`. |
| **RQ-AF-4** | Active uniqueness: one open asked-for per `(sample_id, analysis_id)`. Duplicate → **409**. |
| **RQ-AF-5** | Status: `requested` \| `routed` \| `cancelled`. P1 only writes `requested` / `cancelled`. `routed` is P2. |
| **RQ-AF-6** | `params` is a JSON object. Keys must match `analysis_param_defs` for that analysis (P1 may ship with zero defs = empty object only). Unknown key or missing required def → **422**. |
| **RQ-AF-7** | AuthZ = sample access (project RLS) + `test:assign`. Client role cannot create. Mutate routing/config is **not** this permission. |
| **RQ-AF-8** | RLS via sample → project (same as tests). No new AuthZ path. |
| **RQ-AF-9** | List views: by sample, by project, by analysis, status `requested`. |
| **RQ-AF-10** | Cancel is allowed while `requested`. Cancel after `routed` is P2 (must cancel or complete the work_order first). |

### 4.2 P2 — Routing map + work_order

| ID | Requirement |
|----|-------------|
| **RQ-WO-1** | Entity name is **`work_order`** (WO-1). |
| **RQ-WO-2** | Routing map keys: **analysis + sample_type + TAT day range** (WO-2). Output: **ordered** `process_definition_id[]` (WO-3). |
| **RQ-WO-3** | Mutate routing map = **`config:edit` only**. Empty map mints **nothing**. |
| **RQ-WO-4** | Overlapping TAT ranges for the same `(analysis_id, sample_type_id)` **refuse** on save (**409**). No silent “first match.” |
| **RQ-WO-5** | **L2:** Qubit-on-blood (or any LimsRun step whose configured accepted sample type ≠ current sample type) → **422 `route_sample_type` on map save and on route**. Eligibility is **config** on the LimsRun step and/or analysis — **not** `sample_type_transitions`. Until dest-type execute writes DNA, Extract→Qubit on blood **refuses**. No OOB blood→Qubit routes. |
| **RQ-WO-6** | On asked-for save (or explicit “Route” if map was empty at save): if a map row matches, mint **one** `work_order` embedding the process-definition chain snapshot. Asked-for → `routed`. |
| **RQ-WO-7** | Instantiating the first process uses **existing process AuthZ** (`experiment:manage`). No client expand. **L4:** completing process N starts N+1 from the **WO snapshot chain** — no second routing hop. |
| **RQ-WO-11** | **L3:** Asked-for `params` snapshot onto the Test at LimsRun start and freeze. |
| **RQ-WO-8** | Work_order does **not** create Tests. Tests are created at **LimsRun start** (WO-7). Publish **refuses** if Test is missing (no ensure-on-publish). |
| **RQ-WO-9** | Non-instrument analysis: LimsRun with `analysis_id` required; manual results OK; parser requires instrument XOR CRO (WO-4). |
| **RQ-WO-10** | Work_order status: `queued` \| `in_progress` \| `completed` \| `cancelled`. |

### 4.3 P3 — Results persist lock

| ID | Requirement |
|----|-------------|
| **RQ-RES-1** | Typed token lands in `results.reported_result`. `raw_result` **may** copy. **`qualifiers` is the existing UUID FK** to Result Qualifiers (`<LOD`, `ND`); **NULL** for a clean number. Do **not** write JSON into `qualifiers` (SC1). |
| **RQ-RES-2** | Unit comes from `analytes.units_default`. If missing → **422**. Do **not** add `results.unit_id`. No unit picker. |
| **RQ-RES-3** | Two writers on the same Test (classic entry vs LimsRun publish) → **409**. |
| **RQ-RES-4** | P3 does not mint Tests at asked-for or receive. |

### 4.4 P4 — SOP + AI → process definition

| ID | Requirement |
|----|-------------|
| **RQ-SOP-1** | Human **Apply** of a SOP parse job creates (or updates a draft) **`eln_process_definition`** with typed steps (`eln_experiment` \| `lims_run`), not only an ExperimentTemplate. |
| **RQ-SOP-2** | Apply is **never** silent auto-activate. User reviews and saves. |
| **RQ-SOP-3** | Optional: Apply may create an **inactive** `data_parsers` draft from extracted `parser_config`. Production import stays deterministic. |
| **RQ-SOP-4** | **L5:** Does **not** ship extract-hold dest type. Blood → DNA daughter → Qubit on the daughter remains **Hold**. Apply success copy must not claim that path is runnable. |
| **RQ-SOP-5** | No SOP PDF bodies in git. No IC50. |

### 4.5 P5 — Instrument import configuration

| ID | Requirement |
|----|-------------|
| **RQ-IMP-1** | Admin (`config:edit`) can CRUD **instrument types**, **instruments**, **CRO sources**, and **data_parsers** keyed by analysis + (instrument XOR CRO). |
| **RQ-IMP-2** | Parser setup: ≥1 example file, ≥1 expected-output test, dry-run harness, activate only if tests pass. |
| **RQ-IMP-3** | Optional **AI draft** of `parser_config` at setup only. Day-to-day import = no LLM (G4/G5 already stamped). |
| **RQ-IMP-4** | Sidebar shows **active** parsers/instruments; activate = `config:edit` (FW-1b). |
| **RQ-IMP-5** | Not CMMS, not user-uploaded executable parsers, not XLSX-as-P0 unless already supported. |

## 5. Non-goals (all phases)

- Reopen CORE receive / analysis picker on `/receive` / non-empty `analysis_ids` accepted
- Mint Tests at asked-for or work_order save
- Second workflow engine beside Process / Experiment / LimsRun
- Rename `projects` → `orders`
- Intake-profile engine, bulk intake UI, wizard revival
- Compound registration / lots (WO-5/6)
- Materials module, multi-tenant, IC50 / dose-response
- Extract-hold dest type (own stem; P4 must not pretend it is done)

## 6. Bounce (any phase PR)

1. Analysis on `/receive`
2. Test created at asked-for or work_order save
3. Ensure-on-publish invents a Test
4. Overlapping TAT silently matches
5. Empty routing map mints work_orders
6. LLM on production file import
7. SOP Apply auto-activates a live process without a human save
8. Client role writes asked-for / routing / parsers
9. New `results.unit_id`

## 7. Acceptance (product)

| ID | Criterion |
|----|-----------|
| AC-P1-1 | Receive a sample → record ELISA asked-for → zero Tests, zero work_orders |
| AC-P1-2 | Duplicate asked-for same sample+analysis → 409 |
| AC-P1-3 | User without project access → 403 |
| AC-P2-1 | Matching route mints work_order with ordered process ids; asked-for = routed |
| AC-P2-2 | No map row → no work_order; UI says configure routing |
| AC-P2-3 | Qubit route on blood sample → refuse |
| AC-P3-1 | Type `12.3` with units_default set → `reported_result` set; `qualifiers` NULL unless a list qualifier is chosen |
| AC-P3-2 | Missing units_default → 422, no row |
| AC-P4-1 | Apply creates process definition with at least one step; template-only Apply is gone as the success path |
| AC-P5-1 | Activate parser after dry-run pass; import a file with LLM disabled |

## 8. UAT

New script: `UAT_Scripts/uat-post-receive-work-spine.md` (create at implement, not this docs PR). P1 cases first. Do not use retired `uat-sample-accessioning.md`.
