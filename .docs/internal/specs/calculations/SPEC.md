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
- **Lock hash:** one value for one runnable R environment. It is SHA-256 of a UTF-8 preimage with three fields, separated by a single LF (U+000A), with no spaces and no trailing LF:

  `<base>\n<renv>\n<tree>`

  - `<base>` is 64 lowercase hex digits: the digest in the Dockerfile `FROM <image>@sha256:<base>`. It is the pinned base image, not the built service image.
  - `<renv>` is 64 lowercase hex digits: SHA-256 of the raw bytes of the committed `renv.lock`.
  - `<tree>` is the lowercase hex git tree id of `services/r-calculator` (`git rev-parse <commit>:services/r-calculator`). That tree is the function source. The catalog function version is not an input. It is stored on the result beside the lock hash (CALC-REQ-30).

  The lock hash is reported as 64 lowercase hex digits. Two builds of the same commit produce the same preimage and the same lock hash. The built image digest is required and is recorded alongside the lock hash. It is not an input to the lock hash, because a rebuild changes that digest. An image cannot know its own digest at build time, so the deploy supplies it at run time as the env var `R_IMAGE_DIGEST`, taken from the image it pulled by digest. `/health` gets `<base>` and `<tree>` from build args baked into the image, and computes `<renv>` from the `renv.lock` copied into the image. The backend's expected lock hash is recomputed from the commit the same way, with no image build.
- **Release:** a calculation-scoped bundle of new function versions, their KATs, and the lock hash they were proven on.
- **Calculation configuration:** a no-code composition of catalog functions with input bindings, constants, and units, for one analysis.
- **Stage:** one function call inside a configuration. Each stage has a stop rule.
- **Calculation attempt:** the record of one run of a configuration. It holds status, stop reason codes, lock hash, built image digest, function versions, and time. It always exists once a calculation call is accepted. A **result** is a numeric or qualified output value on an attempt. An attempt can hold no result.
- **Qualified results.** Each is a result with a stored qualifier kind, not missing data. There are three kinds:
  - `not_detected`, shown `<`. LAL only: no onset by the cutoff (CALC-REQ-20).
  - `below_range`, shown `<`. A detected response or onset past the low-concentration end of the used calibrators (CALC-REQ-9, CALC-REQ-17).
  - `above_range`, shown `>`. A response or onset past the high-concentration end (CALC-REQ-9, CALC-REQ-17).

  `not_detected` and `below_range` display the same symbol and are stored as different kinds. The number shown after the symbol is the result's limit, and its value is lab-set (OQ-CALC-7 for LAL, OQ-CALC-11 for ELISA).

---

## 3. Rules

### 3.1 Slice order

- **CALC-REQ-1 [Not built]** The first slice is delivered in order: (a) pin, then (b) KATs, then (c) ELISA plus the LAL stress case. No (b) work merges before (a) is merged. No (c) function is released before its KATs pass on the pinned lock.
  - AC: the merged history of the slice shows the pin before any KAT, and every (c) release record names a lock hash that has a passing KAT run.

### 3.2 (a) Pin the R service

- **CALC-REQ-2 [Not built]** The R service base image is referenced by digest (`FROM <image>@sha256:<digest>`), not by tag. The lock hash uses that base digest (§2). The built image has its own digest, recorded alongside the lock hash, and that built digest is not part of the lock hash.
  - AC: the Dockerfile has no `FROM` line without `@sha256:`. Two builds from the same commit report the same lock hash on `/health`. Their built image digests may differ, and each is recorded. Recomputing §2 from the commit, without building, yields that same lock hash.
- **CALC-REQ-3 [Not built]** R packages come only from a committed `renv.lock` (`renv::restore()`). The image build does no unversioned `install.packages`. A restore that cannot match the lock fails the build.
  - AC: the Dockerfile restores from `renv.lock` and contains no `install.packages(` call. Changing one package version in `renv.lock` changes the lock hash.
- **CALC-REQ-4 [Not built]** `GET /health` reports `<base>`, `<renv>`, `<tree>`, the lock hash from §2, and the built image digest (`R_IMAGE_DIGEST`, §2). The built image digest is required. The backend holds the expected lock hash, recomputed from the commit. **Stop rule:** the backend refuses every calculation call and writes nothing when any of these is true: the reported lock hash differs from the expected one; `/health` does not report a lock hash; or `/health` does not report a built image digest, as `sha256:` followed by 64 lowercase hex digits.
  - AC: with a mismatched expected hash, a calculation request returns an error that names the mismatch, and no attempt or result row exists afterwards. With `R_IMAGE_DIGEST` unset, or not in the `sha256:<64 hex>` form, a calculation request is refused, names the missing digest, and writes nothing. The reported lock hash equals SHA-256 of the §2 preimage recomputed from the commit. Shipped `/health` reports only `drc_version` and `r_version`.
