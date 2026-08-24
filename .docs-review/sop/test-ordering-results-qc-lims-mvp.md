# NimbleLIMS SOP pack: test ordering, results entry, QC, LIMS integrity (MVP)

Compiled 20 Aug 2026. Public/standard sources only. Default tenant = research core + optional GxP controls. Do not ship CLIA patient-safety workflows as the default.

**Model this product on:** 21 CFR 211.194 lab records, ISO/IEC 17025 7.8 (review/authorize/amend), NCI Frederick BDP public SOPs 22004/22009, research-core LIMS request flows (UAB, NYU), plus Part 11 / MHRA / WHO / PIC/S data-integrity *controls* (not a “Part 11 certified” claim).

**Do not model MVP on:** hospital requisitions (ICD-10, DOB/sex as required, panic-value call logs), reflex-rules engines, full OOS investigation modules, instrument parsers, EU Qualified Person batch release.

Companion pack: `sample-management-mvp.md`.

---

## 1. Test ordering

### Concrete process

1. Authorized person selects tracked sample(s) + test(s) from a catalog (CLIA 493.1241; UAB/NYU core LIMS; 211.194(a)(1) sample description in the lab record).
2. Required identifiers: sample ID, test(s), requester, request date, collection date/time, specimen type/source.
3. Optional: priority, project/billing, comments. Priority (STAT) appears on hospital forms; **it is not in the CLIA required-field list** and is not a GMP required field.
4. Lab checks sample vs request at accession (condition/disposition belongs on the later report: CLIA 493.1291(c)(7)).

### Panels vs single tests

Hospital forms (Iowa UIDL, UCI) list named panels that explode into tests, plus individual tests, plus “Other.” **No public BioTech SOP for research panels was found.** Common practice: catalog of named methods (endotoxin, HPLC purity, qPCR titer) with optional panel grouping. Do not invent a clinical CMP/BMP catalog.

### Order cancel / modify

**Common practice, no public SOP found** for cancelling after accession. Do not encode a fake standard. Defensible unverified practice (label it as such): cancel only before result entry; after results exist, void/amend with reason; never silent-delete. CLIA documents *add-ons* (oral + written confirmation in 30 days), not cancels. Verbal add-ons are **clinical-only**.

### Repeat / reflex

- **Reflex** is defined in 42 CFR 493.2: automatic additional testing per SOP when pre-established criteria are met. **Clinical. Overkill for startup R&D.**
- **Retest vs resample** is documented for GMP OOS (FDA May 2022; NCI SOP 22004): retest = same sample; resample = new sample; prefer retest; never “test into compliance”; keep the original OOS value.
- MVP: linked repeat/retest on an existing sample with a reason; original result stays. Full Director-gated OOS retest protocol = GMP-path, not day-1.

### LIMS fields on an order (MVP)

Sample ID, test(s) from catalog, requester, request datetime, collection datetime, specimen type, comments. Do **not** require diagnosis/ICD, sex, or DOB for research/GMP tenants.

### UAT notes

- Cannot order against an unknown sample ID.
- Catalog test is required (free-text “other” is optional and should be confirmable).
- Cancel after a reported result is blocked or becomes an amendment, not a hard delete.
- Repeat creates a linked order; original result remains visible.

---

## 2. Results entry

### Concrete process

1. Evaluate system suitability / controls **before** reporting assay results (NCI SOP 22004 §6.3.1; CLIA 493.1256(f) for patient results; UC Davis PCR core: failed pos/neg control invalidates associated samples).
2. Enter result contemporaneously: value (numeric **or** qualitative), unit from catalog, analyst, system-stamped datetime (211.160(a); FDA data-integrity Q&A 2018).
3. Attach or file original printout/file when the instrument does not store (PIC/S PI 041 §8.9). Instrument auto-file is **not** a public mandate; Annex 11 allows manual entry with a second check. Parsers are out of NimbleLIMS MVP scope.
4. Optional spec comparison → pass/fail/unknown. ISO 17025 7.8.6 conformity statements need a documented decision rule (uncertainty) — **overkill for startup R&D**.
5. Second person reviews for accuracy, completeness, calculations, method, QC (211.194(a)(8); ISO 17025 7.8.1.1). Reviewer ≠ performer. Return to analyst if incomplete (NCI SOP 22009).
6. Release/report only after review/authorization, and only to authorized recipients (ISO 7.8.1.1; CLIA 493.1291(f)).

Second-person review is a **GMP/ISO predicate**, not a CLIA-minimum phrase for every result. For NimbleLIMS: tenant-configurable; **default on for GxP-ready**, off allowed for pure R&D.

### Units, qualitative vs quantitative

- Result **and units** where applicable (CLIA 493.1291(c)(6); ISO 7.8.2.1; WHO: a number without a unit is meaningless).
- Qualitative: pos/neg or pass/fail/NA (CLIA 493.1256; NCI).
- Significant figures: PIC/S says be consistent on rounding. **No public method-level sig-fig SOP found.** Method SOP owns reportable digits; LIMS must not silently round away from the method.

