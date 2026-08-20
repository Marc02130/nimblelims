# SOP packs (source material)

Public/standard BioTech/Pharma laboratory SOP research for NimbleLIMS MVP (sample tracking, test ordering, results entry). These are **source packs**, not product requirements. Wilhelmina turns gaps into stories in `requirements/` and `user-stories/`.

Compiled 20 Aug 2026 by Katinka. Public sources only; do not treat synthesis as a fake SOP.

| File | What it is |
|------|------------|
| [sample-management-mvp.md](sample-management-mvp.md) | Receipt, IDs, chain of custody, storage, aliquots, disposal |
| [test-ordering-results-qc-lims-mvp.md](test-ordering-results-qc-lims-mvp.md) | Test orders, results entry, QC gates, LIMS data integrity |
| [nimblelims-sop-mapping.md](nimblelims-sop-mapping.md) | Mapping onto the current product (status list, barcode suffix, audit) |

**Do not** copy hospital/CLIA two-patient-ID rules as the default. **Do not** pull CGT chain-of-identity from CAR-T seed data. Parked: ELN, LimsRuns, dose-response, parsers, Part 11 e-signature theater.