- **CALC-REQ-4a [Not built]** R sandbox and secrets (Günter H1, fail closed in his re-review B3). The R container runs as non-root, with a read-only root filesystem and tmpfs scratch, no network egress, and no host port. It has CPU, memory, and PID limits, and a per-request timeout enforced in both R and the backend. No database URL, credentials, or secrets are in the container, in image layers, or in build args. On `main` at `8e327c2`, `docker-compose.yml` already omits a host `ports:` block for `r-calculator` and sets no environment on that service. The Dockerfile has no `USER`. There is no read-only root, tmpfs, egress deny, or resource limit, and Plumber enforces no per-request timeout. The backend fit client times out at 60 s (`FIT_TIMEOUT_SECONDS` in `backend/app/services/r_calculator_client.py`), and the shipped R code bounds its profiled confidence interval at 5 s.
  - **Timeouts (default, Marc to confirm; OQ-CALC-16):** R stops a request after 50 s of wall-clock time. The backend stops waiting after 60 s, matching the shipped `FIT_TIMEOUT_SECONDS`. R's limit is shorter, so on a slow call R normally stops first and reports `r_timeout`. The backend's `backend_timeout` covers an R process that does not answer at all.
  - **Self-attestation:** `GET /health` reports a `sandbox` object measured inside the container at the time of the call:
    - `uid`: the process uid.
    - `root_read_only`: whether `/proc/self/mountinfo` shows the `/` mount as `ro`. A write probe alone is not enough, because a non-root process cannot write to `/` even on a writable root.
    - `scratch_tmpfs`: whether the scratch path is a tmpfs mount.
    - `egress_blocked`: whether an outbound connection probe fails.
    - `cpu_limited`, `memory_limited`, `pids_limited`: whether `cpu.max`, `memory.max`, and `pids.max` under `/sys/fs/cgroup` are set to a value other than `max`.
    - `forbidden_env_absent`: whether the environment has no `DATABASE_URL` and no name ending in `_KEY` or `_SECRET`.

    The backend checks that object at startup and again on every calculation call, together with the lock check (CALC-REQ-4). The backend never gets the Docker socket and never calls Docker. `docker inspect` is used only in deploy and CI, as the independent check that the container's real configuration matches what it reports.
  - **Fail closed:** the backend refuses every calculation call and writes nothing when any of these is true: the `sandbox` object is missing; any of its fields is missing; `uid` is 0; or any boolean is false.
  - **Timeout stop:** a timeout in R or in the backend stops that stage. It stores no result: no output value and no partial stage output. The calculation attempt (§2) still records status stopped and the system code `r_timeout` or `backend_timeout` (CALC-REQ-25). Those codes are not a user-entered reason (CALC-REQ-36).
  - AC: from inside the running container, an outbound connection attempt fails, a write outside the tmpfs scratch fails, and the process uid is not 0. The container environment, the image history, and the build args have no `DATABASE_URL`, no variable whose name ends in `_KEY`, and no variable whose name ends in `_SECRET`. `/health` reports every `sandbox` field, with each boolean true and `uid` not 0. With any field false, missing, or `uid` 0, a calculation call is refused and writes no attempt and no result. The backend container has no Docker socket mounted (no `/var/run/docker.sock`). In deploy and CI, `docker inspect` shows a read-only root filesystem and CPU, memory, and PID limits. An R call that runs past 50 s leaves an attempt with status stopped, `r_timeout`, and no result. A backend wait past 60 s leaves an attempt with status stopped, `backend_timeout`, and no result.

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
  - Stop rule: the function never extrapolates. The range is the observed arithmetic-mean response of the lowest-concentration used calibrator and of the highest-concentration used calibrator. A response outside that span has no numeric concentration. Past the high-concentration calibrator's mean, the qualifier is `>`, the result is flagged, and the UI prompts dilute and rerun. Past the low-concentration calibrator's mean, the qualifier is `<` and the result is flagged. The text after `<` or `>` is lab-set (OQ-CALC-11). Gates that read this result use CALC-REQ-37.
  - AC: a KAT sample inside the range back-calculates within tolerance. On `backend/tests/fixtures/elisa/IL6-PLT-0001_Gen5.csv`, IL6-SER-0007 has corrected OD 2.608 and 2.536 (mean 2.572) and STD-S1 has corrected OD 2.058 and 2.089 (mean 2.0735). IL6-SER-0007 is `>` with no numeric concentration. It is not a back-calculated number, including not about 499.6 pg/mL.

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
  - AC: EL 0.5 EU/mg, 10 mg/mL, λ 0.001 EU/mL gives MVD 5000 (STE-1.2 §6 example). No EL gives 500 with the dose-unknown marker. A dilution equal to the MVD is allowed (CALC-REQ-37). A dilution of 10000 against MVD 5000 is refused.