### Amendments

- After a report is **issued**: keep the original, issue a corrected report, identify the change and reason (CLIA 493.1291(k); ISO 17025 7.8.8).
- Silent overwrite is non-compliant.
- A transcription fix *before* issue is an audited change, not necessarily a “corrected report.”
- Notify requester is a **lab process**; LIMS can log it. Email send is not required at MVP.

### Result status (synthesis, not a fake SOP)

**No public SOP names** `{entered, reviewed, reported, amended}`. Closest sourced states: contemporaneous documentation → second-person review → authorized release → original+corrected retained. Also: invalidated (OOS lab error), cancelled (order).

Defensible mapping: **Ordered → In testing → Entered → Reviewed → Reported → Amended**, plus **Cancelled** and **Invalidated**. Never drop original values on status change.

### UAT notes

- Analyst cannot review their own result when the GxP gate is on.
- Reported results cannot be edited in place; amendment creates a new version linked to the old one.
- Both original and amended reports remain retrievable.
- Result without a unit is allowed only for coded qualitative values.
- System timestamp is not user-editable without an audit trail.

---

## 3. QC (what actually gates release)

### Concrete process

- QC materials (blanks, controls, standards) exist as samples/results.
- CLIA 493.1256(f): control results must meet acceptability **before reporting patient results**.
- NCI 22004: report assay results only after system suitability and controls are acceptable. If the reference standard fails suitability, do not analyze test samples until resolved.
- UC Davis PCR core: failed positive control → associated samples invalid (false-neg risk); failed negative/blank → associated samples invalid (false-pos risk).
- CA DPR chemistry: spike OOS may require reanalysis of the associated set.
- Instruments not meeting calibration specs shall not be used (211.160(b)(4)).

A technical hard-block in LIMS is a **good control** (WHO prefers technical over procedural). The regulation binds the laboratory, not the software vendor. MVP: optional “block report if associated QC failed” (on for GxP/CLIA tenants).

### OOS / OOT (do not become a QMS)

FDA OOS guidance (May 2022) and NCI SOP 22004 are real, public, and detailed. They are **post-MVP**.

MVP must:
- Flag result vs spec (pass/fail/unknown).
- Prevent silent delete of failing results (WHO Example 4: all data stay unless documented scientific justification).
- Reason field + link to an external investigation ID.

Do **not** build Phase I/II workflows, Material Review Board, or stability regression. A LIMS should not pretend to be a QMS.

Westgard multi-rules, control charts, lot-to-lot QC: **overkill**. CLSI C24 is paywalled and was not used.

### UAT notes

- Reporting is blocked or warned when the run’s QC failed (when the switch is on).
- A failing result remains visible after a passing retest.
- QC samples are filterable and linkable to the associated unknowns.

---

## 4. LIMS usage / data integrity

These are **record** rules. Research-only records with no FDA predicate rule are outside Part 11. If a customer later uses the LIMS as the official 211/58 record, the data model must already avoid silent overwrites, shared logins, and missing audit trails.

### What MVP must support (sourced)

| Control | Source | LIMS implication |
|---|---|---|
| Unique users, no shared accounts | Part 11 11.10(d); WHO 11.9; PIC/S 9.5 | Unique logins |
| RBAC / authority checks | 11.10(g); ISO 6.2.6 | Analyst vs reviewer vs admin vs requester |
| Enter ≠ review | 211.194(a)(8); PIC/S 8.8 / 9.3 | Reviewer cannot be the performer (configurable) |
| Append-only audit trail: old/new, who, when | 11.10(e); OECD 22; WHO; Annex 11 §9 | Immutable log; reason on GxP change/delete |
| Contemporaneous timestamps | 211.160(a); FDA DI Q&A; ALCOA | Server time; users cannot set the clock |
| Original + complete (including fails) | WHO Ex. 4; PIC/S ALCOA+ Complete | No delete of failing injections/results |
| Export/print of records | 11.10(b); ISO 7.8 | Human-readable copy |
| Spec limits as locked master data | WHO Example 11 | Change control on catalog specs |
| Inactivated users remain | WHO 11.6 | Disable, do not erase |

### ALCOA+ mapped to LIMS (MHRA 2018, WHO TRS 1033 Annex 4, PIC/S PI 041, FDA 2018)

Attributable, Legible, Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available. Practical bar: unique user on every order/result/review/amendment; native values stored; no backdating without trail; failing data kept; catalog-driven units; records survive sample destruction (see sample-management pack).

### Part 11 / Annex 11 — later, not fake on day 1

Real, sourced, **post-MVP**: e-signature with meaning (review/approval/authorship) and re-auth (11.50, 11.200); signature bound to the record (11.70); printouts that show if data changed since original entry (Annex 11 §8.2); validated backup/restore evidence pack.

**Do not claim “21 CFR Part 11 certified.”** FDA does not certify software. EU Annex 11 **2011** is in force; the 2025 draft is not.

### Roles (MVP)

