# Blood → DNA → TruSeq testdata gap

Findings only. Not an SOP pack and not an implement packet. Leadership lock still stands. Not IC50. Compose stays down. Do not reopen the path lock. Do not invent a third ID scheme or new sample barcodes.

Anton mapped existing 0058/0059 catalog names onto the locked **one-UAT-path** for WGS prep: blood intake → DNA daughter (dest type on extract entry, `parent_sample_id`) → TruSeq Nano library. Capture (SureSelectXT) is a **second branch**, not the default walk. The same Extract-then-Qubit Hold still blocks the DNA daughter. Grok Build owns implement; this note is planning/UAT docs only.

Related Hold note (PR 50): [extract-then-qubit-testdata-gap.md](extract-then-qubit-testdata-gap.md).

## Source SOP numbers (Katinka holds the links)

Do not paste SOP procedure text, kit steps, or PDFs. Names and numbers only:

| Role on this path | SOP number (name only) |
|-------------------|------------------------|
| Blood extract (default intake) | CMDL-SOP2310 KingFisher whole blood |
| Tissue (not default path) | MCCRD-SOP0002 |
| FFPE backup (not default path) | CMDL-SOP2308 |
| QIAamp backup (not default path) | SOP 23113 |
| Library (default walk) | TruSeq Nano DNA (WGS) |
| Capture (second branch only) | MCCRD-SOP0005 SureSelectXT |
| Quant (optional on path) | SOP 22975 Qubit |

## Path lock (do not reopen)

- **One UAT path:** blood → DNA (dest type template on extract) → TruSeq Nano.
- **Capture** is a second branch, not the default walk. Do not seed it for default UAT.
- Same **Extract-then-Qubit Hold** holes apply to the DNA daughter: dest must not copy parent matrix/type (must be Genomic DNA); dest must land on `eln_process_samples` of that started instance with `parent_sample_id`.
- **Tobias:** do not stamp until dest DNA has `parent_sample_id` and lands on this instance.
- **Günter:** when dest DNA lands on a started instance, only execute-minted daughters of that instance; same client; `experiment:manage` on that instance; append of an arbitrary sample ID stays refuse.
- Library dest (if minted) follows the same rule.
- Experiment never writes results. LimsRun publish writes only on an existing Test.
- Not IC50. Do not treat NCI-60 / HCP / LAL instrument CSVs as this path.

## Existing 0058/0059 facts

0058 list types include Whole Blood and Genomic DNA, but 0059 has **no sample using them**.

| Catalog name | What it is | Why it does not fill this path |
|--------------|------------|--------------------------------|
| `mAb-2301-PK-T0`, `mAb-2301-PK-T1`, `mAb-2301-PK-T2` | Plasma, `parent_sample_id` null | Intake for PK, not whole-blood WGS |
| `mAb-2301-PK-T0-Aliq` | Plasma child of T0 (same matrix) | Lineage exists, but it is an aliquot, not a DNA extract |
| `CAR-T-Batch-001`, `CAR-T-Blank-QC` | PBMC | No extract / TruSeq / Qubit tests |
| `Plasmid-Lot-2025-001` | Already Plasmid DNA, no parent | Wrong shape for blood → Genomic DNA daughter |

Verified catalog facts from 0058/0059 on main:

- No whole-blood intake sample in 0059.
- No Genomic DNA dest with `parent_sample_id`.
- No Qubit / dsDNA HS analysis or Test.
- No TruSeq / library-prep / WGS analysis or Test.
- No TruSeq or Qubit instrument export fixture (PR 49 is NCI-60 / HCP / LAL only). Those files stay on `NBIO-CMPD-001` / `CAR-T-Batch-001` / `Plasmid-Lot-2025-001` and are out of scope for this path.

## Map (one row per hop)

| Hop | Catalog bind | Gap |
|-----|--------------|-----|
| 1. Intake | None. Closest catalog: none. Do not reuse plasma PK or plasmid as the blood parent. | Missing whole-blood sample. |
| 2. Extract → DNA daughter | Execute can mint dest + `parent_sample_id`, but dest matrix/type copy and missing `eln_process_samples` attach are the Hold holes. Dest must be Genomic DNA, not a copy of blood. Dest must land on `eln_process_samples` of that started instance. | Hold blocks: no Genomic DNA dest with `parent_sample_id` on the instance. |
| 3. Qubit quant (optional on path) | No Qubit / dsDNA HS analysis or Test. Publish must not invent a Test. | No Qubit Test/export in catalog. |
| 4. TruSeq Nano library | No library sample, analysis, or result. If a library dest is minted, same `parent_sample_id` + instance attach rules as dest DNA. | No TruSeq / library-prep / WGS analysis or Test. |
| 5. WGS-shaped result on the sample’s Test | No analysis/Test to bind. LimsRun publish writes only on an existing Test. | Publish must not invent a Test. |

## Capture branch (parked)

MCCRD-SOP0005 SureSelectXT is a **second branch only**. Documented here so default UAT does not walk it. Do not seed capture samples, analyses, Tests, or instrument fixtures for the default blood → DNA → TruSeq Nano walk.

## Close

Testdata will not invent blood/DNA/TruSeq IDs that pretend the Hold shipped. Seed only real gaps **after** dest DNA lands on the instance (`parent_sample_id`, Genomic DNA, `eln_process_samples` of that started instance). No SOP bodies. Compose stays down. Grok Build owns implement.