- **CALC-REQ-12 [Not built]** `lal_kinetic_standard_curve` v1: linear regression of log10(onset time) on log10(calibrator concentration).
  - Inputs: calibrator nominal concentration in EU/mL, onset time in s, replicate identity.
  - Outputs: slope (unit `1`, expected negative), intercept (unit `1`, label `log10(s)`), correlation coefficient r (unit `1`), calibrators used and dropped (count and identity).
  - Points: each used calibrator level enters the regression once. The y value is log10 of the arithmetic mean of that level's replicate onset times, in s. The x value is log10 of the nominal concentration, in EU/mL. Individual tubes are not separate points. The negative control, 0 EU/mL, is never a point.
  - Basis: STE-1.2 §8.1 says only that linear regression builds the curve. Log-log is **USP practice**, not SOP text. Confirming log-log is OQ-CALC-3.
  - Missing-data rule: a calibrator tube with no onset time is excluded and counted; a calibrator level with no tubes left is dropped.
  - Stop rule: a calibrator concentration ≤ 0, or a replicate onset ≤ 0 that would enter the mean, stops the curve. Nothing is passed to log10. The system code is `non_positive_log_input`. It is not a user-entered reason (CALC-REQ-36). Curve acceptance is CALC-REQ-13.
  - AC: a KAT with four calibrators and known onset times reproduces slope, intercept, and r within tolerance, and the slope is negative. The fit matches the arithmetic level means, not one point per tube. A 0 EU/mL negative control does not change the fit. A concentration or onset of 0 stops the curve with `non_positive_log_input` and stores no slope.
- **CALC-REQ-13 [Not built]** Curve acceptance (STE-1.2 §8.2, §8.3, §8.5). The engine tests **|r| ≥ 0.980**, because r is negative for this curve. At least three calibrators must remain. **Stop rule:** |r| < 0.980, or fewer than three calibrators, fails the curve, and the run is to be repeated (§8.5). No sample result is computed on a failed curve.
  - Dropping calibrators: STE-1.2 §8.2 states the minimum of three. It does not itself spell out a dropping procedure. This Spec allows a calibrator to be dropped while at least three remain, as the brief directs; confirming that reading is OQ-CALC-4. A drop is a recorded exclusion (CALC-REQ-27), never silent.
  - AC: r = −0.985 with four calibrators passes. r = −0.975 fails with "repeat run". r = −0.97995 fails: |r| is compared unrounded to 0.980 (CALC-REQ-37), so rounding to three decimal places first, which would show 0.980, does not pass. Dropping one of four calibrators leaves three and the curve is evaluated; dropping two is refused.
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
  - Inputs: curve (CALC-REQ-12), arithmetic mean of the replicate onset times in s, dilution factor (unit `1`), sample concentration in mg/mL.
  - Outputs: measured concentration in EU/mL, concentration corrected for dilution in EU/mL, result in EU/mg.
  - Missing-data rule: no onset by the cutoff is **not missing** (CALC-REQ-20). No dilution factor or no sample concentration gives no EU/mg value and a "missing input" flag.
  - Stop rule: an onset outside the range in CALC-REQ-9 is not extrapolated. Shorter than the mean onset of the highest-concentration used calibrator is `>` (above the top), flagged, with a dilute-and-rerun prompt, and no numeric concentration. Longer than the mean onset of the lowest-concentration used calibrator, while still before the cutoff, is `<` (below the bottom), flagged, and no numeric concentration. That `<` is not "not detected". Not detected remains no onset by the cutoff (CALC-REQ-20). The text after the qualifier is OQ-CALC-7.
  - AC: a KAT onset time between the endpoint calibrator means back-calculates within tolerance, and the EU/mg value equals EU/mL × dilution ÷ mg/mL. An onset past either end stores no number. An onset past the slow end but before the cutoff is `<`, and it is counted as a result, not as missing.
