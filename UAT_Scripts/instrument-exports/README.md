# Instrument-export CSV fixtures

Plate-reader exports for UAT and future parser dry-runs. **Data parsers and LimsRuns stay parked** — these files are fixtures only; they do not implement import.

SOP PDFs stay on the public web. Do **not** commit SOP PDFs and do **not** place files under `.docs/sop/`.

Sample and project names bind to migrations **0058** / **0059**. Do **not** invent a third ID scheme.

| File | Assay | 0058 / 0059 bind |
|------|--------|------------------|
| `nci60-hts-celltiter-glo.csv` | NCI-60 HTS384 CellTiter-Glo five-dose (96-well subset). Vehicle + five log doses `1e-4`…`1e-8` M of `NBIO-CMPD-001`. No EPA/soil. | Project `mAb-2301 PK Study`. No LIMS sample rows. |
| `hek293-hcp-elisa-a450.csv` | Cygnus HEK 293 HCP ELISA (kit F650S), A450/A620 with `a450_corr = a450 − a620`. | SAMPLE rows: `CAR-T-Batch-001` / `CAR-T In-Process Testing` (HEK residual HCP). **Not** `Plasmid-Lot-2025-001` (E. coli plasmid). `lims_sample` / `project` only on SAMPLE rows. |
| `lal-kinetic-chromogenic.csv` | Charles River Sunrise / Endoscan-V kinetic chromogenic LAL (`EU/mL`). | SAMPLE rows: `CAR-T-Batch-001` / `CAR-T In-Process Testing` and `Plasmid-Lot-2025-001` / `Plasmid Lot Release Testing`. PPC 0.5 EU/mL spike on `CAR-T-Batch-001`. |

## NCI-60 (`nci60-hts-celltiter-glo.csv`)

- `plate_id`: `NBIO-HTS-384-001`
- Eight BioTech cell lines (rows A–H): A549, MCF7, HCT116, PC-3, SK-OV-3, U251, MALME-3M, NCI-H460
- Col 01 vehicle; cols 02–06 treated doses
- Tz / C / Ti RLU and NCI `%G`. GI50 / TGI / LC50 filled only where that curve reaches the endpoint; otherwise blank

## HEK 293 HCP (`hek293-hcp-elisa-a450.csv`)

- Standards 0, 2, 4, 8, 16, 32, 64 ng/mL in duplicate
- Positive control ~12 ng/mL
- `CAR-T-Batch-001` neat (~18 ng/mL, `%CV` < 25) and 1:10 (~1.7 ng/mL)

## LAL (`lal-kinetic-chromogenic.csv`)

- Standards 5, 0.5, 0.05, 0.005 EU/mL in duplicate (shorter onset at higher EU)
- Two blanks (no onset / no result)
- Samples in duplicate: CAR-T ~0.13 EU/mL, plasmid ~0.07 EU/mL
