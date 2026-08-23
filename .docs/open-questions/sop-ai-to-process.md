# SOP + AI → process definition

**Date:** 2026-08-21  
**Status:** **Locked** (Marc). Findings only. No code. No SOP bodies in git. Not IC50.  
**Selling point tested:** SOP + instrument data + AI → process definition, experiment steps, LimsRuns.

Source is Katinka’s public links, not files in git. Existing `.docs/sop/` stays mapping/synthesis only.

## Source (links only — do not check in PDFs)

Path: intake → DNA daughter → Qubit on that daughter (not the blood).

| Role | SOP | Link |
|------|-----|------|
| Extract | NCI Frederick SOP 23113 — QIAamp Mini (quantitation points at 22975) | https://frederick.cancer.gov/media/1962/download?ext=pdf |
| Quant | NCI Frederick SOP 22975 — Qubit 4 dsDNA HS | https://frederick.cancer.gov/sites/default/files/2023-01/22975_Redacted.pdf |
| Backup extract | KingFisher whole blood | https://frederick.cancer.gov/media/4402/download?ext=pdf |

## Frame can hold it

The catalog already has a place for:

- A process definition with `eln_experiment` and `lims_run` steps.
- A parser that is analysis × instrument XOR CRO.
- Tests that write for samples that exist on that step.

SopParseJob does **not** produce that catalog.

## Apply cannot

Apply today writes an **ExperimentTemplate** only. It does not create:

- a process definition
- a LimsRun
- a `data_parsers` row

The extracted `parser_config` stays on the job. The extracted `template_definition` is still `protocol_steps` / `transfer_steps` / `result_columns`. Current authoring is `entries[]` and **clears** those legacy keys.

**SOP + AI → a live process is a lie.** The frame can hold it. Apply cannot.

## Extract-then-Qubit Hold still stands

Dest copies the parent’s matrix and never lands on `eln_process_samples`. Even a perfect parse cannot ship blood → DNA daughter → Qubit on the daughter. A perfect parse does not fix that.

Do not reopen IC50.

**Follow-on packet (docs only, implement gate CLOSED):** [requirements/extract-hold-dest-type.md](../requirements/extract-hold-dest-type.md) · [tech-sketch/extract-hold-dest-type.md](../tech-sketch/extract-hold-dest-type.md). Optional dest `sample_type` on aliquot/pool; execute writes type + `parent_sample_id` + `eln_process_samples`. Matrix drop and TruSeq are out.

## Catalog gap (this path, not PR 48)

PR 48 CSVs are HCP / LAL / NCI-60. They do **not** exercise this SOP path.

Missing for blood → DNA → Qubit:

- whole-blood intake
- a DNA daughter with `parent_sample_id`
- a Qubit analysis

Anton’s test-data catalog for this path can live in the repo. SOP bodies still do not.

## Out of this note

- No vendor SOP text in git (IP).
- No product code.
- No UI.
- Compose stays down unless someone is actually checking the app.