- **CALC-REQ-18 [Not built]** `lal_spike_recovery` v1: recovery % = (spiked − unspiked) / 0.05 × 100. Both values are the measured in-tube concentration in EU/mL at that dilution, not the dilution-corrected concentration. 0.05 EU/mL is the nominal in-tube spike (STE-1.2 §5.3). The formula is **USP practice, not in the SOP**; STE-1.2 §8.8 gives the acceptance range only. Confirming the formula is OQ-CALC-6.
  - Output: recovery in `%`.
  - Acceptance (STE-1.2 §8.8, §8.9): 50–200% inclusive passes (CALC-REQ-37). Below 50% means inhibition; above 200% means enhancement or contamination. **Stop rule:** outside 50–200%, that sample's result at that dilution is invalid and is not passed to pass/fail.
  - Missing-data rule: no spiked value gives no recovery and the dilution is not reportable. An unspiked value that is not detected is handled per OQ-CALC-7.
  - AC: spiked 0.06 EU/mL and unspiked 0.01 EU/mL, in-tube, give the unrounded decimal 100. Spiked 0.026 and unspiked 0.001 give exactly 50 and pass. Spiked 0.171 and unspiked 0.071 give exactly 200 and pass. A binary value of 49.99999999999999 where the decimal is 50 does not fail. A difference of 0.02 EU/mL (40%) marks the dilution invalid for inhibition; a difference of 0.12 EU/mL (240%) marks it invalid for enhancement or contamination. A dilution-corrected pair is not the input.
- **CALC-REQ-19 [Not built]** `lal_sample_pass_fail` v1: a sample passes if its EU/mg result is at or below EL (STE-1.2 §9.1).
  - Inputs: result in EU/mg, EL in EU/mg.
  - Output: pass or fail.
  - Missing-data rule: no EL gives no pass/fail (the MVD default in CALC-REQ-11 does not supply an EL).
  - Qualified results (§2): each is compared using its stored limit L in EU/mg, with the bounds in CALC-REQ-37.
    - `not_detected` (no onset by the cutoff) and `below_range` (detected, below the low-concentration end): L ≤ EL passes. L > EL gives no pass/fail, flagged `limit_above_el`, because the true value can lie either side of EL.
    - `above_range` (past the high-concentration end): L ≥ EL fails, because the true value is above L. L < EL gives no pass/fail, flagged `limit_below_el`, with a dilute-and-rerun prompt.
    - L itself is lab-set (OQ-CALC-7). Until OQ-CALC-7 is decided, a qualified result has no L and gives no pass/fail, flagged `limit_undecided`.
    - `not_detected` and `below_range` use the same rule but stay distinct stored kinds.
  - Stop rule: an invalid dilution (CALC-REQ-16, CALC-REQ-18) or a failed run (CALC-REQ-13, CALC-REQ-16) gives no pass/fail.
  - AC: 0.3 EU/mg against EL 0.5 EU/mg passes; 0.5 passes; 0.6 fails; a failed run gives no pass/fail. With an L supplied as a test input:
    - `not_detected` with L 0.4 against EL 0.5 passes.
    - `below_range` with L 0.4 against EL 0.5 passes and stays stored as `below_range`, not `not_detected`.
    - `not_detected` with L 0.6 against EL 0.5 gives no pass/fail and `limit_above_el`.
    - `above_range` with L 0.5 against EL 0.5 fails.
    - `above_range` with L 0.4 against EL 0.5 gives no pass/fail and `limit_below_el`.
    - With no L, every qualified result gives no pass/fail and `limit_undecided`.
- **CALC-REQ-20 [Not built]** Not detected. No onset by the cutoff (7200 s by default, STE-1.2 §7.4) is reported as `<` (not detected): a below-limit result with a qualifier, **not missing data**. STE-1.2 §7.4 notes that some lysate lots need a longer time (for example 9600 s); the cutoff is a configuration input in s, not a constant (OQ-CALC-10). The number reported after `<` is lab-set (OQ-CALC-7).
  - AC: a tube with no onset at 7200 s produces a `<` result, is counted as a result, and is never shown or counted as missing.
- **CALC-REQ-21 [Not built]** Run-level QC summary. A LAL run records pass or fail with the failing reason code: curve |r|, fewer than three calibrators, calibrator %CV, QC %CV. A failed run produces no sample pass/fail. QC accuracy against nominal and a numeric negative-control limit are lab-set and are not in v1 (OQ-CALC-1, OQ-CALC-2).
  - AC: each failing condition produces its own reason code on the run summary; a run that fails any of them shows "repeat run" and no sample pass/fail.

### 3.6 Closed catalog and no-code builder

- **CALC-REQ-22 [Not built]** The catalog is closed. Version 1 contains exactly: `elisa_4pl_standard_curve`, `elisa_4pl_back_calc`, `lal_endotoxin_limit`, `lal_mvd`, `lal_kinetic_standard_curve`, `lal_back_calc`, `percent_cv`, `lal_spike_recovery`, `lal_sample_pass_fail`. Each entry declares name, version, every input and output with its unit, its missing-data rule, its stop rule, and its KATs. Shipped dose-response `fit_compound` is not in the catalog until it is brought under these rules. The catalog changes only through a PR-reviewed code change (Günter H2). It never changes through the API, the UI, a database row, runtime config, or the agent. None of those paths can add a function or enable a version.
  - AC: the catalog lists exactly these nine entries, each with every declared field filled. An attempt to add or enable an entry through the API, the UI, a database write by the application role, runtime config, or an agent run is refused, and the catalog is unchanged. A new entry appears only after a reviewed pull request that changes the catalog in code is merged.
