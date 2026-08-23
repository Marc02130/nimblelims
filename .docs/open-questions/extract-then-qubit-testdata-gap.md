# Extract-then-Qubit testdata gap

Findings only. Not an SOP pack and not an implement packet. Leadership lock still stands. Not IC50. Compose stays down. Do not reopen the path lock. Do not invent a third ID scheme or new sample barcodes.

Anton mapped existing 0058/0059 catalog names onto the locked Extract-then-Qubit Hold SOP path (intake sample → one process instance → experiment extract step and/or Qubit LimsRun). The catalog can bind some nearby objects by name; it does not contain the hops this path needs.

Related UAT-path note: [blood-dnatruseq-testdata-gap.md](blood-dnatruseq-testdata-gap.md) (blood → DNA daughter → TruSeq Nano; same Hold holes on dest DNA; capture is a parked second branch).

## Path lock (do not reopen)

One process instance. Blood (or intake matrix) is assigned to extract. Execute mints a dest DNA sample with `parent_sample_id`. Qubit Tests are written at the Qubit LimsRun start on the daughters, never on the parent and never at plan-save. Experiment never writes results. LimsRun publish writes results only on an existing Test. Dest is the product of the step, not a second batch.

Known Hold holes (already locked by Heidi / Lab Ops / Hans): dest copies parent matrix/type so extract still looks like blood; dest is not added to `eln_process_samples` so the Qubit step would see an empty cohort.

Not IC50. Do not treat NCI-60 / GI50 instrument CSVs as this path.

## Existing 0059 samples (bind only these names)

| Catalog name | What it is | Why it does not fill this path |
|--------------|------------|--------------------------------|
| `mAb-2301-PK-T0`, `mAb-2301-PK-T1`, `mAb-2301-PK-T2` | Plasma, `parent_sample_id` null, ELISA tests | Intake for PK, not extract |
| `mAb-2301-PK-T0-Aliq` | Plasma child of T0 (same matrix) | Lineage exists, but it is an aliquot, not a DNA extract daughter |
| `CAR-T-Batch-001`, `CAR-T-Blank-QC` | PBMC | No extract/Qubit tests |
| `Plasmid-Lot-2025-001` | Already Plasmid DNA, no parent | Wrong shape for extract-then-Qubit |

Verified catalog facts from 0058/0059 on main:

- No whole-blood intake sample in 0059.
- No Genomic DNA / matrix-DNA daughter with `parent_sample_id`.
- No Qubit / dsDNA HS analysis or Test in 0058/0059.
- PR 48 instrument CSVs (if present) are NCI-60 CellTiter-Glo, HEK 293 HCP ELISA, kinetic LAL — not Qubit. They stay on `NBIO-CMPD-001` / `CAR-T-Batch-001` / `Plasmid-Lot-2025-001` and are out of scope for this path.

## Map (one row per hop)

| Hop | Catalog bind | Gap |
|-----|--------------|-----|
| Intake | None. Closest catalog: none. Do not reuse plasma PK or plasmid as the extract parent. | Missing whole blood. |
| Process instance | None in 0058/0059. | No extract-then-Qubit process/seed. |
| Extract experiment step | Execute can mint dest + `parent_sample_id`, but dest matrix/type copy and missing `eln_process_samples` attach are the Hold holes. | Catalog has no DNA dest to bind. |
| Qubit LimsRun | No Qubit Test on a daughter; publish must not invent a Test. | No Qubit instrument file in the catalog. |

Testdata will not invent blood/DNA/Qubit IDs until the Hold ships. Extract-then-Qubit remains Hold. No SOP bodies. Compose stays down.