Admin (no routine data entry via admin), Analyst (enter), Reviewer (authorize; cannot review self when GxP on), Requester (read/order). Do not ship a shared lab login. EU Qualified Person is manufacturing-only, not MVP.

### ISO 17025 / OECD GLP (configuration still needs validation)

ISO 17025 7.11.2: LIMS shall be validated for functionality, including interfaces, before introduction; config changes to COTS authorized, documented, validated. OECD GLP No. 17 names LIMS; No. 22 requires who/what/when/why audit trails and time zone. Official ISO text is paywalled; clauses above are from public accreditation training, not a pirated copy.

### UAT notes

- Shared account creation is rejected.
- Audit log cannot be edited by admin.
- Changing a reported result requires a reason and leaves the old value.
- Disabled user still appears on historical actions.
- Spec-limit edits are audited and, once locked, not casually editable.

---

## 5. End-to-end workflow (synthesis)

Stitched from NCI 22002/22004/22009 + 211.194 + ISO 7.8 + CLIA 493.1241/1291, stripped of patient-care fields:

1. **Request** — sample(s) + catalog test(s) + requester + dates.
2. **Accession** — receipt vs request; reject/flag unacceptable (see sample-management pack).
3. **Perform** — QC/suitability first; contemporaneous result + units + analyst + stamp; attach raw data.
4. **Review** — second person; return if deficient.
5. **Report** — only after authorize; unique report ID; retain issued report.
6. **If fail/OOS** — do not hide; keep original; investigation lives outside LIMS at MVP.
7. **If error after report** — amend; keep original; reason; notify.

---

## 6. Edge cases named in the sources

- Verbal/add-on orders need later written confirmation (**clinical**).
- Transcription into LIS must be accurate (493.1241(e)); Annex 11 second check for critical manual entry.
- Thermal printouts fade — keep a true copy (PIC/S 8.9–8.10).
- Testing into compliance / unlimited retests until pass is an FDA warning-letter pattern.
- HPLC individual injection vs method-defined average as the reportable result (FDA OOS 2022).
- Customer-supplied data on ISO reports must be identified; “results apply to the sample as received” if the lab did not sample (7.8.2.2).
- Hybrid paper+LIMS is called out as high risk (MHRA/WHO).
- Time zone on timestamps (OECD 22).
- COTS configuration changes require re-validation (ISO 7.11.2).

---

## 7. What not to invent

| Topic | Finding |
|---|---|
| Order cancel/modify SOP | Common practice, no public SOP found |
| Named four-state result enum | Common practice, no public SOP found |
| Priority as a required field | Not in 493.1241; hospital STAT forms only |
| Sig-fig / rounding engine | PIC/S “be consistent” only |
| Instrument auto-file mandate | Not found |
| Full NCI SOP 22002 field list | Referenced; PDF not retrieved this pass — do not invent it |
| CLSI GP19 / C24, USP chapters, GAMP 5 book | Paywalled; not cited beyond public GAMP category summary |
| GDP for lab tests | Not applicable (medicinal-product distribution) |

---

## 8. MVP vs later vs wrong segment

**MVP (will not paint a later GMP customer into a corner):** unique users + RBAC; test catalog; order against tracked samples; manual result entry with units and attachments; entered → reviewed → reported; original+amended; append-only audit trail; optional second-person gate; QC samples + optional block-on-QC-fail; server timestamps; export.

**GxP-path later:** Part 11 e-signatures with meaning + re-auth; OOS module; reflex engine; instrument interfaces; audit-trail review workspace; 17025 uncertainty/decision rules; validated backup evidence pack.

**Wrong default:** CLIA patient demographics, ICD-10, panic values, hospital downtime requisitions, EU QP certification, “Part 11 certified” marketing.

---

## Primary sources

- 21 CFR Part 11 (CFR 2025 ed.); FDA Part 11 Scope and Application (2003); FDA Data Integrity Q&A (2018)
- 21 CFR 211.68, 211.160, 211.192, 211.194
- FDA Investigating OOS Test Results, Rev. 1 (May 2022): https://www.fda.gov/media/158416/download
- 42 CFR 493.1241, 493.1256, 493.1291
- NCI Frederick BDP SOP 22004 OOS/OOT: https://frederick.cancer.gov/media/2083/download?ext=pdf
- NCI Frederick BDP SOP 22009 QA review of analytic test records
- MHRA GxP Data Integrity (2018): https://www.gov.uk/government/publications/guidance-on-gxp-data-integrity
- WHO TRS 1033 Annex 4 (2021)
- PIC/S PI 041-1 (1 Jul 2021): https://picscheme.org/docview/4234
- EU GMP Annex 11 (2011, in force)
- OECD GLP No. 17 (2016) and No. 22 (2021)
- ISO/IEC 17025:2017 clauses via public accreditation training (standard itself paywalled)
- UAB / NYU core LIMS request procedures; UC Davis PCR QA/QC (2023); UW Medicine / Iowa / OHSU requisitions (clinical comparison only)