- **CALC-REQ-23 [Not built]** Calculations are configured only in a no-code builder: pick catalog functions, bind each input to a run column, an upstream stage output, or a constant, each with its unit. There is no expression language and no free-text formula.
  - AC: the builder offers only catalog functions; there is no text field that accepts a formula or code.
- **CALC-REQ-24 [Not built]** **Prohibited:** user code, scripts, plugins, a webhook runtime, and any generic "run R" (or run-any-code) endpoint. The R service exposes `/health`, one route per catalog function, and the pre-existing dose-response routes `POST /fit` and `POST /svg/full`. Those two stay, because dose-response on `main` calls them (`backend/app/services/r_calculator_client.py`). They stay until `fit_compound` is brought under these rules. No other route. A new route that runs caller-supplied code, or that accepts an unknown function or model name, is refused and does not fall back to a default.
  - AC: `POST /fit` and `POST /svg/full` still answer a dose-response call. A call to any other non-catalog path, or a body carrying code, is refused. A new route that is given an unknown model name is refused and does not run `LL.4`. Shipped `fit_compound` still silently substitutes `LL.4` for an unknown model name; that stays a defect of the existing route, and this rule forbids it on every route added for the catalog.

### 3.7 Stop rules, missing data, units

- **CALC-REQ-25 [Not built]** Every stage has a stop rule. When a stage stops, no later stage that depends on it runs. The stop and its reason code are recorded on the calculation attempt (§2), even when the stop leaves no result, as a timeout does (CALC-REQ-4a). A refusal before the call is accepted is different. A lock mismatch (CALC-REQ-4) or a sandbox failure (CALC-REQ-4a) writes no attempt.
  - AC: for each catalog function, a KAT case triggers its stop rule and shows that dependent stages did not run.
- **CALC-REQ-26 [Not built]** Every formula has a missing-data rule. Missing input is never imputed, never zero, and never silently dropped. A below-limit (`<`) value is not missing.
  - AC: for each catalog function, a KAT case with a missing input shows the declared outcome.
- **CALC-REQ-27 [Partly shipped]** An excluded point (knockout or calibrator drop) is a recorded exclusion with who and when, and is reversible by recording a new calculation result. Shipped: `lims_run_data_exclusions` records `excluded_by`, `excluded_at`, and an optional reason for dose-response points. Not built: the same for ELISA and LAL calibrators and replicates.
  - AC: after a calibrator drop, the calculation result lists the dropped calibrator, the user, and the time.
- **CALC-REQ-28 [Not built]** Units are explicit on every input and every output, using the `units` table. Percentages use the existing `%`. The table gains an additive seed for `OD` (type `absorbance`), `s` (type `time`), `EU/kg` (type `endotoxin_per_body_mass`), `EU/mg` (type `endotoxin_per_mass`), `mg/kg` (type `dose`), and `1` (type `dimensionless`). Each of those six is multiplier 1 in its own type. None shares a type with `EU/mL` (type `activity`, migration `0092_concentration_unit_scales`) or with `mg/mL` (type `concentration`), so none converts onto those. The log-log intercept is unit `1` with label `log10(s)`, not a unit named log10 s. A binding whose unit does not match the function's declared unit (after a defined conversion within the same unit type) is refused at configuration time.
  - AC: the six names exist, each in the type named above. Binding a mg/kg value to an input declared in EU/mL is refused. `EU/kg` does not convert to `EU/mg` or to `EU/mL`. Every stored output carries its unit. Shipped: `concentration_unit` is sent to R and unused, and `dose_response_results` has no unit column. The six names are not in the seeded units at `8e327c2`.

### 3.8 Immutability, pinning, recompute

- **CALC-REQ-29 [Not built]** A released function version is immutable. Any change to a formula, default, tolerance, unit, stop rule, or missing-data rule is a new version. A released version is never edited or deleted.
  - AC: an edit to a released version is refused; the same change saved as a new version succeeds and the old version is unchanged.
- **CALC-REQ-30 [Not built]** Every calculation result records the function name and version of every stage, the lock hash it ran on, and the built image digest recorded alongside that hash (§2). The built digest is always present, because a call without it is refused (CALC-REQ-4). The function version and the built digest are not inputs to the lock hash.
  - AC: a stored result shows each stage's function version, the lock hash, and the built image digest. The lock hash matches `/health` at the time it ran. The built digest may differ from the base digest inside the lock hash.
