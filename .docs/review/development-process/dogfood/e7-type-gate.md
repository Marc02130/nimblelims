# Dogfood: E-7 type gate on experiment / LimsRun start

**Stem:** `extract-hold-dest-type`  
**Branch:** `feat/e7-type-gate-experiment-limsrun`  
**SHA:** `4b3609a` (`4b3609a` tip at write)  
**When:** After this branch is up, **before** Tobias UAT §10 in [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md).  
**Not a UAT Result.** Do not invent Pass. Do **not** restamp §§1–9. Not E-6. Not dest-follow. Not IC50.

Maps to UAT **10.1–10.6**. SoT is `eln_process_definition_step_accepted_sample_types`. Not on the experiment template. Not on an entry.

## Env

Local compose on **this feature branch**. Frontend `http://localhost:3000`. API `http://localhost:8000`.

| Role | Login | Use for |
|------|--------|---------|
| Admin | `admin` / `admin123` | Process definitions, templates, start, API |
| Lab tech | `lab-tech` / `labtech123` | Start dialog (experiment:manage) |

Need at least one **Blood** sample and one **DNA** sample, each in a container, status **Available for Testing**. Accessioning still sets **Received** (E-6, not this packet) — set status in sample edit if needed. Do not score Received as an E-7 Fail.

Do not prune the DB volume unless you want a wipe.

## Pages

| Path | What to look at |
|------|-----------------|
| `/experiments/processes` | Definitions tab. Per step: kind, template **or** analysis, **Accepted sample types** Autocomplete. |
| `/experiments/templates` | No inbound-types control on the template or on an entry. |
| `/experiments` | Ad hoc / from-template start (path 4). |
| Process instance → step **Start** | Dual-list `StartExperimentDialog`. Ineligible rows show a reason. |

## Paths

1. **Definition allow-list (UI).** Definitions → experiment step → **Accepted sample types** = DNA only. Save. Instantiate. Start the experiment step with an empty cohort (creates the experiment).
2. **Wrong type at experiment start (10.1).** Assign a Blood sample to the process. Start the experiment with that Blood. Expect **422** `route_sample_type`. Blood sample still exists.
3. **Matching type (10.2).** Remove Blood from the process. Assign DNA. Start the experiment with DNA. Cohort locks DNA.
4. **LimsRun start (10.3).** Separate definition: LimsRun step (e.g. Qubit) with accepted types DNA only. Instantiate and start the step (creates the run). `PATCH /v1/lims-runs/{id}/start` with Blood → **422** `route_sample_type`.
5. **Ad hoc (10.4).** New experiment from a template, **no** process. Start with Blood. Start succeeds. This table does not gate standalone experiments.
6. **Template bounce (10.5).** Templates UI has no accepted-types picker. `POST /v1/experiment-templates` with `template_definition.accepted_sample_types` → **422** `accepted_sample_types_not_on_template`. Same if that key is on an entry `config`.
7. **Eligible list (10.6).** DNA-only experiment step; Blood and DNA both assigned. Eligible-samples: Blood `eligible: false` with a type reason; DNA eligible. Dual-list cannot move Blood into the selected cohort.

### API (same SHA; supporting)

Login then:

```http
POST /v1/experiments/{id}/start
{"sample_ids": ["<blood>"]}
→ 422 {"detail":{"code":"route_sample_type",...}}

PATCH /v1/lims-runs/{id}/start
{"sample_ids": ["<blood>"]}
→ 422 {"detail":{"code":"route_sample_type",...}}

POST /v1/experiment-templates
{..., "template_definition": {"accepted_sample_types": ["..."], ...}}
→ 422 {"detail":{"code":"accepted_sample_types_not_on_template",...}}

GET /v1/eln-processes/{id}/steps/{step_id}/eligible-samples
→ Blood eligible false; DNA eligible true
```

pytest `tests/test_e7_type_gate.py` (6 passed on `4b3609a`) is **supporting only** — not the dogfood stamp.

## Fail bars

- Start silently accepts the wrong type.
- Gate lives on the template or an entry.
- Ad hoc start 422s from this table.
- Blood is deleted on 422.
- Dual-list lets you pick Blood on a DNA-only step.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| | | Fill after the walk |

## Ready for UAT?

Fill after a walk. Do **not** invent Ready=Yes.

**Date:**  
**Who:**  
**SHA:** `4b3609a` (update if the tip moved)  
**Env:** local compose on `feat/e7-type-gate-experiment-limsrun`  
**Ready for UAT section 10?** Unsigned until Tobias.

Ready=Yes is dogfood, not a substitute for formal §10 Pass. Do **not** restamp §§1–9.
