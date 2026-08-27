# Instrument export fixtures (testdata)

Plate-reader CSVs for later parser/LimsRuns work. Parsers stay parked for MVP. No SOP PDFs (IP). Bind to existing 0058/0059 names only; no third ID scheme.

Each assay has **10 separate export files** (`01`–`10`): `01`–`08` are `valid`, `09`–`10` are `edge`. One file = one importable result example (one compound or one sample on that plate), not extra wells of the same curve.

Columns still include `example_id`, `example_class`, and `example_note` for traceability.

## Layout

```
instrument-exports/
  nci60-hts-celltiter-glo/     # NCI-60 HTS384 CellTiter-Glo
  hek293-hcp-elisa-a450/       # Cygnus F650S HEK 293 HCP ELISA
  lal-kinetic-chromogenic/     # Kinetic chromogenic LAL (Charles River Sunrise)
  README.md
```

| Directory | Assay | LIMS bind |
|---|---|---|
| `nci60-hts-celltiter-glo/` | NCI-60 HTS384 CellTiter-Glo | `NBIO-CMPD-001` / mAb-2301 PK Study |
| `hek293-hcp-elisa-a450/` | Cygnus F650S HEK 293 HCP ELISA | `CAR-T-Batch-001` / CAR-T In-Process Testing |
| `lal-kinetic-chromogenic/` | Kinetic chromogenic LAL | CAR-T-Batch-001 + Plasmid-Lot-2025-001 |

## NCI-60 (`nci60-hts-celltiter-glo/`)

Keep Tz/C/Ti, %G. Report GI50/TGI/LC50 only when reached.

| File | class | shape |
|---|---|---|
| `01-valid-gi50-only-cytostatic.csv` | valid | GI50 only (cytostatic) |
| `02-valid-gi50-plus-tgi.csv` | valid | GI50 + TGI |
| `03-valid-gi50-plus-tgi-plus-lc50.csv` | valid | GI50 + TGI + LC50 |
| `04-valid-inactive-no-gi50.csv` | valid | inactive, %G stays high, no GI50 |
| `05-valid-potent-nm-gi50.csv` | valid | potent (nM GI50) |
| `06-valid-weak-um-gi50.csv` | valid | weak (µM GI50) |
| `07-valid-line-selective.csv` | valid | line-selective (A549/HCT116/U251); one compound, same plate |
| `08-valid-second-plate-id.csv` | valid | second `plate_id` of `NBIO-CMPD-001` (no second 0059 compound) |
| `09-edge-vehicle-c-le-tz.csv` | edge | vehicle C ≤ Tz; do not report GI50 |
| `10-edge-incomplete-curve.csv` | edge | incomplete curve (1e-6 missing); endpoints blank |

## HEK 293 HCP ELISA (`hek293-hcp-elisa-a450/`)

A450/A620, dups, %CV. SAMPLE is always `CAR-T-Batch-001` (HEK product), never plasmid.

| File | class | shape |
|---|---|---|
| `01-valid-neat-in-range.csv` | valid | neat in-range, %CV <10% |
| `02-valid-1-to-10-dilution.csv` | valid | 1:10 dilution mid-curve |
| `03-valid-just-above-4ng-cv20.csv` | valid | just above 4 ng/mL, %CV ~20% (SOP pass <25%) |
| `04-valid-near-uloq.csv` | valid | near ULOQ (~60 of 64) |
| `05-valid-mid-curve-16ng.csv` | valid | mid-curve ~16 ng/mL |
| `06-valid-1-to-100-dilution.csv` | valid | 1:100 dilution, back-calculated |
| `07-valid-pc-12ng-passing.csv` | valid | PC 12 ng/mL passing |
| `08-valid-second-plate-id.csv` | valid | second `plate_id` of CAR-T-Batch-001 (no second HEK lot in 0059) |
| `09-edge-cv32-fail-repeat.csv` | edge | %CV ~32% on sample >4 ng/mL → fail/repeat |
| `10-edge-above-uloq.csv` | edge | neat above ULOQ (>64); invalid until diluted |

## Kinetic LAL (`lal-kinetic-chromogenic/`)

Onset + EU/mL. USP <85> PPC 50–200%.

| File | class | shape |
|---|---|---|
| `01-valid-car-t-ppc-pass.csv` | valid | CAR-T ~0.14 EU/mL, PPC pass |
| `02-valid-plasmid-ppc-pass.csv` | valid | plasmid ~0.07 EU/mL, PPC pass |
| `03-valid-near-lloq.csv` | valid | near LLOQ ~0.008 |
| `04-valid-mid-range.csv` | valid | mid ~0.5 |
| `05-valid-high-in-range.csv` | valid | high in-range ~2 |
| `06-valid-1-to-10-diluted.csv` | valid | 1:10 diluted sample, corrected EU/mL |
| `07-valid-second-car-t-run.csv` | valid | second CAR-T run, different `plate_id` |
| `08-valid-blanks-and-std-recovery.csv` | valid | blanks 0, std recoveries ~100% |
| `09-edge-ppc-inhibition.csv` | edge | PPC recovery ~30% (inhibition) → run invalid |
| `10-edge-blank-contaminated.csv` | edge | blank contaminated (result >0) → run fail |

## Out of scope

- SOP PDFs
- Parsers / LimsRuns
- Anything under `.docs/internal/sop/`