- **CALC-REQ-31 [Partly shipped]** No silent recompute. A recompute is an explicit, recorded new result that links to the result it replaces and records who triggered it, when, and why it ran (knockout, new version, new lock). The old result is kept. Shipped: a dose-response refit writes a new row with `fit_version + 1` and `superseded_by`. Not built: lock hash and function version on that row; the same rule for ELISA and LAL; and the PDF SVG path, which re-fits on all points without the stored constraints instead of drawing the stored result.
  - AC: after a recompute, both results exist and the new one links to the old one. Opening, exporting, or reporting a result never runs a calculation.
- **CALC-REQ-32 [Not built]** A new lock hash never rewrites results made on an earlier one. Recomputing on the new lock is an explicit recompute (CALC-REQ-31).
  - AC: after a lock change, every earlier result still shows its original lock hash and values.

### 3.9 Releases

- **CALC-REQ-33 [Not built]** Releases are calculation-scoped: one release names the functions it adds versions for, their KATs, and the lock hash. A release is additive (adds versions, never removes or edits one) and incremental (it depends only on releases it names; other calculations are untouched).
  - AC: releasing a new `lal_mvd` version leaves every ELISA function version and every earlier `lal_mvd` version available and unchanged.

### 3.10 Agent proposes, a named person activates

- **CALC-REQ-34 [Not built]** The configuring AI agent may propose a calculation configuration (functions, bindings, constants, units) through the builder. It cannot activate one, and it cannot change the catalog (CALC-REQ-22). Shipped: the agent's allow-list refuses `/v1/lims-runs` ("Run analysis and dose-response are not configuration"); this Spec does not change that for running fits. Activation is refused server-side for every agent run context, including bulk, apply, and import (Günter H2). The refusal is both the allow-list and a check on the activation route. An agent proposal does not carry an activation. A separate interactive request (Günter re-review B1) means all of the following. The activate route requires a single-use confirm token. The activate dialog issues that token. Password re-entry is not required on top of the confirm token (default, Marc to confirm; OQ-CALC-17). The token is valid for 5 minutes from issue and then expires. The route refuses any request that carries a configuring-agent run context, even when the request uses that same person's access token and a fresh confirm token. The confirm token is random, stored server-side hashed, bound to the user, the proposal id and the session, and consumed atomically in the activation transaction. The token-issuing step refuses any configuring-agent run context, and the confirm route is not on the agent allow-list, so the agent can neither obtain nor send a token. Agent run context is set by the server's agent executor, never by a client header or field. Who may send the interactive request is CALC-REQ-35.
  - **Session.** In this rule, "the session" is the login session, identified by the `jti` claim of the access token that requested the confirm token. `create_access_token` in `backend/app/core/security.py` sets that claim. The backend has no other session entity and no refresh tokens. A token used with an access token whose `jti` differs is refused. That covers a new login, and an access token whose `jti` has been revoked by logout. The configuring-agent run is a different thing, called the "agent run" here and in CALC-REQ-35.
  - **Window.** The server clock is used both when the token is issued and when it is checked: the database `now()` in the issuing and activation transactions. The token is valid while now − issued_at ≤ 300 s, so exactly 300 s passes and 300 s plus any further time is refused. No client clock is read.
  - **Rollback.** Consumption is part of the activation transaction. If that transaction commits, the token is consumed. If it rolls back for any reason, the token stays unconsumed and can be used again within its 300 s window. A rolled-back attempt writes no activation row.
  - AC: an agent run can create a proposed configuration. Replaying that person's access token from an agent run is refused, including when the replay carries a fresh confirm token, and no activation row is written. A request with no confirm token is refused and writes no row. A reused confirm token is refused and writes no row. A token checked at 300 s after issue on the server clock is accepted. A token checked at 301 s is refused and writes no row. Bulk, apply, and import paths of an agent run write no activation row. (a) A token issued for proposal A is refused for proposal B, and no row is written. (b) A token issued for session X is refused for session Y, and no row is written. Here session X and session Y are two login `jti` values, including the same user logged in twice. (c) A token request from an agent run is refused. An activation that rolls back after the token check leaves the token unconsumed, and a retry with that token inside the window succeeds. No password field is required on the activate request.
