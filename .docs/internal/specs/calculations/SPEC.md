# Spec: Calculations

**Implement: CLOSED (awaits Marc).** No product code, migration, test, or config change may be built from this Spec until Marc says go.  
**Date:** 2026-11-04  
**Status:** Working draft (requirements level). No Accept, no Confirm, no UAT Pass. The acceptance criteria in §3 are requirements for QA to test. They are not results.  
**Base:** `main` at `8e327c2` (merge of #252). "Shipped" means on that commit. "Not built" means not on that commit.  
**Stress-case SOP:** NCI NCL Method STE-1.2, *Detection of Endotoxin Using the Kinetic Turbidity LAL Assay*, version 1.3 (July 2024), DOI [10.17917/2EEV-MY50](https://doi.org/10.17917/2EEV-MY50), based on USP <85>. Cited by link only: <https://dctd.cancer.gov/drug-discovery-development/assays/nano/ncl-methods-ste1.2.pdf>. No SOP text or PDF is in the repo. Requirements below are written in our own words with section cites ("STE-1.2 §n"). Sourced by Katinka.

Each rule has an ID (CALC-REQ-n), a state tag (**[Shipped]**, **[Partly shipped]**, or **[Not built]**), and acceptance criteria (AC). A tag describes what exists on `main` today, not what this Spec asks for.

---

## 0. Scope

This Spec covers exactly:

1. The first slice, in order: (a) pin the R service; (b) known-answer tests (KATs) on the pinned service; (c) ELISA (4PL standard curve and back-calculation) plus one stress case, the kinetic turbidity LAL endotoxin assay (STE-1.2).
2. A closed catalog of named, versioned functions, used through a no-code builder.
3. Stop rules for every stage, missing-data rules for every formula, and explicit units on every input and output.
4. Immutability of formulas and released versions, result pinning, and no silent recompute.
5. Calculation-scoped, additive, incremental releases.
6. Agent proposes, a named person activates, with a validation-state record.
7. What is out of scope (§5).

Anything else is not in this Spec.

---

## 1. Shipped reality (survey of `main` at `8e327c2`)

| Area | What exists | Where |
|------|-------------|-------|
| R service | Plumber service `lims-r-calculator`, internal network only, no host port. Routes: `GET /health`, `POST /fit`, `POST /svg/full`. R never touches the database. | `services/r-calculator/plumber.R`, `docker-compose.yml` |
| Image pin | **None.** `FROM rocker/r-ver:4.4` is a floating tag. Packages (`plumber`, `drc`, `ggplot2`, `svglite`, `jsonlite`, `MASS`, `R.utils`) are installed at build time from the Posit Package Manager without versions. No `renv.lock`. No digest anywhere. | `services/r-calculator/Dockerfile` |
| Health | Reports `status`, `drc_version`, `r_version`. No image digest, no lock hash. | `plumber.R` |
| Fit | `fit_compound()` wraps `drc::drm` with `LL.4`, `LL.3`, `LL.3u`, `LL.5` (`4PL`, `3PL_FB`, `3PL_FT`, `5PL`). Fewer than 4 points fails. An unknown model name silently falls back to `LL.4`. Bounds vectors are always length 4, whatever the model. CI is profiled with a 5 s timeout, else a ±1.96·SE fallback. | `services/r-calculator/R/fit.R` |
| Categories | Eight curve categories in fixed priority (`CANNOT_FIT` … `SIGMOID`), hook-effect detector, quality flag map. | `services/r-calculator/R/category.R` |
| Use of the fit | Dose-response only: percent inhibition from positive/negative control wells (`samples.qc_type`), replicates averaged per concentration, soft knockouts, 10% knockout warning, one batch POST, 60 s timeout. `potency_type` is always `IC50`. | `backend/app/services/dose_response_fit.py`, `backend/app/services/r_calculator_client.py` |
| Result storage | `dose_response_results` keeps fit parameters, category, review status, `fit_version`, `superseded_by`, `fit_triggered_by/at`. **No** function version, image digest, lock hash, or unit column. `config.concentration_unit` is sent to R and not used there. | `backend/models/dose_response.py`, migration `0043_dose_response_tables` |
| Refit | A refit after knockout writes a new row (`fit_version + 1`); the old row gets `superseded_by`. | `dose_response_fit.py`, `models/dose_response.py` |
| SVG export | `POST /svg/full` re-runs `fit_compound` on all points, without the stored constraints, to draw the PDF curve. The drawn curve is not read from the stored result. | `plumber.R` |
| R tests | `testthat` file with a synthetic 4PL set (IC50 within 10% of 100 nM, R² > 0.99) and category checks. Sourced from the host, not run in the image, not in `.github/workflows/ci.yml`. | `services/r-calculator/tests/test_fit.R` |
| ELISA | **No plate math.** Import plus publish stores the analyte-matched column as entered (for example `corr`). No 4PL standard curve, no back-calculation, no duplicate %CV, no kit QC pass/fail, no LLOQ/ULOQ. The IL-6 Gen5 fixture is synthetic and its `Conc/Dil` column carries no unit. | `manuals/lims-runs.md` (Current Limitations), `UAT_Scripts/uat-elisa-run-gaps.md` (Deferred), `backend/tests/fixtures/elisa/IL6-PLT-0001_Gen5.csv` |
| Endotoxin | Seed analysis `analysis-endotoxin-001` (LAL, analyte EU/mL, range 0–10). No endotoxin calculation exists. | `UAT_Scripts/test-data-scenarios.md` |
| Classic results | `results.raw_result`, `reported_result`, `calculated_result` are free-text strings. `calculated_result` is entered, never computed. Run publish promotes `raw_result` only; "calculated deferred" (run-results Decision #2). | `backend/models/result.py`, `.docs/review/open-questions/run-results.md` |
| Units | A `units` table with base-unit multipliers and conversion helpers. Not wired to the R service. | `backend/app/core/conversions.py` |
| Configuring agent | The allow-list refuses `/v1/lims-runs`: "Run analysis and dose-response are not configuration." | `backend/app/services/configuring_agent_allow.py`, `.docs/internal/specs/configuring-agent/SPEC.md` §3.4 |
| Catalog / builder | **None.** No named, versioned function catalog. No builder. No user code path. | — |

---

## 2. Definitions

- **Function:** a named calculation in the catalog, for example `lal_endotoxin_limit`. Identified by `name` plus an integer `version`.
- **Lock:** the pair (R service image digest `sha256:…`, SHA-256 of the committed `renv.lock` file bytes).
- **Lock hash:** SHA-256 of the UTF-8 string `<image digest>\n<renv.lock sha256>`. One lock hash names one runnable R environment.
- **Release:** a calculation-scoped bundle of new function versions, their KATs, and the lock hash they were proven on.
- **Calculation configuration:** a no-code composition of catalog functions with input bindings, constants, and units, for one analysis.
- **Stage:** one function call inside a configuration. Each stage has a stop rule.
- **Not detected (`<`):** a below-limit result. It is a value with a qualifier, not missing data.

---

## 3. Rules

### 3.1 Slice order

- **CALC-REQ-1 [Not built]** The first slice is delivered in order: (a) pin, then (b) KATs, then (c) ELISA plus the LAL stress case. No (b) work merges before (a) is merged. No (c) function is released before its KATs pass on the pinned lock.
  - AC: the merged history of the slice shows the pin before any KAT, and every (c) release record names a lock hash that has a passing KAT run.

### 3.2 (a) Pin the R service

- **CALC-REQ-2 [Not built]** The R service base image is referenced by digest (`FROM <image>@sha256:<digest>`), not by tag. The deployed service image is identified by its own digest.
  - AC: the Dockerfile has no `FROM` line without `@sha256:`. Two builds from the same commit report the same lock hash on `/health`.
- **CALC-REQ-3 [Not built]** R packages come only from a committed `renv.lock` (`renv::restore()`). The image build does no unversioned `install.packages`. A restore that cannot match the lock fails the build.
  - AC: the Dockerfile restores from `renv.lock` and contains no `install.packages(` call. Changing one package version in `renv.lock` changes the lock hash.
- **CALC-REQ-4 [Not built]** `GET /health` reports the image digest, the `renv.lock` SHA-256, and the lock hash. The backend holds the expected lock hash. **Stop rule:** if the reported lock hash differs from the expected one, or `/health` does not report one, the backend refuses every calculation call and writes nothing.
  - AC: with a mismatched expected hash, a calculation request returns an error that names the mismatch, and no result row exists afterwards. Shipped `/health` reports only `drc_version` and `r_version`.

### 3.3 (b) Known-answer tests

- **CALC-REQ-5 [Not built]** Every released function version has KATs: fixed inputs (with units), expected outputs (with units), and a declared tolerance per output (absolute or relative, with units). KATs run against the built, pinned image over HTTP, not against host R.
  - AC: the KAT run log names the image digest and lock hash it ran on, and lists each case as pass or fail with the observed value, expected value, and tolerance. Shipped `test_fit.R` runs on the host, is not in CI, and uses a 10% band on one synthetic set; it does not meet this rule.
- **CALC-REQ-6 [Not built]** KAT expected values come from a cited source independent of the function under test (a published worked example, or a computation outside the R service that is recorded with the case). Synthetic or public data only. No SOP body text, no SOP PDF, and no client data in fixtures.
  - AC: each KAT case has a source citation. The STE-1.2 §6 worked example (EL 0.5 EU/mg, MVD 5000 at 10 mg/mL and HED 10 mg/kg) is a valid citation for `lal_endotoxin_limit` and `lal_mvd`, cited by section, not copied.
- **CALC-REQ-7 [Not built]** **Stop rule (engineering, not lab validation):** a function version cannot be part of a release unless its KATs pass on the release's lock hash. A new lock hash re-runs every KAT of every released version it will serve.
  - AC: an attempt to release a version with a failing or absent KAT run on that lock hash is refused. This is a software-release check. It is not the lab validation gate, which is out of scope (§5).

### 3.4 (c) ELISA

The IL-6 serum ELISA pack (synthetic Gen5 fixture, duplicates, 8 standards, low/mid QC) is the ELISA reference shape.

- **CALC-REQ-8 [Not built]** `elisa_4pl_standard_curve` v1 fits a four-parameter logistic curve to calibrator responses against nominal calibrator concentrations.
  - Inputs: calibrator nominal concentration (concentration unit declared on the binding, for example pg/mL), calibrator response (absorbance, unit `OD`), replicate identity.
  - Outputs: bottom (`OD`), top (`OD`), slope (unit `1`), inflection point (same unit as the calibrator concentration), goodness-of-fit statistic (unit `1`), points used and excluded (count).
  - Missing-data rule: a calibrator replicate with no numeric response is excluded from the fit and counted as excluded. It is never treated as zero.
  - Stop rule: fewer than four calibrator levels with a numeric response, or a fit that does not converge, ends the stage with "curve not fitted". No back-calculation runs on that plate.
  - AC: a KAT with a published or independently computed 4PL set reproduces the four parameters within the declared tolerance. A plate with three usable levels stops with "curve not fitted" and produces no sample concentrations.
- **CALC-REQ-9 [Not built]** `elisa_4pl_back_calc` v1 inverts the fitted curve for each sample response, then multiplies by the dilution factor.
  - Inputs: curve parameters from CALC-REQ-8, sample response (`OD`), dilution factor (unit `1`).
  - Output: concentration in the calibrator concentration unit.
  - Missing-data rule: no numeric response, or no dilution factor, gives no concentration and a "missing input" flag. A response at or beyond an asymptote has no inverse and is flagged, not assigned a number.
  - Stop rule: the function never extrapolates. A response outside the fitted calibrator range is returned as out-of-range with no numeric concentration. How out-of-range is reported (LLOQ/ULOQ wording, `<`/`>`) is lab-set (OQ-CALC-11).
  - AC: a KAT sample inside the range back-calculates within tolerance; a response above the top calibrator response returns out-of-range with no number.

### 3.5 (c) Stress case: kinetic turbidity LAL endotoxin (STE-1.2)

Why it stresses differently from the IL-6 ELISA: a linear fit (not 4PL) over four log decades (calibrators 1.0, 0.1, 0.01, 0.001 EU/mL, STE-1.2 §5.1); an inverse response (more endotoxin gives a shorter onset time, so the slope is negative); duplicates on every item; several dilutions per sample, each with its own spiked control; a run-repeat rule; and a below-limit "not detected" outcome.

- **CALC-REQ-10 [Not built]** `lal_endotoxin_limit` v1: EL = K / M (STE-1.2 §6).
  - Inputs: K in EU/kg, from a closed choice of 5 EU/kg (all routes except intrathecal) or 0.2 EU/kg (intrathecal); M, the maximum dose per kg per hour, in mg/kg.
  - Output: EL in EU/mg.
  - Missing-data rule: no M gives no EL. EL is never defaulted.
  - Stop rule: M ≤ 0, or a K outside the closed choice, is refused.
  - AC: K 5 EU/kg, M 10 mg/kg gives 0.5 EU/mg (STE-1.2 §6 worked example). M 0 is refused.
- **CALC-REQ-11 [Not built]** `lal_mvd` v1: MVD = EL × sample concentration / λ (STE-1.2 §6), with λ = 0.001 EU/mL (the lowest calibrator, §5.1).
  - Inputs: EL in EU/mg (CALC-REQ-10), sample concentration in mg/mL, λ in EU/mL.
  - Output: MVD, unit `1` (dimensionless).
  - Missing-data rule: when the dose is unknown (no EL), MVD = 500, and the output records that the dose-unknown rule was used (STE-1.2 §6 also sets the highest final test concentration to 1 mg/mL in that case).
  - Stop rule: a tested dilution above the MVD is refused for that dilution; its result is not reportable.
  - AC: EL 0.5 EU/mg, 10 mg/mL, λ 0.001 EU/mL gives MVD 5000 (STE-1.2 §6 example). No EL gives 500 with the dose-unknown marker. A dilution of 10000 against MVD 5000 is refused.
- **CALC-REQ-12 [Not built]** `lal_kinetic_standard_curve` v1: linear regression of log10(onset time) on log10(calibrator concentration).
  - Inputs: calibrator nominal concentration in EU/mL, onset time in s, replicate identity.
  - Outputs: slope (unit `1`, expected negative), intercept (log10 s), correlation coefficient r (unit `1`), calibrators used and dropped (count and identity).
  - Basis: STE-1.2 §8.1 says only that linear regression builds the curve. Log-log is **USP practice**, not SOP text. Confirming log-log is OQ-CALC-3.
  - Missing-data rule: a calibrator tube with no onset time is excluded and counted; a calibrator level with no tubes left is dropped.
  - Stop rule: see CALC-REQ-13.
  - AC: a KAT with four calibrators and known onset times reproduces slope, intercept, and r within tolerance, and the slope is negative.
- **CALC-REQ-13 [Not built]** Curve acceptance (STE-1.2 §8.2, §8.3, §8.5). The engine tests **|r| ≥ 0.980**, because r is negative for this curve. At least three calibrators must remain. **Stop rule:** |r| < 0.980, or fewer than three calibrators, fails the curve, and the run is to be repeated (§8.5). No sample result is computed on a failed curve.
  - Dropping calibrators: STE-1.2 §8.2 states the minimum of three. It does not itself spell out a dropping procedure. This Spec allows a calibrator to be dropped while at least three remain, as the brief directs; confirming that reading is OQ-CALC-4. A drop is a recorded exclusion (CALC-REQ-27), never silent.
  - AC: r = −0.985 with four calibrators passes. r = −0.975 fails with "repeat run". Dropping one of four calibrators leaves three and the curve is evaluated; dropping two is refused.
- **CALC-REQ-14 [Not built]** `percent_cv` v1: %CV = SD / mean × 100.
  - Inputs: two or more replicate values in one shared unit.
  - Output: %CV in `%`.
  - Missing-data rule: fewer than two numeric replicates gives no %CV and a "replicate missing" flag (handling a missing single tube or split duplicate is OQ-CALC-8).
  - Stop rule: mean = 0 gives no %CV and a flag.
  - Open: SD form (n−1 or n) and whether %CV is taken on onset time or on back-calculated concentration are OQ-CALC-5.
  - AC: replicates 100 and 110 give the %CV defined by the chosen SD form, within tolerance; one replicate gives no %CV and the flag.
- **CALC-REQ-15 [Not built]** Replicate design (STE-1.2 §5.3, §6, §7.3). Every item (negative control, calibrators, QC, spiked control, sample) is run in duplicate tubes. Each sample is tested at several dilutions not exceeding the MVD. Each dilution has its own spiked control (inhibition/enhancement control) at 0.05 EU/mL.
  - AC: a configuration that binds a sample dilution with no paired spiked control at that dilution cannot be activated as a complete LAL configuration; the builder shows the missing pairing.
- **CALC-REQ-16 [Not built]** Outlier rule. %CV ≤ 25% for each calibrator and QC (STE-1.2 §8.1), for each sample (§8.6), and for each spiked control (§8.7). **No Grubbs, Dixon, or other statistical outlier test** is in the catalog for this case.
  - Stop rule: a calibrator or QC %CV above 25% fails the run, which is to be repeated (§8.4, §8.5).
  - Stop rule: a sample or spiked-control %CV above 25% marks that sample dilution as failing §8.6 or §8.7; it is not passed to sample pass/fail. Whether another valid dilution may then be reported is OQ-CALC-9.
  - AC: QC duplicates at 30% CV fail the run with "repeat run". A sample dilution at 30% CV is marked and is not used for pass/fail.
- **CALC-REQ-17 [Not built]** `lal_back_calc` v1: back-calculate concentration from the curve, multiply by the dilution factor, divide by sample concentration (STE-1.2 §6 states the goal is endotoxin per mg).
  - Inputs: curve (CALC-REQ-12), mean onset time in s, dilution factor (unit `1`), sample concentration in mg/mL.
  - Outputs: measured concentration in EU/mL, concentration corrected for dilution in EU/mL, result in EU/mg.
  - Missing-data rule: no onset by the cutoff is **not missing** (CALC-REQ-20). No dilution factor or no sample concentration gives no EU/mg value and a "missing input" flag.
  - Stop rule: an onset time outside the calibrator range is not extrapolated (same rule as CALC-REQ-9).
  - AC: a KAT onset time between two calibrators back-calculates within tolerance, and the EU/mg value equals EU/mL × dilution ÷ mg/mL.
- **CALC-REQ-18 [Not built]** `lal_spike_recovery` v1: recovery % = (spiked − unspiked) / 0.05 × 100, with both values in EU/mL at the same dilution and 0.05 EU/mL the nominal spike (STE-1.2 §5.3). The formula is **USP practice, not in the SOP**; STE-1.2 §8.8 gives the acceptance range only. Confirming the formula is OQ-CALC-6.
  - Output: recovery in `%`.
  - Acceptance (STE-1.2 §8.8, §8.9): 50–200% passes. Below 50% means inhibition; above 200% means enhancement or contamination. **Stop rule:** outside 50–200%, that sample's result at that dilution is invalid and is not passed to pass/fail.
  - Missing-data rule: no spiked value gives no recovery and the dilution is not reportable. An unspiked value that is not detected is handled per OQ-CALC-7.
  - AC: spiked 0.06 EU/mL, unspiked 0.01 EU/mL gives 100%. A difference of 0.02 EU/mL (40%) marks the dilution invalid for inhibition; a difference of 0.12 EU/mL (240%) marks it invalid for enhancement or contamination.
- **CALC-REQ-19 [Not built]** `lal_sample_pass_fail` v1: a sample passes if its EU/mg result is at or below EL (STE-1.2 §9.1).
  - Inputs: result in EU/mg, EL in EU/mg.
  - Output: pass or fail.
  - Missing-data rule: no EL gives no pass/fail (the MVD default in CALC-REQ-11 does not supply an EL). A not-detected result is compared using its `<` limit.
  - Stop rule: an invalid dilution (CALC-REQ-16, CALC-REQ-18) or a failed run (CALC-REQ-13, CALC-REQ-16) gives no pass/fail.
  - AC: 0.3 EU/mg against EL 0.5 EU/mg passes; 0.6 fails; a failed run gives no pass/fail.
- **CALC-REQ-20 [Not built]** Not detected. No onset by the cutoff (7200 s by default, STE-1.2 §7.4) is reported as `<` (not detected): a below-limit result with a qualifier, **not missing data**. STE-1.2 §7.4 notes that some lysate lots need a longer time (for example 9600 s); the cutoff is a configuration input in s, not a constant (OQ-CALC-10). The number reported after `<` is lab-set (OQ-CALC-7).
  - AC: a tube with no onset at 7200 s produces a `<` result, is counted as a result, and is never shown or counted as missing.
- **CALC-REQ-21 [Not built]** Run-level QC summary. A LAL run records pass or fail with the failing reason code: curve |r|, fewer than three calibrators, calibrator %CV, QC %CV. A failed run produces no sample pass/fail. QC accuracy against nominal and a numeric negative-control limit are lab-set and are not in v1 (OQ-CALC-1, OQ-CALC-2).
  - AC: each failing condition produces its own reason code on the run summary; a run that fails any of them shows "repeat run" and no sample pass/fail.

### 3.6 Closed catalog and no-code builder

- **CALC-REQ-22 [Not built]** The catalog is closed. Version 1 contains exactly: `elisa_4pl_standard_curve`, `elisa_4pl_back_calc`, `lal_endotoxin_limit`, `lal_mvd`, `lal_kinetic_standard_curve`, `lal_back_calc`, `percent_cv`, `lal_spike_recovery`, `lal_sample_pass_fail`. Each entry declares name, version, every input and output with its unit, its missing-data rule, its stop rule, and its KATs. Shipped dose-response `fit_compound` is not in the catalog until it is brought under these rules.
  - AC: the catalog lists exactly these nine entries, each with every declared field filled.
- **CALC-REQ-23 [Not built]** Calculations are configured only in a no-code builder: pick catalog functions, bind each input to a run column, an upstream stage output, or a constant, each with its unit. There is no expression language and no free-text formula.
  - AC: the builder offers only catalog functions; there is no text field that accepts a formula or code.
- **CALC-REQ-24 [Not built]** **Prohibited:** user code, scripts, plugins, a webhook runtime, and any generic "run R" (or run-any-code) endpoint. The R service exposes only `/health` and one route per catalog function. A request naming an unknown function or unknown model is refused; it never falls back to a default.
  - AC: a call to a non-catalog function name, or a body carrying code, is refused. Shipped `fit_compound` silently substitutes `LL.4` for an unknown model name, which this rule forbids.

### 3.7 Stop rules, missing data, units

- **CALC-REQ-25 [Not built]** Every stage has a stop rule. When a stage stops, no later stage that depends on it runs, and the stop and its reason code are recorded on the calculation result.
  - AC: for each catalog function, a KAT case triggers its stop rule and shows that dependent stages did not run.
- **CALC-REQ-26 [Not built]** Every formula has a missing-data rule. Missing input is never imputed, never zero, and never silently dropped. A below-limit (`<`) value is not missing.
  - AC: for each catalog function, a KAT case with a missing input shows the declared outcome.
- **CALC-REQ-27 [Partly shipped]** An excluded point (knockout or calibrator drop) is a recorded exclusion with who and when, and is reversible by recording a new calculation result. Shipped: `lims_run_data_exclusions` records `excluded_by`, `excluded_at`, and an optional reason for dose-response points. Not built: the same for ELISA and LAL calibrators and replicates.
  - AC: after a calibrator drop, the calculation result lists the dropped calibrator, the user, and the time.
- **CALC-REQ-28 [Not built]** Units are explicit on every input and every output, using the existing `units` table. Dimensionless values are declared as unit `1`; percentages as `%`. A binding whose unit does not match the function's declared unit (after a defined conversion within the same unit type) is refused at configuration time.
  - AC: binding a mg/kg value to an input declared in EU/mL is refused. Every stored output carries its unit. Shipped: `concentration_unit` is sent to R and unused, and `dose_response_results` has no unit column.

### 3.8 Immutability, pinning, recompute

- **CALC-REQ-29 [Not built]** A released function version is immutable. Any change to a formula, default, tolerance, unit, stop rule, or missing-data rule is a new version. A released version is never edited or deleted.
  - AC: an edit to a released version is refused; the same change saved as a new version succeeds and the old version is unchanged.
- **CALC-REQ-30 [Not built]** Every calculation result records the function name and version of every stage, and the lock hash it ran on.
  - AC: a stored result shows each stage's function version and the lock hash, and that lock hash matches `/health` at the time it ran.
- **CALC-REQ-31 [Partly shipped]** No silent recompute. A recompute is an explicit, recorded new result that links to the result it replaces and records who triggered it, when, and why it ran (knockout, new version, new lock). The old result is kept. Shipped: a dose-response refit writes a new row with `fit_version + 1` and `superseded_by`. Not built: lock hash and function version on that row; the same rule for ELISA and LAL; and the PDF SVG path, which re-fits on all points without the stored constraints instead of drawing the stored result.
  - AC: after a recompute, both results exist and the new one links to the old one. Opening, exporting, or reporting a result never runs a calculation.
- **CALC-REQ-32 [Not built]** A new lock hash never rewrites results made on an earlier one. Recomputing on the new lock is an explicit recompute (CALC-REQ-31).
  - AC: after a lock change, every earlier result still shows its original lock hash and values.

### 3.9 Releases

- **CALC-REQ-33 [Not built]** Releases are calculation-scoped: one release names the functions it adds versions for, their KATs, and the lock hash. A release is additive (adds versions, never removes or edits one) and incremental (it depends only on releases it names; other calculations are untouched).
  - AC: releasing a new `lal_mvd` version leaves every ELISA function version and every earlier `lal_mvd` version available and unchanged.

### 3.10 Agent proposes, a named person activates

- **CALC-REQ-34 [Not built]** The configuring AI agent may propose a calculation configuration (functions, bindings, constants, units) through the builder. It cannot activate one. Shipped: the agent's allow-list refuses `/v1/lims-runs` ("Run analysis and dose-response are not configuration"); this Spec does not change that for running fits.
  - AC: an agent run can create a proposed configuration; an attempt by the agent to activate it is refused.
- **CALC-REQ-35 [Not built]** A named, signed-in person activates a configuration. Activation records the person, time, the function versions, the lock hash, and a validation-state value. The validation state is recorded, **not a required gate**: activation succeeds whatever the state. The list of state values is OQ-CALC-12. Activation adds no reason field.
  - AC: activation with any validation-state value succeeds and the record shows the person, time, versions, lock hash, and state.

### 3.11 Reasons

- **CALC-REQ-36 [Shipped]** This Spec adds **no** required reason field. The only existing required reason it touches is the dose-response reset-fit reason (`reset_fit_reason_required`): 1–4000 characters, refused when missing, blank, or whitespace-only, including NBSP and U+2007 (`backend/app/core/required_reason.py`). The data-point exclusion reason stays optional, shares the 4000 maximum, and a whitespace-only value (including NBSP and U+2007) is not stored as a reason.
  - AC: no route added for this Spec requires a reason.

---

## 4. Open questions

Status labels follow [`.docs/review/open-questions/README.md`](../../../review/open-questions/README.md). All are **Open**. None of these values are invented here.

| ID | Question | Blocks | Source |
|----|----------|--------|--------|
| OQ-CALC-1 | QC accuracy range (recovery against the 0.05 EU/mL QC nominal). | CALC-REQ-21 | Lab-set; not in STE-1.2 |
| OQ-CALC-2 | Numeric negative-control limit. | CALC-REQ-21 | Lab-set; not in STE-1.2 |
| OQ-CALC-3 | Confirm the curve is log10(onset) vs log10(concentration). STE-1.2 §8.1 says only "linear regression"; log-log is USP practice. | CALC-REQ-12 | STE-1.2 §8.1, USP <85> |
| OQ-CALC-4 | Confirm calibrators may be dropped while at least three remain. STE-1.2 §8.2 states the minimum; who may drop, and on what basis, is not stated. | CALC-REQ-13 | STE-1.2 §8.2 |
| OQ-CALC-5 | %CV: SD with n−1 or n; computed on onset time or on back-calculated concentration. | CALC-REQ-14, 16 | Not stated in STE-1.2 §8 |
| OQ-CALC-6 | Confirm the spike-recovery formula. It is USP practice; STE-1.2 §8.8 gives only the 50–200% range. | CALC-REQ-18 | STE-1.2 §8.8, USP <85> |
| OQ-CALC-7 | The number reported after `<` (for example λ × dilution ÷ mg/mL), and how a not-detected unspiked value enters spike recovery. | CALC-REQ-18, 19, 20 | Lab-set |
| OQ-CALC-8 | Handling a missing single tube, or a split duplicate (one tube with onset, one not detected). | CALC-REQ-14, 16 | Lab-set; not in STE-1.2 |
| OQ-CALC-9 | Which of several valid dilutions is reported. | CALC-REQ-16, 17, 19 | Lab-set; not in STE-1.2 |
| OQ-CALC-10 | Onset-time cutoff: fixed 7200 s, or set per lysate lot (STE-1.2 §7.4 allows longer). | CALC-REQ-20 | STE-1.2 §7.4 |
| OQ-CALC-11 | ELISA: blank handling, 4PL weighting, curve acceptance, duplicate %CV limit, kit QC ranges, LLOQ/ULOQ wording, and the concentration unit of the IL-6 pack (the synthetic fixture's `Conc/Dil` column has none). | CALC-REQ-8, 9 | Lab-set; IL-6 pack |
| OQ-CALC-12 | The closed list of validation-state values recorded at activation. | CALC-REQ-35 | Product |
| OQ-CALC-13 | Who supplies independent expected values for the IL-6 and LAL KATs. | CALC-REQ-6 | Product / QA |

---

## 5. Out of scope

Stated explicitly, and not built by this Spec:

- A **required validation gate** before activation or use. Validation state is recorded only (CALC-REQ-35).
- **Electronic signatures.**
- **21 CFR Part 11** compliance.
- Any new required reason field.
- IC50 as the stress case. The stress case is the STE-1.2 LAL assay.
- Any change to other features' behavior or docs.

---

## 6. Review

All pending. No stamp is given until the named person gives it.

| Order | Review | Who | Status | Date | Commit |
|-------|--------|-----|--------|------|--------|
| 1 | Security review | Günter | Pending | | |
| 2 | Fail bars written | Tobias | Pending | | |
| 3 | Confirm | Rolf | Pending | | |
| 4 | Approve | Marc | Pending | | |
