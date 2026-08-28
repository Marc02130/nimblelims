# Working note: `analysis_param_defs` (example data for table design)

**Date:** 2026-08-28  
**Status:** Working note (not a house SOP; **not seed**)  
**Stem:** `post-receive-work-spine`  
**Why this file:** Domain PRD/SPEC live under gitignored `.docs/internal/` and are **not on git**. Do **not** invent an internal tree. Documentarian folds this into `.docs/internal/prd/post-receive-work-spine/PRD.md` and `.docs/internal/specs/post-receive-work-spine/SPEC.md` when the host is back.

**Related (committed):**  
- [requirements](../review/requirements/post-receive-work-spine.md) (RQ-AF-6, RQ-WO-11 / L3)  
- [schema-changes](../review/schema-changes/post-receive-work-spine.md)  
- [tech-sketch](../review/tech-sketch/post-receive-work-spine.md)  
- OQ-AF-3 (table ships; OOB may have zero defs)  
- WO-7 / L3 / SC5: params freeze at **LimsRun start**, not receive, not result fields  

**Audience:** Heidi (table design). Every `analysis_code`, allowed value, and snapshot number below is **example data**.

---

## 1. Timing lock (normative)

| Layer | What | Not |
|-------|------|-----|
| Receive | Identity + vessels | No params, no Tests, no results |
| Asked-for (P1) | May hold `params` JSON matching defs | Not a Test; capture stays parked |
| **LimsRun start (WO-7)** | Snapshot asked-for `params` onto the Test and **freeze** | Not receive; not publish; not result columns |
| Results (P3) | Fitted / reported values | **Not** method params |

**Not params (results — do not catalog, do not snapshot):** fitted IC50, Hill, % remaining, CLint, fu.

**Not this note:** house SOP, extra assays, seed rows, Field Management UI, OOB catalog contents.

---

## 2. `analysis_param_defs` catalog — example rows (one per param key)

Column sketch for Heidi (maps to schema `analysis_id` FK, `key`, `data_type`, `required`, optional `source_list_id`, `sort_order`):

| Column | Meaning |
|--------|---------|
| `analysis_code` | **Example** analysis label (not a seed code, not an OOB id) |
| `param_key` | Catalog `key` — **Katinka sourced keys only** |
| `value_type` | Example `data_type` |
| `unit` | Display unit (empty if dimensionless / enum / bool / text) |
| `required` | Catalog `required` |
| `allowed_values` | Enum / list sketch; empty = free text or unconstrained number |
| `notes` | When the key applies |
| `source` | Public source (not house SOP) |

`analysis_code` values are **example grouping labels** so one analysis can own its keys. They are not inventory.

### 2.1 Safety, Toxicology & Secondary Pharmacology