- **CALC-REQ-35 [Not built]** Only an Admin may activate a calculation, enforced server-side (OQ-CALC-14, Decided, Marc, 2026-11-03). Self-activation is allowed (OQ-CALC-15, Decided, Marc, 2026-11-03): an Admin who proposed the configuration, or who started the configuring-agent run that proposed it (the agent run owner, not the login session in CALC-REQ-34), may activate that proposal through the interactive confirm path. The activation row records that Admin as the named person (`created_by = current_user_id()`). The configuring agent is never allowed to activate (CALC-REQ-34). Activation is the interactive confirm path in CALC-REQ-34. It records the person, time, the function versions, the lock hash, and a validation-state value. The validation state is recorded, **not a required gate**: an Admin's activation succeeds whatever the state. The list of state values is OQ-CALC-12. Activation adds no reason field. The activation row is append-only. The database enforces `created_by = current_user_id()`. A forged actor, a `created_by` other than `current_user_id()`, gets SQLSTATE 42501 and no row. UPDATE and DELETE of an activation row are refused the same way. `current_user_id()` already exists (`backend/db/migrations/versions/0003_rls_policies.py`). The activation table does not.
  - AC: (a) a Lab Manager is refused and no row is written. (b) Any other non-Admin role is refused and no row is written. (c) An Admin who completes the interactive confirm path succeeds, for any validation-state value, and the row shows that Admin, the time, the versions, the lock hash, and the state. (d) An Admin who proposed the configuration, or who started the agent run that proposed it, can activate that proposal through the interactive confirm path, and the row records them as the named person. (e) An agent run context is always refused and no row is written. Inserting a row whose `created_by` is not `current_user_id()` fails with SQLSTATE 42501 and stores nothing. UPDATE and DELETE of a stored activation row fail and leave the row unchanged.

### 3.11 Reasons

- **CALC-REQ-36 [Shipped]** This Spec adds **no** required reason field. The only existing required reason it touches is the dose-response reset-fit reason (`reset_fit_reason_required`): 1–4000 characters, refused when missing, blank, or whitespace-only, including NBSP and U+2007 (`backend/app/core/required_reason.py`). The data-point exclusion reason stays optional, shares the 4000 maximum, and a whitespace-only value (including NBSP and U+2007) is not stored as a reason. System codes on a stopped stage (`non_positive_log_input`, `r_timeout`, `backend_timeout`) are not user-entered reasons and have no text field.
  - AC: no route added for this Spec requires a reason. None of those system codes accepts or requires a reason string.

### 3.12 Precision of gates

- **CALC-REQ-37 [Not built]** Gates run in the backend, not in R.
  - **Inputs stay decimal strings.** Every gate input and every gate threshold is carried as a decimal string end to end: from the run data, binding, or constant, through the backend, and in every JSON body. It is never a JSON number and never an R double.
  - **Values that come from R.** R and drc fit outputs (for example slope, intercept, r, 4PL parameters) are binary doubles. R serialises each one as a decimal string with 17 significant digits. The backend parses that string with Python `decimal`. That parsed value is the "unrounded decimal" for a fit output, and it is what is stored and gated.
  - **Arithmetic.** The backend evaluates every gate quantity with Python `decimal`, using a context of precision 50 and rounding `ROUND_HALF_EVEN`. Division, `log10`, and `sqrt` use that context. Within a formula, products are formed first and a single division is done last. MVD is K × sample concentration ÷ (M × λ). Recovery is (spiked − unspiked) × 100 ÷ 0.05. So a quotient that is exact in decimal is exact here.
  - **Bounds are inclusive:** |r| ≥ 0.980, %CV ≤ 25%, 50% ≤ spike recovery ≤ 200%, dilution ≤ MVD, and sample result ≤ EL.
  - **Display.** Rounding is for display only. Each numeric output stores the unrounded decimal and the display precision declared for that output on the catalog entry. Display rounds half away from zero to that precision, and the result records the precision. No gate reads the displayed value. This Spec does not pick a global number of display decimal places.
  - AC: K 5 EU/kg, M 3 mg/kg, sample concentration 3 mg/mL, and λ 0.001 EU/mL give MVD exactly 5000. A dilution of 5000 is allowed. A value of 4999.999…998 from dividing EL first under `ROUND_DOWN`, which would refuse that dilution, fails this rule. |r| = 0.97995 fails the 0.980 gate. Rounding it to three decimal places before the compare, which would show 0.980, is a failure of this rule. Recovery whose decimal value is 50 or 200 passes, including the pairs 0.026 with 0.001 and 0.171 with 0.071. A stored gate result that followed a binary value of 49.99999999999999 where the decimal is 50 fails this rule. Gate inputs in request and response bodies are JSON strings, not JSON numbers; a JSON number in a gate input is refused. A fit output from R arrives as a 17-significant-digit string and is stored as that decimal. The stored row has the unrounded value and the recorded display precision, and the displayed rounding is not what the gate compared.

---

## 4. Open questions

