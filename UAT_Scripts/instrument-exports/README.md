# Instrument export fixtures (testdata)

Three plate-reader CSVs for later parser/LimsRuns work. Parsers stay parked for MVP. No SOP PDFs (IP). One file per instrument. Bind to existing 0058/0059 names only; no third ID scheme.

Each file has **10 examples**: `example_id` 01–10, `example_class` `valid` (01–08) or `edge` (09–10). One example = one importable result (one compound or one sample on that plate), not extra wells of the same curve.

## Files

| File | Assay | LIMS bind |
|---|---|---|
| `nci60-hts-celltiter-glo.csv` | NCI-60 HTS384 CellTiter-Glo | `NBIO-CMPD-001` / mAb-2301 PK Study |
| `hek293-hcp-elisa-a450.csv` | Cygnus F650S HEK 293 HCP ELISA | `CAR-T-Batch-001` / CAR-T In-Process Testing |
| `lal-kinetic-chromogenic.csv` | Kinetic chromogenic LAL (Charles River Sunrise) | CAR-T-Batch-001 + Plasmid-Lot-2025-001 |

## NCI-60 (`example_id`)

Keep Tz/C/Ti, %G. Report GI50/TGI/LC50 only when reached.

| id | class | shape |
|---|---|---|
| 01 | valid | GI50 only (cytostatic) |
| 02 | valid | GI50 + TGI |
| 03 | valid | GI50 + TGI + LC50 |
| 04 | valid | inactive, %G stays high, no GI50 |
| 05 | valid | potent (nM GI50) |
| 06 | valid | weak (µM GI50) |
| 07 | valid | line-selective (A549/HCT116/U251); one compound, same plate |
| 08 | valid | second `plate_id` of `NBIO-CMPD-001` (no second 0059 compound) |
| 09 | edge | vehicle C ≤ Tz; do not report GI50 |
| 10 | edge | incomplete curve (1e-6 missing); endpoints blank |

## HEK 293 HCP ELISA

A450/A620, dups, %CV. SAMPLE is always `CAR-T-Batch-001` (HEK product), never plasmid.

| id | class | shape |
|---|---|---|
| 01 | valid | neat in-range, %CV <10% |
| 02 | valid | 1:10 dilution mid-curve |
| 03 | valid | just above 4 ng/mL, %CV ~20% (SOP pass <25%) |
| 04 | valid | near ULOQ (~60 of 64) |
| 05 | valid | mid-curve ~16 ng/mL |
| 06 | valid | 1:100 dilution, back-calculated |
| 07 | valid | PC 12 ng/mL passing |
| 08 | valid | second `plate_id` of CAR-T-Batch-001 (no second HEK lot in 0059) |
| 09 | edge | %CV ~32% on sample >4 ng/mL → fail/repeat |
| 10 | edge | neat above ULOQ (>64); invalid until diluted |

## Kinetic LAL

Onset + EU/mL. USP <85> PPC 50–200%.

| id | class | shape |
|---|---|---|
| 01 | valid | CAR-T ~0.14 EU/mL, PPC pass |
| 02 | valid | plasmid ~0.07 EU/mL, PPC pass |
| 03 | valid | near LLOQ ~0.008 |
| 04 | valid | mid ~0.5 |
| 05 | valid | high in-range ~2 |
| 06 | valid | 1:10 diluted sample, corrected EU/mL |
| 07 | valid | second CAR-T run, different `plate_id` |
| 08 | valid | blanks 0, std recoveries ~100% |
| 09 | edge | PPC recovery ~30% (inhibition) → run invalid |
| 10 | edge | blank contaminated (result >0) → run fail |

## Out of scope

- SOP PDFs
- Parsers / LimsRuns
- Anything under `.docs/sop/`
