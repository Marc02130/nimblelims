# SOP links for the configuring-agent slice

Links and field-name hints only. No SOP body text. TruSeq Nano is held for run 2. SureSelect stays parked. Both are left out of this packet.

The blood-to-DNA path below uses only the whole-blood intake and the genomic DNA daughter. Do not route `mAb-2301-PK-T0`, `mAb-2301-PK-T0-Aliq`, or `Plasmid-Lot-2025-001` through these steps.

## 1. CMDL-SOP2310 v1.0

Whole-blood DNA extraction. NCI Frederick. KingFisher Flex and GenFind kit.

Source: https://frederick.cancer.gov/media/4402/download?ext=pdf

| Step | Input matrix | Output matrix | Field-name hints |
|------|----------------|---------------|------------------|
| 1. Bind the intake vessel | Whole Blood | Whole Blood (same material) | barcode, sample ID, vessel, matrix/type |
| 2. Extract | Whole Blood | Genomic DNA | barcode, sample ID, vessel, parent link, matrix/type |

Named quantities from the SOP owner, not copied procedure text: 600 µL blood input, up to 24 samples per run, about 400 µL DNA eluate per sample.

Sample type on the parent is the existing list entry `Blood`. Sample type on the daughter is the existing list entry `DNA`, allowed by the 0068 transition Blood × aliquot → DNA. `Whole Blood` and `Genomic DNA` are existing matrix list entries, not sample types.

## 2. SOP 22975

Qubit 4 dsDNA quantitation. NCI Frederick.

Source: https://frederick.cancer.gov/sites/default/files/2023-01/22975_Redacted.pdf

| Step | Input matrix | Output matrix | Field-name hints |
|------|----------------|---------------|------------------|
| 1. Read the DNA eluate | Genomic DNA | Genomic DNA (same material; the output is a concentration result, not a new sample) | barcode, sample ID, vessel, parent link, matrix/type |

Result fields to configure later, not seeded here: concentration (ng/µL), HS or BR kit, sample volume, dilution factor, standards pass/fail.