Status labels follow [`.docs/review/open-questions/README.md`](../../../review/open-questions/README.md). OQ-CALC-14 and OQ-CALC-15 are **Decided**. OQ-CALC-16 and OQ-CALC-17 are **Open** with a stated default that applies until Marc confirms or changes it. The rest are **Open**. No open question is given a number here.

| ID | Question | Blocks | Source |
|----|----------|--------|--------|
| OQ-CALC-1 | QC accuracy range (recovery against the 0.05 EU/mL QC nominal). | CALC-REQ-21 | Lab-set; not in STE-1.2 |
| OQ-CALC-2 | Numeric negative-control limit. | CALC-REQ-21 | Lab-set; not in STE-1.2 |
| OQ-CALC-3 | Confirm the curve is log10(onset) vs log10(concentration). STE-1.2 §8.1 says only "linear regression"; log-log is USP practice. | CALC-REQ-12 | STE-1.2 §8.1, USP <85> |
| OQ-CALC-4 | Confirm calibrators may be dropped while at least three remain. STE-1.2 §8.2 states the minimum; who may drop, and on what basis, is not stated. | CALC-REQ-13 | STE-1.2 §8.2 |
| OQ-CALC-5 | %CV: SD with n−1 or n; computed on onset time or on back-calculated concentration. | CALC-REQ-14, 16 | Not stated in STE-1.2 §8 |
| OQ-CALC-6 | Confirm the spike-recovery formula. It is USP practice; STE-1.2 §8.8 gives only the 50–200% range. | CALC-REQ-18 | STE-1.2 §8.8, USP <85> |
| OQ-CALC-7 | The number reported after `<` or `>` (for example λ × dilution ÷ mg/mL), and how a not-detected unspiked value enters spike recovery. The qualifier direction is decided (CALC-REQ-9, CALC-REQ-17). | CALC-REQ-17, 18, 19, 20 | Lab-set |
| OQ-CALC-8 | Handling a missing single tube, or a split duplicate (one tube with onset, one not detected). | CALC-REQ-14, 16 | Lab-set; not in STE-1.2 |
| OQ-CALC-9 | Which of several valid dilutions is reported. | CALC-REQ-16, 17, 19 | Lab-set; not in STE-1.2 |
| OQ-CALC-10 | Onset-time cutoff: fixed 7200 s, or set per lysate lot (STE-1.2 §7.4 allows longer). | CALC-REQ-20 | STE-1.2 §7.4 |
| OQ-CALC-11 | ELISA: blank handling, 4PL weighting, curve acceptance, duplicate %CV limit, kit QC ranges, the number shown after `<` or `>` (the qualifier direction is decided in CALC-REQ-9), and the concentration unit of the IL-6 pack (the synthetic fixture's `Conc/Dil` column has none). | CALC-REQ-8, 9 | Lab-set; IL-6 pack |
| OQ-CALC-12 | The closed list of validation-state values recorded at activation. | CALC-REQ-35 | Product |
| OQ-CALC-13 | Who supplies independent expected values for the IL-6 and LAL KATs. | CALC-REQ-6 | Product / QA |
| OQ-CALC-14 | **Decided (Marc, 2026-11-03).** Only an Admin may activate a calculation, enforced server-side. | CALC-REQ-35 | Marc. Günter's re-review B2 is closed by this answer. |
| OQ-CALC-15 | **Decided (Marc, 2026-11-03).** Self-activation is allowed, because a startup cannot be assumed to have a second person. The proposer, or the owner of the agent run that proposed it, may activate their own proposal. The row records that named person (`created_by = current_user_id()`). The configuring agent can never activate. The person must still be an Admin (OQ-CALC-14). | CALC-REQ-35 | Marc. Günter's re-review B2 is closed by this answer. |
| OQ-CALC-16 | Timeout lengths. **Default, Marc to confirm:** R stops a request at 50 s. The backend stops waiting at 60 s, matching the shipped `FIT_TIMEOUT_SECONDS`. | CALC-REQ-4a | Product. Tobias N2. |
| OQ-CALC-17 | Is password re-entry required on top of the confirm token? **Default, Marc to confirm:** no. The confirm token alone suffices. | CALC-REQ-34 | Product. Tobias N4. |

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

Rolf and Marc are still pending. No stamp is given until the named person gives it.

| Order | Review | Who | Status | Date | Commit |
|-------|--------|-----|--------|------|--------|
| 1 | Security review | Günter | Accept at 6f7288a, CI green required | 2026-11-04 | 6f7288a |
| 2 | Fail bars written | Tobias | Request changes at 6f7288a (draft, not posted on GitHub) | 2026-11-04 | 6f7288a |
| 3 | Confirm | Rolf | Pending | | |
| 4 | Approve | Marc | Pending | | |