#### Example analysis `EX_hERG` — hERG (ICH S7B)

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_hERG | `temperature_C` | number | °C | yes | | Method temp at run start | [ICH S7B](https://database.ich.org/sites/default/files/S7B_Guideline.pdf) |
| EX_hERG | `voltage_protocol` | text | | yes | | Protocol name/label; not a fitted result | ICH S7B |
| EX_hERG | `stim_freq_Hz` | number | Hz | yes | | Stimulation frequency | ICH S7B |
| EX_hERG | `cell_line` | text | | yes | | Expression system | ICH S7B |

#### Example analysis `EX_AMES` — Ames (OECD 471)

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_AMES | `strain` | text | | yes | | Tester strain | OECD 471 |
| EX_AMES | `s9_activation` | bool | | yes | true \| false | Metabolic activation | OECD 471 |

#### Example analysis `EX_2ND_PHARM` — 2nd pharmacology

Catalog keys only. **No Katinka filled snapshot** in §3.

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_2ND_PHARM | `target_id` | text | | yes | | Target identifier | 2nd pharm (sourced key list) |
| EX_2ND_PHARM | `assay_mode` | text | | yes | agonist \| antagonist \| binding | Mode of the assay | 2nd pharm (sourced key list) |

### 2.2 DMPK & ADME (AGM NBK326710)

#### Example analysis `EX_DMPK_MIC` — microsome metabolic stability (CYP)

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_DMPK_MIC | `species` | text | | yes | | Donor species | [AGM NBK326710](https://www.ncbi.nlm.nih.gov/books/NBK326710/) |
| EX_DMPK_MIC | `matrix` | text | | yes | microsome \| hepatocyte \| plasma | Incubation matrix | AGM NBK326710 |
| EX_DMPK_MIC | `protein_conc_mg_ml` | number | mg/mL | yes if `matrix=microsome` | | Microsome protein concentration | AGM NBK326710 |
| EX_DMPK_MIC | `substrate_uM` | number | µM | yes | | Substrate (typically 1 or 10) | AGM NBK326710 |
| EX_DMPK_MIC | `incubation_min` | number | min | yes | | Incubation time | AGM NBK326710 |
| EX_DMPK_MIC | `temp_C` | number | °C | yes | | Incubation temperature (often 37) | AGM NBK326710 |
| EX_DMPK_MIC | `nadph` | bool | | yes on microsomes | true \| false | Cofactor on microsomes | AGM NBK326710 |
| EX_DMPK_MIC | `cyp_isoform` | text | | yes on CYP assays | | Isoform when the analysis is a CYP assay | AGM NBK326710 |

Do **not** catalog CLint, fu, % remaining.

### 2.3 Cell-based & functional (AGM NBK144065, NCI SOP 23103)

Same sourced keys; two **example** analyses so Heidi can see optional `wavelength_nm` on ELISA vs absent on luminescence.

#### Example analysis `EX_CTG` — CellTiter-Glo / ATP luminescence

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_CTG | `cell_line` | text | | yes | | | [AGM NBK144065](https://www.ncbi.nlm.nih.gov/books/NBK144065/) · [NCI SOP 23103](https://dctd.cancer.gov/drug-discovery-development/assays/high-throughput-screening-services/nci60/submitting-compounds/sop.pdf) |
| EX_CTG | `seeding_density` | number | cells/well | yes | | | AGM NBK144065 · NCI SOP 23103 |
| EX_CTG | `incubation_h` | number | h | yes | | | AGM NBK144065 · NCI SOP 23103 |
| EX_CTG | `readout` | text | | yes | ATP_lum \| MTT \| resazurin \| ELISA \| reporter | Luminescence: no wavelength | AGM NBK144065 · NCI SOP 23103 |
| EX_CTG | `wavelength_nm` | number | nm | no | | Optional; luminescence has none | AGM NBK144065 (ELISA 450/620; lum none) |

#### Example analysis `EX_ELISA` — ELISA readout

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_ELISA | `cell_line` | text | | yes | | Same cell-based family keys | AGM NBK144065 · NCI SOP 23103 |
| EX_ELISA | `seeding_density` | number | cells/well | yes | | | AGM NBK144065 · NCI SOP 23103 |
| EX_ELISA | `incubation_h` | number | h | yes | | | AGM NBK144065 · NCI SOP 23103 |
| EX_ELISA | `readout` | text | | yes | ATP_lum \| MTT \| resazurin \| ELISA \| reporter | | AGM NBK144065 · NCI SOP 23103 |
| EX_ELISA | `wavelength_nm` | number | nm | no | | ELISA often 450 (ref 620) | AGM NBK144065 |

### 2.4 Primary screening & biochemical (AGM NBK91993)

#### Example analysis `EX_BIOCHEM`

Catalog keys only. **No Katinka filled snapshot** in §3.

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_BIOCHEM | `enzyme_or_target` | text | | yes | | | [AGM NBK91993](https://www.ncbi.nlm.nih.gov/books/NBK91993/) |
| EX_BIOCHEM | `substrate_conc_uM` | number | µM | yes | | | AGM NBK91993 |
| EX_BIOCHEM | `incubation_min` | number | min | yes | | | AGM NBK91993 |
| EX_BIOCHEM | `detection` | text | | yes | abs \| fluor \| lum \| lcms | | AGM NBK91993 |
| EX_BIOCHEM | `excitation_nm` | number | nm | no | | Optional if `detection=fluor` | AGM NBK91993 |
| EX_BIOCHEM | `emission_nm` | number | nm | no | | Optional if `detection=fluor` | AGM NBK91993 |
| EX_BIOCHEM | `plate_format` | text | | yes | 96 \| 384 | | AGM NBK91993 |
| EX_BIOCHEM | `dmso_pct` | number | % | no | | | AGM NBK91993 |

### 2.5 Dose/response (AGM 4PL + NCI-60 HTS384)

#### Example analysis `EX_NCI60` — method params for a dose series

`endpoint` here is **which metric the run is set up to estimate**. The **fitted** GI50/IC50 number is a **result**, not a param.

| analysis_code | param_key | value_type | unit | required | allowed_values | notes | source |
|---------------|-----------|------------|------|----------|----------------|-------|--------|
| EX_NCI60 | `n_concentrations` | int | | yes | | NCI 5; AGM 8–10 | [NCI SOP](https://dctd.cancer.gov/drug-discovery-development/assays/high-throughput-screening-services/nci60/submitting-compounds/sop.pdf) · AGM 4PL |
| EX_NCI60 | `conc_min_M` | number | M | yes | | | NCI SOP · AGM 4PL |
| EX_NCI60 | `conc_max_M` | number | M | yes | | | NCI SOP · AGM 4PL |
| EX_NCI60 | `dilution_scheme` | text | | yes | 10-fold \| half-log | | NCI SOP · AGM 4PL |
| EX_NCI60 | `fit_model` | text | | yes | 4PL | Model **choice**, not fitted coefficients | AGM 4PL |
| EX_NCI60 | `endpoint` | text | | yes | IC50 \| EC50 \| GI50 \| TGI \| LC50 | Which endpoint the series is for; fitted value is a result | NCI SOP · AGM 4PL |

---

## 3. Example run-start snapshots (frozen payload)

**Example data only — not seed.** Shape: JSON object whose keys match that analysis’s defs. Frozen at **LimsRun start** (WO-7 / L3). Empty defs remain `{}` (OQ-AF-3).

Only families with **Katinka snapshot values** are filled. `EX_2ND_PHARM` and `EX_BIOCHEM` have catalog keys in §2 and **no** snapshot here.

### 3.1 hERG — Katinka example

`voltage_protocol`: sourced **required** key. String below is a **generic ICH S7B step-depolarization label** (example), not a house protocol id.

```json
{
  "temperature_C": 37,
  "voltage_protocol": "ICH S7B step-depolarization (example label)",
  "stim_freq_Hz": 0.2,
  "cell_line": "HEK-hERG"
}
```

| param_key | example value |
|-----------|----------------|
| `temperature_C` | **37** (example) |
| `voltage_protocol` | **ICH S7B step-depolarization (example label)** (example) |
| `stim_freq_Hz` | **0.2** (example) |
| `cell_line` | **HEK-hERG** (example) |

### 3.2 Ames — Katinka example

```json
{
  "strain": "TA100",
  "s9_activation": true
}
```

| param_key | example value |
|-----------|----------------|
| `strain` | **TA100** (example) |
| `s9_activation` | **true** (example) |

### 3.3 DMPK microsome — Katinka example

```json
{
  "species": "human",
  "matrix": "microsome",
  "protein_conc_mg_ml": 0.5,
  "substrate_uM": 1,
  "incubation_min": 30,
  "temp_C": 37,
  "nadph": true,
  "cyp_isoform": "CYP3A4"
}
```

| param_key | example value |
|-----------|----------------|
| `species` | **human** (example) |
| `matrix` | **microsome** (example) |
| `protein_conc_mg_ml` | **0.5** (example) |
| `substrate_uM` | **1** (example) |
| `incubation_min` | **30** (example) |
| `temp_C` | **37** (example) |
| `nadph` | **true** (example) |
| `cyp_isoform` | **CYP3A4** (example) |

No CLint / fu / % remaining.

### 3.4 CellTiter-Glo — Katinka example

Luminescence: omit `wavelength_nm`.

```json
{
  "cell_line": "A549",
  "seeding_density": 5000,
  "incubation_h": 48,
  "readout": "ATP_lum"
}
```

| param_key | example value |
|-----------|----------------|
| `cell_line` | **A549** (example) |
| `seeding_density` | **5000** (example) |
| `incubation_h` | **48** (example) |
| `readout` | **ATP_lum** (example) |

### 3.5 ELISA — Katinka example + required-key fillers

Katinka snapshot named **`readout`** and **`wavelength_nm`**. Other **required** cell-based keys must appear in a valid freeze object; values for those three are **example fillers**, not Katinka numbers.

```json
{
  "cell_line": "example_cell_line",
  "seeding_density": 10000,
  "incubation_h": 2,
  "readout": "ELISA",
  "wavelength_nm": 450
}
```

| param_key | example value | provenance |
|-----------|----------------|------------|
| `cell_line` | **example_cell_line** (example filler) | required key; not in Katinka snapshot list |
| `seeding_density` | **10000** (example filler) | required key; not in Katinka snapshot list |
| `incubation_h` | **2** (example filler) | required key; not in Katinka snapshot list |
| `readout` | **ELISA** (example) | Katinka |
| `wavelength_nm` | **450** (example) | Katinka |

### 3.6 Dose/response NCI-60 — Katinka example

`endpoint: GI50` is the **setup** choice. Do **not** put a fitted GI50/IC50 number in this payload.

```json
{
  "n_concentrations": 5,
  "conc_min_M": 1e-8,
  "conc_max_M": 1e-4,
  "dilution_scheme": "10-fold",
  "fit_model": "4PL",
  "endpoint": "GI50"
}
```

| param_key | example value |
|-----------|----------------|
| `n_concentrations` | **5** (example) |
| `conc_min_M` | **1e-8** (example) |
| `conc_max_M` | **1e-4** (example) |
| `dilution_scheme` | **10-fold** (example) |
| `fit_model` | **4PL** (example) |
| `endpoint` | **GI50** (example) |

---

## 4. Sources (cite; do not invent)

- https://www.ncbi.nlm.nih.gov/books/NBK326710/
- https://www.ncbi.nlm.nih.gov/books/NBK91993/
- https://www.ncbi.nlm.nih.gov/books/NBK144065/
- https://database.ich.org/sites/default/files/S7B_Guideline.pdf
- OECD 471
- https://dctd.cancer.gov/drug-discovery-development/assays/high-throughput-screening-services/nci60/submitting-compounds/sop.pdf

---

## 5. Fold-in (when `.docs/internal/` is on the host)

Add a section **`analysis_param_defs`** to the spine PRD and SPEC with §1–§3. Do not copy this into gitignored paths from this PR. Do not seed these rows in Alembic/OOB.
